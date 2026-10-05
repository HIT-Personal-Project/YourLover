"""
聊天窗口模块 （项目主页）
负责：
- 聊天消息显示
- Markdown渲染
- 历史记录管理
- 输入框交互
- 语音按钮
- Tool调用状态显示
- 左侧历史会话列表

窗口生命周期：
- 关闭时执行hide()，而非destroy()
- 保持窗口状态，下次打开时恢复

事件流示例：
    User -> ChatWindow -> AgentClient -> Server -> Streaming -> EventBus -> ChatWindow更新
"""

import uuid
from datetime import datetime
from typing import Any

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from agent.memory.session_store import SessionRecord, SessionStore, SessionStoreError
from core.agent_event import AgentEvent
from core.event_bus import event_bus
from utils.message_filter import extract_emotion
from windows.base_window import BaseWindow
from widgets.chat.chat_header import ChatHeader
from widgets.chat.chat_history import ChatHistory, MessageRole
from widgets.chat.chat_input import ChatInput
from widgets.chat.chat_session_list import ChatSessionList, SessionData


class ChatWindow(BaseWindow):
    """聊天主页窗口（Claude Desk 风格）。

    职责：
    - 组合 ChatSessionList（左侧）、ChatHeader、ChatHistory、ChatInput 四个组件。
    - 将用户输入通过 EventBus 转发给 Agent。
    - 订阅 Agent 回复事件并更新历史记录。
    - 通过 header 的设置按钮打开设置面板。
    - 管理会话列表（新建、切换、删除）。

    暴露接口：
    - append_user_message(text): 追加用户消息。
    - append_agent_message(text): 追加助手消息。
    - update_last_agent_message(text): 更新最后一条助手消息（流式）。
    - set_status(text, color): 更新顶部状态。
    - clear_chat(): 清空聊天记录。
    - set_input_enabled(enabled): 启用/禁用输入。
    - create_new_session(): 新建一个会话。
    - switch_session(session_id): 切换到指定会话。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化聊天窗口。

        Args:
            parent: 父级窗口，通常为空或 LoverWindow。
        """
        self._current_agent_bubble = None
        self._user_id = "default-user"  # 当前界面所属用户，与 Agent 默认用户保持一致
        self._session_store = SessionStore()  # 负责读取和维护已持久化的短期会话
        self._sessions: dict[str, dict] = {}  # 保存各 session 的界面消息缓存
        super().__init__(parent)

        # 等 App 完成事件绑定后，再把初始 session_id 同步给 AgentController。
        QTimer.singleShot(0, self._activate_current_session)

    def _setup_window_flags(self) -> None:
        """配置聊天窗口标志：标准窗口，可最小化/关闭。"""
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("YourLover - 聊天")
        self.setMinimumSize(900, 560)
        self.resize(1040, 680)

    def setup_ui(self) -> None:
        """创建聊天窗口布局：左侧会话列表 + 右侧聊天区。"""
        self._central_widget = QWidget(self)
        self.setCentralWidget(self._central_widget)

        # 主水平布局：左侧会话列表 | 右侧聊天区
        self._root_layout = QHBoxLayout(self._central_widget)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # 左侧会话列表
        self._session_list = ChatSessionList(self)

        # 右侧聊天区
        self._chat_area = QWidget(self)
        self._chat_area.setObjectName("chat_area")
        self._chat_layout = QVBoxLayout(self._chat_area)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(0)

        # 顶部栏
        self._header = ChatHeader(self)
        # 历史记录
        self._history = ChatHistory(self)
        # 输入框
        self._input = ChatInput(self)

        self._chat_layout.addWidget(self._header)
        self._chat_layout.addWidget(self._history, stretch=1)
        self._chat_layout.addWidget(self._input)

        # 组装
        self._root_layout.addWidget(self._session_list)
        self._root_layout.addWidget(self._chat_area, stretch=1)

        self.apply_style()

        # 优先恢复历史会话；没有历史记录时再创建一个新会话。
        if not self._restore_persisted_sessions():
            self.create_new_session()

    def connect_signals(self) -> None:
        """连接组件信号与 EventBus。"""
        # 用户点击发送 -> EventBus
        # 注意：用户消息的显示由 WindowManager 统一处理，避免重复连接。
        self._input.send_clicked.connect(event_bus.user_message_sent.emit)

        # 顶部设置按钮 -> EventBus
        self._header.settings_clicked.connect(
            event_bus.show_setting_window_requested.emit
        )

        # 会话列表信号
        self._session_list.new_session_requested.connect(self.create_new_session)
        self._session_list.session_clicked.connect(self._on_session_clicked)
        self._session_list.session_deleted.connect(self._on_session_deleted)

        # Agent 事件
        event_bus.agent_thinking_started.connect(self._on_agent_thinking_started)
        event_bus.agent_thinking_finished.connect(self._on_agent_thinking_finished)
        event_bus.agent_reply_received.connect(self._on_agent_reply_received)
        event_bus.agent_stream_chunk.connect(self._on_agent_stream_chunk)

        #更新状态栏
        event_bus.state_emotion_change.connect(self._header.set_emotional)
        event_bus.state_love_change.connect(self._header.set_affection)

    def apply_style(self) -> None:
        """应用聊天窗口整体样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #fdf2f8;
            }
            QWidget#chat_area {
                background-color: #fffafc;
            }
            """
        )

    # ============================================================
    # 会话管理接口
    # ============================================================

    def _restore_persisted_sessions(self) -> bool:
        """读取并展示历史 Session，逻辑是按最近更新时间恢复列表和消息。"""
        try:
            records = [
                record
                for record in self._session_store.list_sessions(self._user_id)
                if record.session_id != "mini-chat"
            ]
            restored_sessions = [
                (record, *self._load_display_messages(record.session_id))
                for record in records
            ]
            for record, messages, emotion, love in restored_sessions:
                # 缓存消息及最近一条 AI 消息的情绪/好感度，切换会话时恢复到头部
                self._sessions[record.session_id] = {
                    "messages": messages,
                    "emotion": emotion,
                    "love": love,
                }
                self._session_list.add_session(
                    SessionData(
                        session_id=record.session_id,
                        title=self._session_title(record, messages),
                        preview=self._session_preview(record, messages),
                        updated_at=self._parse_datetime(record.updated_at),
                        avatar="🌸",
                    )
                )
        except SessionStoreError as exc:
            print(f"[chat_window] 读取历史会话失败: {exc}")
            return False

        if not records:
            return False

        # list_sessions 已按新到旧排序，因此启动时默认选中最近会话。
        self._session_list.select_session(records[0].session_id)
        return True

    def _load_display_messages(
        self,
        session_id: str,
    ) -> tuple[list[tuple[MessageRole, str]], str | None, int | None]:
        """读取一个 Session 的可见消息，只恢复正常的用户和助手对话。

        返回 (消息列表, 最近AI情绪, 最近AI好感度)：
        - AI 消息会剥离 <<情绪>> 与 {{好感度}} 标记（与实时聊天展示一致）；
        - 情绪取最后一条带标记的 AI 消息的首个标记；
        - 好感度取最后一条 AI 消息的 MemoryItem.love（轮末快照）。
        """
        messages: list[tuple[MessageRole, str]] = []
        emotion: str | None = None
        love: int | None = None
        for item in self._session_store.load_memory_items(self._user_id, session_id):
            if item.type != "Chat":
                continue
            role = self._display_role(item.speaker)
            content = self._message_content(item.message.content)
            if role is None or not content:
                continue
            if role == MessageRole.AGENT:
                # 历史消息同样要过滤标记，避免 <<Happy>>{{+3}} 残留在气泡里
                content, emotions = extract_emotion(content)
                content = content.strip()
                if emotions:
                    emotion = emotions[0]
                if isinstance(item.love, int):
                    love = item.love
            if content:
                messages.append((role, content))
        return messages, emotion, love

    @staticmethod
    def _display_role(speaker: str) -> MessageRole | None:
        """把 MemoryItem 的说话者转换为聊天气泡角色。"""
        normalized = speaker.strip().lower()
        if normalized in {"user", "human"}:
            return MessageRole.USER
        if normalized in {"ai", "assistant"}:
            return MessageRole.AGENT
        return None

    @staticmethod
    def _message_content(content: Any) -> str:
        """把持久化消息内容转换为界面可展示的文本。"""
        if isinstance(content, str):
            return content.strip()
        return str(content).strip() if content is not None else ""

    @staticmethod
    def _session_title(
        record: SessionRecord,
        messages: list[tuple[MessageRole, str]],
    ) -> str:
        """生成会话标题，优先使用数据库标题，再使用首条用户消息。"""
        if record.title.strip():
            return record.title
        first_user_message = next(
            (content for role, content in messages if role == MessageRole.USER),
            "",
        )
        return ChatWindow._short_text(first_user_message, 12) or "新对话"

    @staticmethod
    def _session_preview(
        record: SessionRecord,
        messages: list[tuple[MessageRole, str]],
    ) -> str:
        """生成会话预览，优先展示最后一条消息，其次展示摘要。"""
        source = messages[-1][1] if messages else record.summary
        return ChatWindow._short_text(source, 20) or "点击开始聊天~"

    @staticmethod
    def _short_text(content: str, limit: int) -> str:
        """截取列表中的标题或预览文本，并在超长时添加省略号。"""
        return content[:limit] + ("..." if len(content) > limit else "")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        """解析数据库时间；旧数据格式异常时使用当前时间。"""
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now()

    def _activate_current_session(self) -> None:
        """启动后恢复当前会话内容，并把 session_id 同步给 AgentController。"""
        session_id = self._session_list.current_session_id()
        if session_id is not None:
            self._on_session_clicked(session_id)

    def create_new_session(self) -> None:
        """新建一个会话并添加到列表中。

        设计说明：
        - 每个会话有独立的 session_id，通过 chat_session_changed 事件通知
          AgentController 更新当前 session_id，确保 Agent 记忆隔离。
        """
        session_id = uuid.uuid4().hex[:8]
        data = SessionData(
            session_id=session_id,
            title="新对话",
            preview="点击开始聊天~",
            avatar="🌸",
        )
        self._session_store.create_session(self._user_id, session_id, data.title)
        self._sessions[session_id] = {"messages": []}
        self._session_list.add_session(data)
        # 通知 AgentController 切换到新会话
        event_bus.chat_session_changed.emit(session_id)

    def switch_session(self, session_id: str) -> None:
        """切换到指定会话。

        Args:
            session_id: 目标会话 ID。
        """
        self._session_list.select_session(session_id)
        # 通知 AgentController 切换到该会话
        event_bus.chat_session_changed.emit(session_id)

    def _on_session_clicked(self, session_id: str) -> None:
        """会话被点击：恢复该会话的消息历史，并通知 AgentController 切换会话。

        Args:
            session_id: 会话 ID。
        """
        # 通知 AgentController 切换到该会话
        event_bus.chat_session_changed.emit(session_id)

        # 清空当前显示
        self._history.clear_history()
        self._current_agent_bubble = None

        # 恢复会话消息
        session = self._sessions.get(session_id, {"messages": []})
        for role, content in session["messages"]:
            bubble = self._history.append_message(role, content)
            if role == MessageRole.AGENT:
                self._current_agent_bubble = None  # 历史消息不参与流式更新

        # 恢复头部状态：最近一条 AI 消息的情绪与好感度（无历史则保持现状）
        emotion = session.get("emotion")
        if emotion in {"Happy", "Sad", "Angry", "Shy"}:
            event_bus.state_emotion_change.emit(emotion)
        love = session.get("love")
        if love is not None:
            event_bus.state_love_change.emit(int(love))

    def _on_session_deleted(self, session_id: str) -> None:
        """删除会话，逻辑是先删除数据库记录，再移除界面缓存。

        Args:
            session_id: 被删除的会话 ID。
        """
        try:
            self._session_store.delete_session(self._user_id, session_id)
        except SessionStoreError as exc:
            print(f"[chat_window] 删除历史会话失败: {exc}")
            return

        self._sessions.pop(session_id, None)
        self._session_list.remove_session(session_id)

        # 如果删的是当前会话，清空聊天区
        if not self._sessions:
            self._history.clear_history()
            self._current_agent_bubble = None

    def _save_message_to_session(self, role: MessageRole, content: str) -> None:
        """把消息保存到当前会话。

        Args:
            role: 消息角色。
            content: 消息内容。
        """
        session_id = self._session_list.current_session_id()
        if session_id is None:
            return

        # 每次发送前再次同步，避免迷你聊天使用的固定 session_id 影响大窗口。
        if role == MessageRole.USER:
            event_bus.chat_session_changed.emit(session_id)

        session = self._sessions.setdefault(session_id, {"messages": []})
        session["messages"].append((role, content))

        # 更新会话列表的标题和预览；消息正文由 ChatAgent 统一持久化。
        if role == MessageRole.USER:
            title = self._short_text(content, 12)
            preview = self._short_text(content, 20)
            data = SessionData(
                session_id=session_id,
                title=title,
                preview=preview,
                avatar="🌸",
            )
        else:
            title_source = session["messages"][0][1] if session["messages"] else ""
            title = self._short_text(title_source, 12) or "新对话"
            preview = self._short_text(content, 20)
            data = SessionData(
                session_id=session_id,
                title=title,
                preview=preview,
                avatar="🌸",
            )

        self._session_list.update_session(data)
        try:
            self._session_store.update_session_title(
                self._user_id,
                session_id,
                data.title,
            )
        except SessionStoreError as exc:
            print(f"[chat_window] 更新会话标题失败: {exc}")

    # ============================================================
    # 消息操作接口
    # ============================================================

    def append_user_message(self, text: str) -> None:
        """追加一条用户消息到历史记录。

        Args:
            text: 用户消息文本。
        """
        self._history.append_message(MessageRole.USER, text)
        self._save_message_to_session(MessageRole.USER, text)

    def append_agent_message(self, text: str) -> None:
        """追加一条助手消息到历史记录。

        Args:
            text: 助手消息文本。
        """
        self._current_agent_bubble = self._history.append_message(
            MessageRole.AGENT, text
        )
        self._save_message_to_session(MessageRole.AGENT, text)

    def update_last_agent_message(self, text: str) -> None:
        """更新最后一条助手消息（用于流式输出）。

        Args:
            text: 当前累计的完整文本。
        """
        self._history.update_last_message(text)

    def clear_chat(self) -> None:
        """清空聊天记录。"""
        self._history.clear_history()
        self._current_agent_bubble = None

    # ============================================================
    # 状态与输入控制
    # ============================================================

    def set_status(self, text: str, color: str = "#10b981") -> None:
        """更新顶部状态文本。

        Args:
            text: 状态文本。
            color: 状态颜色（hex）。
        """
        self._header.set_status(text, color)

    def set_input_enabled(self, enabled: bool) -> None:
        """启用或禁用输入框。

        Args:
            enabled: True 表示启用，False 表示禁用。
        """
        self._input.set_enabled(enabled)

    # ============================================================
    # EventBus 事件处理（预留，后续填充具体业务）
    # ============================================================

    def _on_agent_thinking_started(self) -> None:
        """Agent 开始思考时调用。"""
        self.set_status("思考中...", "#f59e0b")
        self.set_input_enabled(False)
        # TODO: 可在此显示思考动画或工具调用状态

    def _on_agent_thinking_finished(self) -> None:
        """Agent 思考结束时调用。"""
        self.set_status("正在回复...", "#3b82f6")

    def _on_agent_reply_received(self, event: AgentEvent) -> None:
        """收到完整 Agent 回复时调用。

        说明：
        - 若已存在流式气泡，则仅做最终状态更新。
        - 若不存在，则直接追加完整回复（非流式模式）。

        Args:
            event: AgentEvent 事件对象。
        """
        content = event.payload.get("content", "")
        if self._current_agent_bubble is None:
            # 非流式模式：直接追加完整回复
            self.append_agent_message(content)
        else:
            # 流式模式：更新最后一条已有的 Agent 气泡
            self.update_last_agent_message(content)
        # 无论哪种模式，回复处理结束后都要清空当前 Agent 气泡引用，
        # 避免下次回复时错误更新到最后一条消息（可能是用户消息）。
        self._current_agent_bubble = None

        self.set_status("在线", "#10b981")
        self.set_input_enabled(True)

    def _on_agent_stream_chunk(self, chunk: str) -> None:
        """收到流式回复片段时调用。

        Args:
            chunk: 当前片段文本。
        """
        if self._current_agent_bubble is None:
            self._current_agent_bubble = self._history.append_message(
                MessageRole.AGENT, chunk
            )
        else:
            current_text = self._current_agent_bubble.message().content
            self.update_last_agent_message(current_text + chunk)

    # ============================================================
    # 预留扩展接口
    # ============================================================

    def show_tool_status(self, tool_name: str, status: str) -> None:
        """显示工具调用状态（预留接口）。

        Args:
            tool_name: 工具名称。
            status: 状态描述。
        """
        # TODO: 在历史记录中插入系统提示或状态气泡
        pass

    def set_voice_input_enabled(self, enabled: bool) -> None:
        """启用或禁用语音输入按钮（预留接口）。

        Args:
            enabled: True 表示启用。
        """
        # TODO: 接入语音识别后实现
        pass
