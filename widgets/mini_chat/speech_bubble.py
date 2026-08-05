"""角色头顶对话气泡组件。

职责：
- 在角色上方显示对话内容或"思考中"状态。
- 卡通游戏风格：圆角矩形 + 底部小三角尾巴指向角色。
- 白底粉色边框，自动适应文本长度。
- 支持自动隐藏（定时器）。

使用方式：
    bubble = SpeechBubble()
    bubble.show_thinking()          # 显示"思考中..."
    bubble.show_message("你好呀！")  # 显示回复内容
    bubble.hide_bubble()             # 隐藏气泡
"""

from PySide6.QtCore import Qt, QTimer, QRectF, QSize
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QFontMetrics,
)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from widgets.base.base_widget import BaseWidget


class SpeechBubble(BaseWidget):
    """角色头顶对话气泡。

    职责：
    - 显示 Agent 回复文本或思考状态。
    - 卡通风格：白色圆角矩形 + 粉色边框 + 底部三角尾巴。
    - 自动根据文本长度调整大小。
    - 支持定时自动隐藏。

    暴露接口：
    - show_message(text): 显示对话内容，并启动自动隐藏定时器。
    - show_thinking(): 显示"思考中..."状态。
    - hide_bubble(): 立即隐藏气泡。
    - set_auto_hide(seconds): 设置自动隐藏秒数，0 表示不自动隐藏。
    """

    # 尾巴与圆角参数
    _TAIL_WIDTH = 24       # 底部尾巴宽度
    _TAIL_HEIGHT = 14       # 底部尾巴高度
    _CORNER_RADIUS = 18   # 圆角半径
    _BUBBLE_PADDING = 16   # 内边距
    _MAX_BUBBLE_WIDTH = 320  # 最大宽度
    _MIN_BUBBLE_WIDTH = 80   # 最小宽度

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化对话气泡。

        Args:
            parent: 父级 QWidget。
        """
        # 注意：Qt 对象（QTimer）必须在 super().__init__() 之后创建
        self._text: str = ""
        self._thinking: bool = False
        self._auto_hide_seconds: int = 8
        self._thinking_dot_count: int = 0
        super().__init__(parent)
        # 以下 Qt 对象在基类初始化后创建
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide_bubble)

        # 思考动画定时器（循环 "思考中" / "思考中." / "思考中.." / "思考中..."）
        self._thinking_timer = QTimer(self)
        self._thinking_timer.timeout.connect(self._update_thinking_text)

    def setup_ui(self) -> None:
        """创建气泡内部布局与文本标签。"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            self._BUBBLE_PADDING,
            self._BUBBLE_PADDING,
            self._BUBBLE_PADDING,
            self._BUBBLE_PADDING + self._TAIL_HEIGHT,  # 底部留出尾巴空间
        )

        self._label = QLabel(self)
        self._label.setObjectName("bubble_text")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setFont(QFont("Microsoft YaHei", 10))
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setStyleSheet(
            """
            QLabel#bubble_text {
                color: #1e293b;
                background: transparent;
                border: none;
            }
            """
        )
        self._layout.addWidget(self._label)

    def connect_signals(self) -> None:
        """气泡内部无外部信号需要连接。"""
        pass

    def apply_style(self) -> None:
        """气泡样式由 paintEvent 绘制，这里设置窗口透明与无边框。"""
        # 必须设置 FramelessWindowHint，否则会有 Windows 外框 + 最小尺寸限制
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

    def paintEvent(self, event) -> None:  # noqa: N802
        """绘制卡通气泡形状：圆角矩形 + 底部三角尾巴。

        绘制流程：
        1. 主体为圆角矩形（顶部到底部减去尾巴高度）。
        2. 底部中央延伸出三角形尾巴指向角色。
        3. 白色填充 + 粉色边框。
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = self._CORNER_RADIUS
        tw = self._TAIL_WIDTH
        th = self._TAIL_HEIGHT
        body_h = h - th  # 主体高度（不含尾巴）

        if body_h <= 0:
            return

        path = QPainterPath()

        # 从左上圆角右侧开始，顺时针绘制
        path.moveTo(r, 0)
        # 上边
        path.lineTo(w - r, 0)
        # 右上圆角
        path.arcTo(QRectF(w - 2 * r, 0, 2 * r, 2 * r), 90, -90)
        # 右边
        path.lineTo(w, body_h - r)
        # 右下圆角
        path.arcTo(QRectF(w - 2 * r, body_h - 2 * r, 2 * r, 2 * r), 0, -90)
        # 下边到尾巴右点
        tail_center_x = w / 2
        path.lineTo(tail_center_x + tw / 2, body_h)
        # 尾巴尖（向下）
        path.lineTo(tail_center_x, h)
        # 尾巴左点
        path.lineTo(tail_center_x - tw / 2, body_h)
        # 下边到左下圆角
        path.lineTo(r, body_h)
        # 左下圆角
        path.arcTo(QRectF(0, body_h - 2 * r, 2 * r, 2 * r), 270, -90)
        # 左边
        path.lineTo(0, r)
        # 左上圆角
        path.arcTo(QRectF(0, 0, 2 * r, 2 * r), 180, -90)

        # 填充白色，描边粉色
        painter.setPen(QPen(QColor("#ec4899"), 2))
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawPath(path)

    # ============================================================
    # 公共接口
    # ============================================================

    def show_message(self, text: str) -> None:
        """显示对话内容。

        Args:
            text: 要显示的文本。
        """
        self._thinking = False
        self._thinking_timer.stop()
        self._text = text
        self._label.setText(text)
        self._update_size()
        self.show()
        self.raise_()

        # 启动自动隐藏定时器
        if self._auto_hide_seconds > 0:
            self._auto_hide_timer.start(self._auto_hide_seconds * 1000)

    def show_thinking(self) -> None:
        """显示"思考中"状态（带动画省略号）。"""
        self._auto_hide_timer.stop()
        self._thinking = True
        self._thinking_dot_count = 0
        self._update_thinking_text()
        self._update_size()
        self.show()
        self.raise_()

        # 启动思考动画
        self._thinking_timer.start(400)

    def hide_bubble(self) -> None:
        """立即隐藏气泡。"""
        self._thinking = False
        self._thinking_timer.stop()
        self._auto_hide_timer.stop()
        self.hide()

    def set_auto_hide(self, seconds: int) -> None:
        """设置自动隐藏时间。

        Args:
            seconds: 秒数，0 表示不自动隐藏。
        """
        self._auto_hide_seconds = seconds

    # ============================================================
    # 内部方法
    # ============================================================

    def _update_thinking_text(self) -> None:
        """更新思考中文本（循环显示省略号动画）。"""
        dots = "." * self._thinking_dot_count
        self._label.setText(f"💭 思考中{dots}")
        self._thinking_dot_count = (self._thinking_dot_count + 1) % 4
        self._update_size()

    def _update_size(self) -> None:
        """根据文本内容自动调整气泡大小。"""
        text = self._label.text()
        font = self._label.font()
        fm = QFontMetrics(font)

        # 计算文本所需宽高（考虑自动换行）
        # PySide6 的 boundingRect 需要 QRect（整数）而非 QRectF
        max_text_width = self._MAX_BUBBLE_WIDTH - 2 * self._BUBBLE_PADDING
        text_rect = fm.boundingRect(
            0, 0, max_text_width, 10000,
            int(Qt.TextFlag.TextWordWrap),
            text,
        )

        # 气泡宽度 = 文本宽度 + 内边距，限制在 [min, max] 范围
        bubble_width = text_rect.width() + 2 * self._BUBBLE_PADDING
        bubble_width = max(self._MIN_BUBBLE_WIDTH, min(self._MAX_BUBBLE_WIDTH, bubble_width))

        # 气泡高度 = 文本高度 + 内边距 + 尾巴高度
        bubble_height = text_rect.height() + 2 * self._BUBBLE_PADDING + self._TAIL_HEIGHT

        self.setFixedSize(int(bubble_width), int(bubble_height))

    def sizeHint(self) -> QSize:  # noqa: N802
        """返回建议大小。"""
        return QSize(self._MAX_BUBBLE_WIDTH, 80)
