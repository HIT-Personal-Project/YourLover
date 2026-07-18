"""
桌面 UI 原型演示入口

运行方式（项目根目录）：
    conda activate YourLoverDesk
    python -m demos.desktop_ui_demo

说明：
- 使用 live2d-py 渲染真实 Avatar，并集成悬浮窗、右键菜单、聊天窗口、设置面板。
- 若 live2d 加载失败（如模型缺失），自动 fallback 到 FakeAvatarController 占位。
- 发送消息后会模拟 Agent 回复（用于验证事件流）。

重要架构说明（为什么 Live2D 必须用 QOpenGLWidget）：
- Live2D 的 LoadModelJson / Draw / Update 都依赖 OpenGL 上下文。
- 普通 QWidget 没有 GL 上下文，调用会直接闪退。
- 必须在 QOpenGLWidget 子类的 initializeGL() 里初始化 live2d、加载模型。
- paintGL() 由 Qt 自动调用，不能写在 Controller 里。
"""

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


# ============================================================
# 占位 Avatar（无 live2d-py 或加载失败时使用）
# ============================================================

class FakeAvatarWidget(QWidget):
    """模拟 Avatar 渲染控件（占位用）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(300, 380)
        self.setStyleSheet("background-color: transparent;")

        self._label = QLabel("🐱\nYourLover", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(50, 80, 200, 200)
        self._label.setFont(QFont("Segoe UI Emoji", 48))
        self._label.setStyleSheet(
            "background-color: rgba(255,255,255,180); border-radius: 20px;"
        )


class FakeAvatarController:
    """模拟 AvatarController（无 live2d-py 时使用）。"""

    def __init__(self) -> None:
        self._render_widget = FakeAvatarWidget()

    def get_render_widget(self) -> QWidget:
        return self._render_widget

    def on_drag(self, x: int, y: int) -> None:
        pass

    def on_update(self) -> None:
        pass

    def on_click(self, x: int, y: int) -> None:
        print(f"[FakeAvatarController] 原始点击: ({x}, {y})")

    def on_hit_area(self, area_name: str) -> None:
        print(f"[FakeAvatarController] 点击部位: {area_name}")

    def on_shake(self) -> None:
        print("[FakeAvatarController] 摇晃")

    def play_motion(self, motion_name: str) -> None:
        pass

    def change_expression(self, expression_name: str) -> None:
        pass

    def set_state(self, state_name: str) -> None:
        pass


# ============================================================
# 真正的 Live2D Avatar
# ============================================================

class Live2DAvatarWidget(QOpenGLWidget):
    """基于 live2d-py 的 Avatar 渲染控件（QOpenGLWidget 子类）。

    职责：
    - 在 initializeGL 中初始化 live2d 并加载模型（必须有 OpenGL 上下文）。
    - 通过 QTimer 每帧驱动 model.Drag / model.Update / self.update()。
    - 在 paintGL 中绘制模型。
    - 暴露 model 引用供 Controller 调用。
    """

    def __init__(self, model_path: str, parent: QWidget | None = None) -> None:
        """初始化渲染控件。

        Args:
            model_path: model3.json 路径。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self._model_path = model_path
        self.model = None  # LAppModel，initializeGL 中创建
        self._timer: QTimer | None = None          # 每帧渲染定时器
        self._idle_timer: QTimer | None = None     # Idle 动作检测定时器（低频）
        self._idle_check_interval_ms: int = 3000    # Idle 检测间隔（毫秒）
        self._init_ok: bool = False

        # 配置 OpenGL 表面格式（带 alpha 通道，用于透明背景）
        fmt = QSurfaceFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setSwapInterval(1)
        self.setFormat(fmt)

        # 透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        self.setFixedSize(300, 680)

    def initializeGL(self) -> None:
        """OpenGL 上下文创建完成后由 Qt 自动调用。

        这里才能调用 live2d.init() / glInit() / LoadModelJson。
        在 __init__ 里调用会导致崩溃。
        """
        try:
            live2d.init()
            live2d.glInit()
            live2d.enableLog(False)

            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self._model_path)
            self.model.Resize(self.width(), self.height())
            self.model.SetAutoBreathEnable(True)
            self.model.SetAutoBlinkEnable(True)

            # 播放 Idle 动作
            try:
                self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)
            except Exception:
                # 模型可能没有 Idle 动作组，忽略
                pass

            print(f"[Live2DAvatarWidget] 模型加载成功: {self._model_path}")
            self._init_ok = True
        except Exception as e:
            print(f"[Live2DAvatarWidget] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self._init_ok = False
            return

        # 启动每帧更新循环（约 60 FPS）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_frame)
        self._timer.start(16)

        # 启动 Idle 动作检测定时器（每 3 秒检查一次，低频，避免每帧检测）
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._on_idle_check)
        self._idle_timer.start(self._idle_check_interval_ms)

    def resizeGL(self, w: int, h: int) -> None:  # noqa: N802
        """窗口大小变化时同步模型视口。"""
        if self.model:
            self.model.Resize(w, h)

    def paintGL(self) -> None:  # noqa: N802
        """每帧绘制模型。由 Qt 在 self.update() 后自动调用。"""
        live2d.clearBuffer(0, 0, 0, 0)
        if self.model:
            try:
                self.model.Draw()
            except Exception:
                pass

    def _on_frame(self) -> None:
        """每帧回调：鼠标跟随 + 模型更新 + 请求重绘。

        注意：不要在这里递归调用自己！
        注意：Idle 动作检测放在 _idle_timer 里，避免每帧都检测。
        """
        if not self.model:
            return

        # 1. 鼠标跟随：把全局鼠标坐标转换为控件本地坐标
        cursor_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(cursor_pos)
        self.model.Drag(local_pos.x(), local_pos.y())

        # 2. 模型内部状态更新
        self.model.Update()

        # 3. 请求重绘（Qt 会在下一帧调用 paintGL）
        self.update()

    def _on_idle_check(self) -> None:
        """Idle 动作检测：每隔几秒检查一次，若动作已结束则播放 Idle。

        设计说明：
        - 放在独立 QTimer 里，避免每帧都调用 IsMotionFinished。
        - 检测间隔由 _idle_check_interval_ms 控制（默认 3000ms）。
        """
        if not self.model:
            return
        try:
            if self.model.IsMotionFinished():
                self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)
        except Exception as e:
            print(f"[Live2DAvatarWidget] Idle 检测异常: {e}")

    def paintGL(self) -> None:  # noqa: N802
        """每帧绘制模型。由 Qt 在 self.update() 后自动调用。"""
        live2d.clearBuffer(0, 0, 0, 0)
        if self.model:
            try:
                self.model.Draw()
            except Exception:
                pass


class Live2DAvatarController:
    """基于 live2d-py 的 AvatarController。

    实现 AvatarControllerProtocol，内部持有 Live2DAvatarWidget。
    所有交互最终委托给 model。
    """

    def __init__(self, model_path: str) -> None:
        """初始化 Controller。

        Args:
            model_path: model3.json 路径。
        """
        # 注意：创建 widget 时不会立即加载模型，模型加载在 initializeGL 中
        self._render_widget = Live2DAvatarWidget(model_path)

    @property
    def model(self) -> live2d.LAppModel | None:
        """返回 Live2D 模型实例（可能为 None，在 initializeGL 完成前）。"""
        return self._render_widget.model

    def get_render_widget(self) -> QWidget:
        """返回 Avatar 渲染控件。"""
        return self._render_widget

    def on_drag(self, x: int, y: int) -> None:
        """处理鼠标跟随（对应 Live2D 的 model.Drag）。

        说明：实际已在 Live2DAvatarWidget._on_frame 中调用，
        此处保留协议接口，外部也可主动调用。
        """
        if self.model:
            self.model.Drag(x, y)

    def on_update(self) -> None:
        """每帧更新 Avatar 内部状态（对应 Live2D 的 model.Update）。

        说明：实际已在 Live2DAvatarWidget._on_frame 中调用，
        此处保留协议接口。注意：不要递归调用自己！
        """
        if self.model:
            self.model.Update()

        if self.model.IsMotionFinished():
            self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)

    def on_click(self, x: int, y: int) -> None:
        """处理原始点击坐标（可调用 Live2D HitTest）。"""
        print(f"[Live2DAvatarController] 原始点击: ({x}, {y})")
        # TODO: 这里可以调用 self.model.HitTest("head", x, y) 检测命中部位

    def on_hit_area(self, area_name: str) -> None:
        """处理不同部位点击。"""
        print(f"[Live2DAvatarController] 点击部位: {area_name}")
        if area_name == "head":
            self.play_motion("Tap")
            self.change_expression("happy")
        elif area_name == "body":
            self.play_motion("Tap@Body")

    def on_shake(self) -> None:
        """处理摇晃。"""
        print("[Live2DAvatarController] 检测到摇晃")
        self.play_motion("FlickHead")

    def play_motion(self, motion_name: str) -> None:
        """播放指定动作组中的随机动作。"""
        if self.model:
            try:
                self.model.StartRandomMotion(
                    motion_name, live2d.MotionPriority.NORMAL
                )
            except Exception as e:
                print(f"[Live2DAvatarController] 动作播放失败 {motion_name}: {e}")


    def change_expression(self, expression_name: str) -> None:
        """切换表情。"""
        if self.model:
            try:
                self.model.SetExpression(expression_name)
            except Exception as e:
                print(f"[Live2DAvatarController] 表情切换失败 {expression_name}: {e}")

    def set_state(self, state_name: str) -> None:
        """设置 Avatar 状态（预留接口）。"""
        # TODO: 接入状态机
        print(f"[Live2DAvatarController] 设置状态: {state_name}")


# ============================================================
# 模拟 Agent 回复线程
# ============================================================

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


# ============================================================
# 入口
# ============================================================

# 默认模型路径（相对项目根目录）
DEFAULT_MODEL_PATH = "./assets/models/hiyori/hiyori_pro_t11.model3.json"


def build_avatar_controller():
    """构建 AvatarController。

    优先使用 Live2DAvatarController；若 live2d-py 不可用或模型文件不存在，
    则回退到 FakeAvatarController 占位。
    """
    if not LIVE2D_AVAILABLE:
        print("[Main] live2d-py 未安装，使用 FakeAvatarController")
        return FakeAvatarController()

    if not os.path.isfile(DEFAULT_MODEL_PATH):
        print(f"[Main] 模型文件不存在: {DEFAULT_MODEL_PATH}，使用 FakeAvatarController")
        return FakeAvatarController()

    try:
        controller = Live2DAvatarController(DEFAULT_MODEL_PATH)
        print("[Main] 使用 Live2DAvatarController")
        return controller
    except Exception as e:
        print(f"[Main] Live2DAvatarController 初始化异常: {e}，回退到 FakeAvatarController")
        return FakeAvatarController()


def main() -> None:
    """桌面 UI 演示主函数。"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    manager = WindowManager(app)

    # 构建 AvatarController（live2d 失败时自动 fallback）
    controller = build_avatar_controller()
    manager.set_avatar_controller(controller)

    # 注册示例 HitArea
    manager.lover_window.register_hit_area("head", QRect(100, 60, 100, 80))
    manager.lover_window.register_hit_area("body", QRect(90, 150, 120, 140))

    # 监听用户发送消息，模拟 Agent 回复
    event_bus.user_message_sent.connect(on_user_message)

    manager.run()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
