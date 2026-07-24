import os
import sys
import time

from PySide6.QtCore import Qt, QThread, Signal, QRect, QTimer
from PySide6.QtGui import QCursor, QFont, QSurfaceFormat
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from core.agent_event import AgentEvent
from core.event_bus import event_bus
from windows.window_manager import WindowManager

try:
    import live2d.v3 as live2d
    LIVE2D_AVAILABLE = True
except ImportError:
    LIVE2D_AVAILABLE = False

from core.config import settings
from avatar.controller import Live2DController

class FakeAgentWorker(QThread):
    """模拟 Agent 回复工作线程。"""

    chunk_ready = Signal(str)
    reply_ready = Signal(AgentEvent)

    def __init__(self, user_text: str) -> None:
        super().__init__()
        self._user_text = user_text

    def run(self) -> None:
        """模拟流式回复。"""
        event_bus.agent_thinking_started.emit()
        time.sleep(0.8)
        event_bus.agent_thinking_finished.emit()

        reply = f"收到你的消息：{self._user_text}\n（这是模拟回复，后续接入 ChatAgent。）"
        for word in reply:
            self.chunk_ready.emit(word)
            time.sleep(0.02)

        event = AgentEvent(
            type="reply",
            payload={"content": reply},
        )
        self.reply_ready.emit(event)

# 保存活跃 worker 的集合，防止线程运行期间被 Python GC 销毁。
_active_workers: set[FakeAgentWorker] = set()


def on_user_message(text: str) -> None:
    """用户发送消息后启动模拟 Agent 回复。"""
    worker = FakeAgentWorker(text)

    worker.chunk_ready.connect(event_bus.agent_stream_chunk.emit)
    worker.reply_ready.connect(event_bus.agent_reply_received.emit)

    def _on_finished() -> None:
        _active_workers.discard(worker)
        worker.deleteLater()

    worker.finished.connect(_on_finished)

    _active_workers.add(worker)
    worker.start()





def main() -> None:
    """桌面 UI 演示主函数。"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    manager = WindowManager(app)

    # 构建 AvatarController（live2d 失败时自动 fallback）
    controller = Live2DController(settings)
    manager.set_avatar_controller(controller)

    # 注册示例 HitArea
    manager.lover_window.register_hit_area("head", QRect(0,0,settings.CHARACTER_WINDOW_SIZE[0], settings.CHARACTER_WINDOW_SIZE[1] // 6 ))
    manager.lover_window.register_hit_area("body", QRect(0,settings.CHARACTER_WINDOW_SIZE[0] // 6, settings.CHARACTER_WINDOW_SIZE[0], settings.CHARACTER_WINDOW_SIZE[1]))

    # 监听用户发送消息，模拟 Agent 回复
    event_bus.user_message_sent.connect(on_user_message)

    event_bus.application_quit_requested.connect((sys.exit))

    manager.run()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
