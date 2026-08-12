"""
应用程序核心模块

职责：
- 管理应用程序整体生命周期（QApplication 创建、运行、退出）。
- 初始化并持有所有核心组件（WindowManager、AvatarController、AgentController）。
- 注册 EventBus 信号路由（用户消息、迷你聊天、会话切换）。
- 管理 AgentWorker 工作线程的创建与回收，防止 GC 销毁运行中的 QThread。
- 协调各模块之间的交互。

设计说明：
- App 是桌面助手的唯一顶层协调者，main.py 仅作为启动入口。
- AgentController.chat() 内部调用 LangGraph invoke，是同步阻塞的，不能在主线程调用，
  否则会卡住 UI。因此通过 AgentWorker(QThread) 异步执行。
- AgentWorker 运行期间由 App 持有引用（_active_workers），防止
  "QThread: Destroyed while thread is still running"。
"""

import sys
import traceback
from typing import Dict, Any

from PySide6.QtCore import QRect, QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication

from agent.agent_controller import AgentController, AgentMessage
from core.agent_event import AgentEvent
from core.event_bus import event_bus
from windows.window_manager import WindowManager

from utils.config_manager import config
from avatar.controller import Live2DController



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
        2. 调用 AgentController.chat()。
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
            if not self._mini_chat:
                event_bus.agent_thinking_finished.emit()
            self.reply_ready.emit(result)
        
        except Exception as exc:
            if not self._mini_chat:
                event_bus.agent_thinking_finished.emit()
            traceback.print_exc()
            # 异常时返回错误提示，不让 UI 卡在"思考中"
            self.reply_ready.emit(AgentMessage(f"出错了：{exc}", "Sad"))

        finally:
            event_bus.avatar_expression_clear.emit()


# ============================================================
# 应用核心类
# ============================================================

class App:
    """桌面助手应用核心，管理整体生命周期。

    职责：
    - 创建并持有 QApplication、WindowManager、AvatarController、AgentController。
    - 注册 EventBus 信号到本类的处理方法。
    - 管理 AgentWorker 工作线程集合，防止运行期间被 GC。

    暴露接口：
    - run(): 启动窗口管理器并进入 Qt 事件循环，返回退出码。
    - quit(): 退出应用（委托给 WindowManager.quit()）。
    """

    def __init__(self) -> None:
        """初始化应用核心。

        流程：
        1. 创建 QApplication 并配置"最后一个窗口关闭也不退出"。
        2. 创建 WindowManager。
        3. 注入 AvatarController（Live2D）。
        4. 注册示例 HitArea（头部 / 身体）。
        5. 初始化 AgentController 并连接 LLM。
        6. 注册 EventBus 信号路由。
        """
        # QApplication 实例（生命周期由 App 持有）
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        # 窗口管理器
        self._window_manager = WindowManager(self._app)

        # 注入 AvatarController（Live2D）
        self._avatar_controller = Live2DController(config)
        self._window_manager.set_avatar_controller(self._avatar_controller)

        # 注册示例 HitArea（根据窗口尺寸划分头部和身体）
        win_w, win_h = config.CHARACTER_WINDOW_SIZE
        self._window_manager.lover_window.register_hit_area(
            "head", QRect(0, 0, win_w, win_h // 6)
        )
        self._window_manager.lover_window.register_hit_area(
            "body", QRect(0, win_h // 6, win_w, win_h - win_h // 6)
        )

        # Agent 相关状态
        self._agent_controller: AgentController | None = None
        # 保存活跃 worker 的集合，防止线程运行期间被 Python GC 销毁
        self._active_workers: set[AgentWorker] = set()
        # AgentController 启动时返回的系统提示（如"连接成功了！"），延迟显示在迷你聊天气泡
        self._startup_message: str | None = None

        # 初始化 AgentController 并连接 LLM
        self._init_agent_controller()

        # 注册 EventBus 信号路由
        self._setup_event_routing()

    # ============================================================
    # AgentController 初始化
    # ============================================================

    def _init_agent_controller(self) -> None:
        """初始化 AgentController 并连接 LLM。

        设计说明：
        - 使用 settings 中的配置（Ollama + qwen2.5:3b）连接 LLM。
        - 连接结果（如"连接成功了！现在可以开始聊天了！"）保存到 _startup_message，
          延迟到 UI 就绪后通过 mini_chat_reply_received 显示在角色头顶气泡。
        - 连接失败时打印错误，但不阻塞 UI 启动（用户仍可使用其他功能）。
        """
        configurable = {
            "user_id": "default-user",
            "session_id": "default-session",
        }

        self._agent_controller = AgentController(config, configurable)

        # 连接 LLM（Ollama）
        try:
            message = self._agent_controller.APIConnect(
                LLM_type="ollama",
                LLM_name=config.CHAT_MODEL_NAME,
            )
            self._startup_message = getattr(message, "msg", None) or str(message)
            print(f"[app] AgentController 连接结果: {self._startup_message}")
        except Exception as exc:
            self._startup_message = f"连接失败: {exc}"
            print(f"[app] AgentController 连接失败: {exc}")
            traceback.print_exc()

    # ============================================================
    # EventBus 信号路由
    # ============================================================

    def _setup_event_routing(self) -> None:
        """配置 EventBus 信号路由到本类的处理方法。

        路由：
        - user_message_sent        -> _on_user_message（大聊天消息）
        - mini_chat_input_sent     -> _on_mini_chat_message（迷你聊天消息）
        - chat_session_changed     -> _on_chat_session_changed（会话切换）
        """
        # 监听用户发送消息，启动 Agent 回复
        event_bus.user_message_sent.connect(self._on_user_message)

        # 监听迷你聊天消息，启动 Agent 回复（回复显示在角色头顶气泡）
        event_bus.mini_chat_input_sent.connect(self._on_mini_chat_message)

        # 监听聊天窗口会话切换，更新 AgentController 的 session_id
        event_bus.chat_session_changed.connect(self._on_chat_session_changed)


        event_bus.settings_batch_changed.connect(self._on_config_update)

        # 2D模型管理
        event_bus.avatar_expression_clear.connect(self._avatar_controller.clear_expression)


    # ============================================================
    # 大聊天消息处理
    # ============================================================

    def _on_user_message(self, text: str) -> None:
        """用户发送消息后启动 AgentWorker 调用 AgentController.chat()。

        设计说明：
        - 每次发送消息创建一个 AgentWorker，避免并发调用 chat() 时的状态冲突。
        - worker 运行期间用 _active_workers 保持引用，防止 GC。
        - worker 结束后自动清理引用并 deleteLater。
        """
        if self._agent_controller is None:
            event_bus.agent_reply_received.emit(
                AgentEvent(type="error", payload={"content": "AgentController 未初始化"})
            )
            return

        worker = AgentWorker(self._agent_controller, text)

        # chat() 完成后，把 AgentMessage 包装成 AgentEvent 发送
        worker.reply_ready.connect(self._on_agent_reply)
        # 线程结束后清理引用
        worker.finished.connect(lambda: self._cleanup_worker(worker))

        self._active_workers.add(worker)
        worker.start()

    def _on_agent_reply(self, agent_message: AgentMessage) -> None:
        """将 AgentMessage 包装成 AgentEvent，通过 EventBus 发送给聊天窗口。
        同时更新角色状态 emotion 和好感度。

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

    def _cleanup_worker(self, worker: AgentWorker) -> None:
        """线程结束后清理引用。

        Args:
            worker: 已完成的 AgentWorker。
        """
        self._active_workers.discard(worker)
        worker.deleteLater()

    # ============================================================
    # 迷你聊天（快速对话）消息处理
    # ============================================================

    def _on_mini_chat_message(self, text: str) -> None:
        """迷你聊天消息处理：通过 AgentWorker 调用 AgentController。

        与 _on_user_message 的区别：
        - 使用 mini_chat=True 模式，思考信号走 mini_chat_thinking_started。
        - 使用固定的 session_id="mini-chat"，与大聊天窗口会话隔离。
        - 回复通过 mini_chat_reply_received 发送给角色头顶气泡，不走大聊天窗口。
        """
        if self._agent_controller is None:
            event_bus.mini_chat_reply_received.emit("AgentController 未初始化")
            return

        # 迷你聊天使用固定的 session_id，与大聊天窗口互不影响
        mini_configurable = {
            "user_id": "default-user",
            "session_id": "mini-chat",
        }

        worker = AgentWorker(
            self._agent_controller, text, mini_chat=True, configurable=mini_configurable
        )

        # chat() 完成后，把 AgentMessage 文本通过 mini_chat_reply_received 发送
        worker.reply_ready.connect(self._on_mini_chat_reply)
        worker.finished.connect(lambda: self._cleanup_worker(worker))

        self._active_workers.add(worker)
        worker.start()

    def _on_mini_chat_reply(self, agent_message: AgentMessage) -> None:
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
        emotion = getattr(agent_message, "ai_emo", "Happy")
        self._avatar_controller.speak(emotion)

    def _on_chat_session_changed(self, session_id: str) -> None:
        """聊天窗口切换/新建会话时，更新 AgentController 的 session_id。

        设计说明：
        - 大聊天窗口的每个会话都有独立的 session_id，确保 Agent 记忆隔离。
        - 迷你聊天的 session_id 固定为 "mini-chat"，不受此方法影响。

        Args:
            session_id: 新的会话 ID。
        """
        if self._agent_controller is not None:
            self._agent_controller.configurable["session_id"] = session_id
            print(f"[app] 切换到会话: {session_id}")

    # ============================================================
    # 生命周期管理
    # ============================================================

    def run(self) -> int:
        """启动应用：显示窗口并进入 Qt 事件循环。

        流程：
        1. 启动 WindowManager（显示悬浮宠物窗口与迷你聊天浮层）。
        2. 延迟 800ms 通过 mini_chat_reply_received 显示 AgentController 连接结果，
           确保 UI 已就绪（例如"连接成功了！现在可以开始聊天了！"）。
        3. 进入 Qt 事件循环，返回退出码。

        Returns:
            QApplication 退出码。
        """
        self._window_manager.run()

        # 延迟显示 AgentController 连接结果（系统提示），确保 UI 已就绪
        # 例如"连接成功了！现在可以开始聊天了！"会自动显示在角色头顶气泡
        if self._startup_message:
            QTimer.singleShot(
                800,
                lambda: event_bus.mini_chat_reply_received.emit(self._startup_message),
            )

        return self._app.exec()

    def quit(self) -> None:
        """退出应用（委托给 WindowManager.quit()，走 QApplication.quit() 释放 Qt 资源）。"""
        self._window_manager.quit()


    def _on_config_update(self) -> None:
        """配置项更新时，通知所有监听器。更新所对应的模块。重新载入配置文件和模块。"""
        
        del self._avatar_controller
        self._avatar_controller = Live2DController(config)
        
        self._window_manager.set_avatar_controller(self._avatar_controller)

        # 注册示例 HitArea（根据窗口尺寸划分头部和身体）
        win_w, win_h = config.CHARACTER_WINDOW_SIZE
        self._window_manager.lover_window.register_hit_area(
            "head", QRect(0, 0, win_w, win_h // 6)
        )
        self._window_manager.lover_window.register_hit_area(
            "body", QRect(0, win_h // 6, win_w, win_h - win_h // 6)
        )

        # 重新初始化 AgentController 并连接 LLM
        self._init_agent_controller()

        if self._startup_message:
            QTimer.singleShot(
                800,
                lambda: event_bus.mini_chat_reply_received.emit(self._startup_message),
            )


# ============================================================
# 模块入口
# ============================================================

def main() -> int:
    """应用入口：创建 App 并运行。"""
    application = App()
    return application.run()


if __name__ == "__main__":
    sys.exit(main())
