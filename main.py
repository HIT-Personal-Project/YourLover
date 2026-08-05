"""
YourLover 桌面助手主入口

职责：
- 初始化 QApplication 与 WindowManager。
- 注入 Live2DController 作为 AvatarController。
- 初始化 AgentController 并连接 LLM（Ollama）。
- 监听用户消息，通过 AgentWorker 线程调用 AgentController.chat()，
  将回复通过 EventBus 发送给聊天窗口。

设计说明：
- AgentController.chat() 是同步阻塞调用（LangGraph invoke），不能在主线程调用，
  否则会卡住 UI。因此用 AgentWorker(QThread) 包装。
- AgentWorker 运行期间必须保持 Python 引用，否则会触发
  "QThread: Destroyed while thread is still running"。
"""

import sys
import traceback

from PySide6.QtCore import QRect, QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication

from agent.agent_controller import AgentController, AgentMessage
from core.agent_event import AgentEvent
from core.config import settings
from core.event_bus import event_bus
from windows.window_manager import WindowManager

import time


# ============================================================
# Agent 工作线程
# ============================================================

class AgentWorker(QThread):
    """调用 AgentController.chat() 的工作线程。

    设计说明：
    - AgentController.chat() 内部调用 LangGraph invoke，是同步阻塞的。
    - 在主线程调用会卡住 UI，因此放到 QThread 中执行。
    - 完成后通过 reply_ready 信号把 AgentMessage 发回主线程。
    - mini_chat 模式下发射 mini_chat_thinking_started（角色头顶气泡），
      否则发射 agent_thinking_started（大聊天窗口）。

    信号：
    - reply_ready(AgentMessage): chat() 完成后发射，携带回复结果。
    """

    reply_ready = Signal(object)  # AgentMessage 实例

    def __init__(
        self,
        agent_controller: AgentController,
        user_text: str,
        mini_chat: bool = False,
        configurable: dict | None = None,
    ) -> None:
        """初始化工作线程。

        Args:
            agent_controller: AgentController 实例。
            user_text: 用户输入文本。
            mini_chat: True 表示迷你聊天模式，思考信号走 mini_chat_thinking_started。
            configurable: 可选的会话配置（含 session_id），用于区分不同会话。
                         None 表示使用 AgentController 默认配置。
        """
        super().__init__()
        self._agent_controller = agent_controller
        self._user_text = user_text
        self._mini_chat = mini_chat
        self._configurable = configurable

    def run(self) -> None:
        """执行 chat() 调用。

        流程：
        1. 发射 thinking 信号通知 UI 显示"思考中"。
        2. 调用 AgentController.chat_test()（后续可切换为 chat()）。
        3. 仅在大聊天模式下发射 agent_thinking_finished（迷你聊天不走大窗口）。
        4. 通过 reply_ready 把结果发回主线程。
        5. 若 chat() 抛异常，把错误信息包装成 AgentMessage 返回。
        """
        if self._mini_chat:
            event_bus.mini_chat_thinking_started.emit()
        else:
            event_bus.agent_thinking_started.emit()

        try:
            result = self._agent_controller.chat(
                self._user_text, self._configurable
            )
            # time.sleep(5)
            if not self._mini_chat:
                event_bus.agent_thinking_finished.emit()
            self.reply_ready.emit(result)
        except Exception as exc:
            if not self._mini_chat:
                event_bus.agent_thinking_finished.emit()
            traceback.print_exc()
            # 异常时返回错误提示，不让 UI 卡在"思考中"
            self.reply_ready.emit(AgentMessage(f"出错了：{exc}", "Sad"))


# ============================================================
# 全局状态
# ============================================================

# AgentController 全局实例（在 main() 中初始化）
_agent_controller: AgentController | None = None

# 保存活跃 worker 的集合，防止线程运行期间被 Python GC 销毁
_active_workers: set[AgentWorker] = set()

# AgentController 启动时返回的系统提示（如"连接成功了！"），延迟显示在迷你聊天气泡
_startup_message: str | None = None


# ============================================================
# 消息处理
# ============================================================

def on_user_message(text: str) -> None:
    """用户发送消息后启动 AgentWorker 调用 AgentController.chat()。

    设计说明：
    - 每次发送消息创建一个 AgentWorker，避免并发调用 chat() 时的状态冲突。
    - worker 运行期间用 _active_workers 保持引用，防止 GC。
    - worker 结束后自动清理引用并 deleteLater。
    """
    if _agent_controller is None:
        event_bus.agent_reply_received.emit(
            AgentEvent(type="error", payload={"content": "AgentController 未初始化"})
        )
        return

    worker = AgentWorker(_agent_controller, text)

    # chat() 完成后，把 AgentMessage 包装成 AgentEvent 发送
    worker.reply_ready.connect(_on_agent_reply)
    # 线程结束后清理引用
    worker.finished.connect(lambda: _cleanup_worker(worker))

    _active_workers.add(worker)
    worker.start()


def _on_agent_reply(agent_message: AgentMessage) -> None:
    """将 AgentMessage 包装成 AgentEvent，通过 EventBus 发送给聊天窗口。
        同时更新角色状态 emotion和好感度
    Args:
        agent_message: AgentController.chat() 返回的 AgentMessage。
    """
    # AgentMessage 有两种构造方式，属性可能不同，做兼容处理
    content = (
        getattr(agent_message, "msg", None)
        or getattr(agent_message, "message", None)
        or str(agent_message)
    )
    emotion = getattr(agent_message, "ai_emo", None)

    event = AgentEvent(
        type="reply",
        payload={"content": str(content), "emotion": emotion},
    )

    event_bus.agent_reply_received.emit(event)
    event_bus.state_emotion_change.emit(emotion)
    event_bus.state_love_change.emit(90)

def _cleanup_worker(worker: AgentWorker) -> None:
    """线程结束后清理引用。

    Args:
        worker: 已完成的 AgentWorker。
    """
    _active_workers.discard(worker)
    worker.deleteLater()


# ============================================================
# 迷你聊天（快速对话）消息处理
# ============================================================

def on_mini_chat_message(text: str) -> None:
    """迷你聊天消息处理：通过 AgentWorker 调用 AgentController。

    与 on_user_message 的区别：
    - 使用 mini_chat=True 模式，思考信号走 mini_chat_thinking_started。
    - 使用固定的 session_id="mini-chat"，与大聊天窗口会话隔离。
    - 回复通过 mini_chat_reply_received 发送给角色头顶气泡，不走大聊天窗口。
    """
    if _agent_controller is None:
        event_bus.mini_chat_reply_received.emit("AgentController 未初始化")
        return

    # 迷你聊天使用固定的 session_id，与大聊天窗口互不影响
    mini_configurable = {
        "user_id": "default-user",
        "session_id": "mini-chat",
    }

    worker = AgentWorker(
        _agent_controller, text, mini_chat=True, configurable=mini_configurable
    )

    # chat() 完成后，把 AgentMessage 文本通过 mini_chat_reply_received 发送
    worker.reply_ready.connect(_on_mini_chat_reply)
    worker.finished.connect(lambda: _cleanup_worker(worker))

    _active_workers.add(worker)
    worker.start()


def on_chat_session_changed(session_id: str) -> None:
    """聊天窗口切换/新建会话时，更新 AgentController 的 session_id。

    设计说明：
    - 大聊天窗口的每个会话都有独立的 session_id，确保 Agent 记忆隔离。
    - 迷你聊天的 session_id 固定为 "mini-chat"，不受此函数影响。

    Args:
        session_id: 新的会话 ID。
    """
    if _agent_controller is not None:
        _agent_controller.configurable["session_id"] = session_id
        print(f"[main] 切换到会话: {session_id}")


def _on_mini_chat_reply(agent_message: AgentMessage) -> None:
    """迷你聊天回复：提取文本，通过 mini_chat_reply_received 发送给头顶气泡。

    Args:
        agent_message: AgentController.chat() 返回的 AgentMessage。
    """
    content = (
        getattr(agent_message, "msg", None)
        or getattr(agent_message, "message", None)
        or str(agent_message)
    )
    event_bus.mini_chat_reply_received.emit(str(content))


# ============================================================
# AgentController 初始化
# ============================================================

def init_agent_controller() -> None:
    """初始化 AgentController 并连接 LLM。

    设计说明：
    - 使用 settings 中的配置（Ollama + qwen2.5:3b）连接 LLM。
    - 连接结果（如"连接成功了！现在可以开始聊天了！"）保存到 _startup_message，
      延迟到 UI 就绪后通过 mini_chat_reply_received 显示在角色头顶气泡。
    - 连接失败时打印错误，但不阻塞 UI 启动（用户仍可使用其他功能）。
    """
    global _agent_controller, _startup_message

    configurable = {
        "user_id": "default-user",
        "session_id": "default-session",
    }

    _agent_controller = AgentController(settings, configurable)

    # 连接 LLM（Ollama）
    try:
        message = _agent_controller.APIConnect(
            LLM_type="ollama",
            LLM_name=settings.CHAT_MODEL_NAME,
        )
        _startup_message = getattr(message, "msg", None) or str(message)
        print(f"[main] AgentController 连接结果: {_startup_message}")
    except Exception as exc:
        _startup_message = f"连接失败: {exc}"
        print(f"[main] AgentController 连接失败: {exc}")
        traceback.print_exc()


# ============================================================
# 主函数
# ============================================================

def main() -> None:
    """桌面助手主入口。"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 初始化窗口管理器
    manager = WindowManager(app)

    # 注入 AvatarController（Live2D）
    from avatar.controller import Live2DController
    avatar_controller = Live2DController(settings)
    manager.set_avatar_controller(avatar_controller)

    # 注册示例 HitArea（根据窗口尺寸划分头部和身体）
    win_w, win_h = settings.CHARACTER_WINDOW_SIZE
    manager.lover_window.register_hit_area(
        "head", QRect(0, 0, win_w, win_h // 6)
    )
    manager.lover_window.register_hit_area(
        "body", QRect(0, win_h // 6, win_w, win_h - win_h // 6)
    )

    # 初始化 AgentController 并连接 LLM
    init_agent_controller()

    # 监听用户发送消息，启动 Agent 回复
    event_bus.user_message_sent.connect(on_user_message)

    # 监听迷你聊天消息，启动 Agent 回复（回复显示在角色头顶气泡）
    event_bus.mini_chat_input_sent.connect(on_mini_chat_message)

    # 监听聊天窗口会话切换，更新 AgentController 的 session_id
    event_bus.chat_session_changed.connect(on_chat_session_changed)

    # 退出应用
    event_bus.application_quit_requested.connect(sys.exit)

    manager.run()

    # 延迟显示 AgentController 连接结果（系统提示），确保 UI 已就绪
    # 例如"连接成功了！现在可以开始聊天了！"会自动显示在角色头顶气泡
    if _startup_message:
        QTimer.singleShot(800, lambda: event_bus.mini_chat_reply_received.emit(_startup_message))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
