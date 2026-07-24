

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QSurfaceFormat
from PySide6.QtWidgets import (
    QWidget,
)
from PySide6.QtOpenGLWidgets import QOpenGLWidget

import live2d.v3 as live2d

from core.config import settings, Settings  



class Live2D(QOpenGLWidget):
    """基于 live2d-py 的 Avatar 渲染控件（QOpenGLWidget 子类）。

    职责：
    - 在 initializeGL 中初始化 live2d 并加载模型（必须有 OpenGL 上下文）。
    - 通过 QTimer 每帧驱动 model.Drag / model.Update / self.update()。
    - 在 paintGL 中绘制模型。
    - 暴露 model 引用供 Controller 调用。
    """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        """初始化渲染控件。

        Args:
            model_path: model3.json 路径。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self._model_path = settings.DEFAULT_MODEL_PATH
        self.model = None  # LAppModel，initializeGL 中创建
        self._timer: QTimer | None = None          # 每帧渲染定时器
        self._idle_timer: QTimer | None = None     # Idle 动作检测定时器（低频）
        self._idle_check_interval_ms: int = 10000    # Idle 检测间隔（毫秒）
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

        self.setFixedSize(*settings.CHARACTER_WINDOW_SIZE)

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
            self.model.Resize(*settings.CHARACTER_WINDOW_SIZE)
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


    def play_motion(self, motion_name: str) -> None:
        """播放指定动作。"""
        if self.model:
            self.model.StartRandomMotion(motion_name, live2d.MotionPriority.IDLE)

    def change_expression(self, expression: str) -> None:
        """改变角色表情。"""
        if self.model:
            self.model.SetExpression(expression)

    def clear_expression(self) -> None:
        """清除角色表情。"""
        if self.model:
            self.model.ResetExpressions()

    def stop_motion(self) -> None:
        """停止当前动作。"""
        if self.model:
            self.model.StopAllMotions()


    