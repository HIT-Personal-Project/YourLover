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
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from core.agent_event import AgentEvent
from core.event_bus import event_bus
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
        self._sessions: dict[str, dict] = {}  # session_id -> {"messages": [...]}
        super().__init__(parent)

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

        # 默认创建一个会话
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

    def create_new_session(self) -> None:
        """新建一个会话并添加到列表中。"""
        session_id = uuid.uuid4().hex[:8]
        data = SessionData(
            session_id=session_id,
            title="新对话",
            preview="点击开始聊天~",
            avatar="🌸",
        )
        self._sessions[session_id] = {"messages": []}
        self._session_list.add_session(data)

    def switch_session(self, session_id: str) -> None:
        """切换到指定会话。

        Args:
            session_id: 目标会话 ID。
        """
        self._session_list.select_session(session_id)

    def _on_session_clicked(self, session_id: str) -> None:
        """会话被点击：恢复该会话的消息历史。

        Args:
            session_id: 会话 ID。
        """
        # 清空当前显示
        self._history.clear_history()
        self._current_agent_bubble = None

        # 恢复会话消息
        session = self._sessions.get(session_id, {"messages": []})
        for role, content in session["messages"]:
            bubble = self._history.append_message(role, content)
            if role == MessageRole.AGENT:
                self._current_agent_bubble = None  # 历史消息不参与流式更新

    def _on_session_deleted(self, session_id: str) -> None:
        """会话被删除。

        Args:
            session_id: 被删除的会话 ID。
        """
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
        session = self._sessions.setdefault(session_id, {"messages": []})
        session["messages"].append((role, content))

        # 更新会话列表的预览
        if role == MessageRole.USER:
            preview = content[:20] + ("..." if len(content) > 20 else "")
            self._session_list.update_session(
                SessionData(
                    session_id=session_id,
                    title=content[:12] + ("..." if len(content) > 12 else ""),
                    preview=preview,
                    avatar="🌸",
                )
            )
        else:
            preview = content[:20] + ("..." if len(content) > 20 else "")
            self._session_list.update_session(
                SessionData(
                    session_id=session_id,
                    title=session["messages"][0][1][:12] + ("..." if len(session["messages"][0][1]) > 12 else "") if session["messages"] else "新对话",
                    preview=preview,
                    avatar="🌸",
                )
            )

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
            self.append_agent_message(content)
        else:
            self.update_last_agent_message(content)
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
