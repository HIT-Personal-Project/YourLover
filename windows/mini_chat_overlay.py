"""迷你聊天浮层窗口。

职责：
- 在角色下方显示一个 💬 聊天按钮（始终可见）。
- 点击按钮展开输入框，用户可输入消息快速对话。
- 用户发送消息后，在角色上方显示对话气泡（思考中 → 回复内容）。
- 跟踪 LoverWindow 位置，自动调整自身与气泡位置。

设计说明：
- 本窗口不依赖 ChatWindow，是独立的小型对话入口。
- 发送的消息通过 EventBus（mini_chat_input_sent）广播，由业务层处理。
- 回复通过 mini_chat_reply_received 接收，显示在角色头顶 SpeechBubble 中。
- 不影响原有大聊天窗口（ChatWindow）的功能。

事件流：
    点击💬 → 展开输入 → 输入文本 → mini_chat_input_sent.emit(text)
        → 业务层 Agent 处理 → mini_chat_thinking_started.emit()
            → SpeechBubble 显示"思考中..."
        → Agent 回复完成 → mini_chat_reply_received.emit(reply)
            → SpeechBubble 显示回复内容
            → 自动隐藏（8秒后）
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from core.event_bus import event_bus
from windows.base_window import BaseWindow
from widgets.mini_chat.speech_bubble import SpeechBubble


class MiniChatOverlay(BaseWindow):
    """迷你聊天浮层窗口。

    职责：
    - 在角色下方显示 💬 按钮 / 展开后显示输入框。
    - 管理角色头顶的 SpeechBubble。
    - 跟踪 LoverWindow 位置自动跟随。

    暴露接口：
    - set_target_window(window): 设置跟踪的目标窗口（LoverWindow）。
    - expand(): 展开输入框。
    - collapse(): 收起输入框。
    - show_reply(text): 显示回复气泡。
    - show_thinking(): 显示思考气泡。
    - hide_bubble(): 隐藏气泡。

    信号：
    - 无外部信号，通过 EventBus 通信。
    """

    # 收起状态下按钮尺寸
    _COLLAPSED_WIDTH = 56
    _COLLAPSED_HEIGHT = 56
    # 展开状态下输入区尺寸
    _EXPANDED_WIDTH = 320
    _EXPANDED_HEIGHT = 52
    # 按钮与角色右下角的重叠偏移（正值=往外移，负值=往内移）
    _CORNER_OFFSET_X = -12
    _CORNER_OFFSET_Y = -12
    # 气泡与角色之间的间距
    _BUBBLE_OFFSET_Y = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化迷你聊天浮层。

        Args:
            parent: 父级窗口，通常为空。
        """
        self._target_window: QWidget | None = None
        self._expanded: bool = False
        # 注意：SpeechBubble 是 QWidget，必须在 super().__init__() 之后创建
        self._bubble: SpeechBubble | None = None
        super().__init__(parent)
        # 基类初始化后创建气泡
        self._bubble = SpeechBubble()

    def _setup_window_flags(self) -> None:
        """配置浮层窗口标志：无边框、透明、置顶、不在任务栏显示。"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def setup_ui(self) -> None:
        """创建浮层 UI：💬按钮 + 输入框 + 发送按钮 + 关闭按钮。"""
        self._central = QWidget(self)
        self._central.setObjectName("mini_chat_central")
        self.setCentralWidget(self._central)

        self._layout = QHBoxLayout(self._central)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(6)

        # 💬 聊天按钮（收起状态下唯一可见控件）
        self._toggle_button = QPushButton("💬", self._central)
        self._toggle_button.setObjectName("mini_chat_toggle")
        self._toggle_button.setFixedSize(self._COLLAPSED_WIDTH - 8, self._COLLAPSED_HEIGHT - 8)
        self._toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_button.setFont(QFont("Segoe UI Emoji", 20))

        # 输入框（展开状态下可见）
        self._input = QLineEdit(self._central)
        self._input.setObjectName("mini_chat_input")
        self._input.setPlaceholderText("说点什么...")
        self._input.setFixedHeight(36)
        self._input.setFont(QFont("Microsoft YaHei", 10))

        # 发送按钮（展开状态下可见）
        self._send_button = QPushButton("➤", self._central)
        self._send_button.setObjectName("mini_chat_send")
        self._send_button.setFixedSize(40, 36)
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.setFont(QFont("Segoe UI Emoji", 14))

        # 关闭按钮（展开状态下可见，点击收起）
        self._close_button = QPushButton("✕", self._central)
        self._close_button.setObjectName("mini_chat_close")
        self._close_button.setFixedSize(36, 36)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_button.setFont(QFont("Microsoft YaHei", 12))

        self._layout.addWidget(self._toggle_button)
        self._layout.addWidget(self._input)
        self._layout.addWidget(self._send_button)
        self._layout.addWidget(self._close_button)

        # 默认收起
        self._set_expanded(False)
        self.apply_style()

    def connect_signals(self) -> None:
        """连接按钮事件与 EventBus。"""
        # 💬 按钮点击 → 展开
        self._toggle_button.clicked.connect(lambda: self._set_expanded(True))
        # ✕ 按钮点击 → 收起
        self._close_button.clicked.connect(self.collapse)
        # ➤ 发送按钮 / Enter → 发送消息
        self._send_button.clicked.connect(self._on_send)
        self._input.returnPressed.connect(self._on_send)

        # 监听迷你聊天事件：思考与回复
        event_bus.mini_chat_thinking_started.connect(self.show_thinking)
        event_bus.mini_chat_reply_received.connect(self.show_reply)

    def apply_style(self) -> None:
        """应用卡通游戏风格样式。"""
        self._central.setStyleSheet(
            """
            #mini_chat_central {
                background-color: transparent;
            }
            """
        )
        # 💬 按钮：圆形粉色渐变
        self._toggle_button.setStyleSheet(
            """
            QPushButton#mini_chat_toggle {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f9a8d4, stop:1 #ec4899);
                color: white;
                border: 2px solid #fbcfe8;
                border-radius: 24px;
                font-size: 22px;
            }
            QPushButton#mini_chat_toggle:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f472b6, stop:1 #db2777);
                border: 2px solid #f9a8d4;
            }
            QPushButton#mini_chat_toggle:pressed {
                background-color: #be185d;
            }
            """
        )
        # 输入框：白色圆角，聚焦时粉色边框
        self._input.setStyleSheet(
            """
            QLineEdit#mini_chat_input {
                background-color: #ffffff;
                border: 2px solid #fce7f3;
                border-radius: 18px;
                padding: 4px 14px;
                color: #1e293b;
                selection-background-color: rgba(236, 72, 153, 0.2);
            }
            QLineEdit#mini_chat_input:focus {
                border: 2px solid #ec4899;
                background-color: #fffafc;
            }
            """
        )
        # 发送按钮：粉色圆角
        self._send_button.setStyleSheet(
            """
            QPushButton#mini_chat_send {
                background-color: #ec4899;
                color: white;
                border: none;
                border-radius: 18px;
                font-weight: bold;
            }
            QPushButton#mini_chat_send:hover {
                background-color: #db2777;
            }
            QPushButton#mini_chat_send:pressed {
                background-color: #be185d;
            }
            QPushButton#mini_chat_send:disabled {
                background-color: #fbcfe8;
            }
            """
        )
        # 关闭按钮：浅色圆角
        self._close_button.setStyleSheet(
            """
            QPushButton#mini_chat_close {
                background-color: #f1f5f9;
                color: #64748b;
                border: 1.5px solid #e2e8f0;
                border-radius: 18px;
            }
            QPushButton#mini_chat_close:hover {
                background-color: #fce7f3;
                color: #ec4899;
                border: 1.5px solid #f9a8d4;
            }
            """
        )

    # ============================================================
    # 公共接口
    # ============================================================

    def set_target_window(self, window: QWidget) -> None:
        """设置跟踪的目标窗口（LoverWindow）。

        连接目标窗口的 position_changed 信号，自动跟随移动。

        Args:
            window: LoverWindow 实例。
        """
        self._target_window = window
        # LoverWindow.moveEvent 会发射 position_changed
        window.position_changed.connect(self._on_target_moved)
        self._reposition()
        self.show_window()

    def expand(self) -> None:
        """展开输入框。"""
        self._set_expanded(True)

    def collapse(self) -> None:
        """收起输入框。"""
        self._set_expanded(False)

    def show_reply(self, text: str) -> None:
        """在角色头顶气泡中显示回复内容。

        Args:
            text: 回复文本。
        """
        self._bubble.show_message(text)
        self._reposition_bubble()
        # 回复后恢复输入
        self._input.setEnabled(True)
        self._send_button.setEnabled(True)

    def show_thinking(self) -> None:
        """在角色头顶气泡中显示"思考中"状态。"""
        self._bubble.show_thinking()
        self._reposition_bubble()
        # 思考时禁用输入
        self._input.setEnabled(False)
        self._send_button.setEnabled(False)

    def hide_bubble(self) -> None:
        """隐藏角色头顶气泡。"""
        self._bubble.hide_bubble()

    # ============================================================
    # 内部方法
    # ============================================================

    def _set_expanded(self, expanded: bool) -> None:
        """切换展开/收起状态。

        Args:
            expanded: True 展开，False 收起。
        """
        self._expanded = expanded

        # 收起状态：仅显示💬按钮
        self._toggle_button.setVisible(not expanded)
        # 展开状态：显示输入框+发送+关闭
        self._input.setVisible(expanded)
        self._send_button.setVisible(expanded)
        self._close_button.setVisible(expanded)

        if expanded:
            self.setFixedSize(self._EXPANDED_WIDTH, self._EXPANDED_HEIGHT)
            self.show()
            self.raise_()
            self.activateWindow()
            self._input.setFocus()
        else:
            self.setFixedSize(self._COLLAPSED_WIDTH, self._COLLAPSED_HEIGHT)

        self._reposition()

    def _on_send(self) -> None:
        """处理发送：获取文本，非空则通过 EventBus 广播。"""
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        event_bus.mini_chat_input_sent.emit(text)

    def _on_target_moved(self, pos) -> None:
        """目标窗口移动时，重新定位浮层与气泡，并保持在最上层。

        Args:
            pos: 目标窗口新位置（QPoint）。
        """
        self._reposition()
        self._reposition_bubble()
        # 拖拽后 LoverWindow 会被 raise 到最上层，需要把浮层也 raise，
        # 否则 💬 按钮会被 LoverWindow 遮挡无法点击
        self.raise_()

    def _reposition(self) -> None:
        """将浮层定位在角色窗口右下角。"""
        if self._target_window is None:
            return
        target_geo = self._target_window.geometry()

        if self._expanded:
            # 展开状态：输入框在角色右下方，右对齐
            x = target_geo.right() - self.width() + self._CORNER_OFFSET_X
            y = target_geo.bottom() + 4
        else:
            # 收起状态：💬按钮在角色右下角，部分重叠
            x = target_geo.right() - self.width() + 12 + self._CORNER_OFFSET_X
            y = target_geo.bottom() - self.height() + 12 + self._CORNER_OFFSET_Y
        self.move(x, y)

    def _reposition_bubble(self) -> None:
        """将对话气泡定位在角色窗口上方居中。"""
        if self._target_window is None or not self._bubble.isVisible():
            return
        target_geo = self._target_window.geometry()
        # 水平居中
        x = target_geo.center().x() - self._bubble.width() // 2
        # 垂直：角色顶部上方
        y = target_geo.y() - self._bubble.height() - self._BUBBLE_OFFSET_Y
        self._bubble.move(x, y)
        self._bubble.raise_()

    def closeEvent(self, event) -> None:  # noqa: N802
        """关闭时同时隐藏气泡。"""
        self._bubble.hide_bubble()
        super().closeEvent(event)
