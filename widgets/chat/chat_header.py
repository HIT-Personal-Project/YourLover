"""
聊天窗口顶部栏组件
显示助手头像、状态文本、设置按钮等。
"""

from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from widgets.base.base_widget import BaseWidget


class ChatHeader(BaseWidget):
    """聊天窗口顶部状态栏。

    职责：
    - 展示助手头像与名称（或状态文本）。
    - 提供设置按钮入口。
    - 暴露状态更新接口，便于外部同步 Agent 状态。

    暴露接口：
    - set_status(text): 更新状态文本。
    - set_title(text): 更新标题。
    - set_settings_callback(callback): 设置设置按钮回调。

    信号：
    - settings_clicked(): 设置按钮被点击时发射。
    """

    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化顶部栏。

        Args:
            parent: 父级 QWidget。
        """
        self._title: str = "虚拟助手"
        self._status: str = "在线"
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建顶部栏布局。"""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 10, 16, 10)
        self._layout.setSpacing(12)

        # 头像占位（后续可替换为 QLabel + QPixmap）
        self._avatar_label = QLabel("🌸", self)
        self._avatar_label.setObjectName("header_avatar")
        self._avatar_label.setFont(QFont("Segoe UI Emoji", 20))
        self._avatar_label.setFixedSize(42, 42)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题与状态
        self._title_label = QLabel(self._title, self)
        self._title_label.setObjectName("title_label")
        self._title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))

        self._status_label = QLabel(self._status, self)
        self._status_label.setObjectName("status_label")
        self._status_label.setFont(QFont("Microsoft YaHei", 9))
        self._status_label.setStyleSheet("color: #ec4899;")

        # 左侧信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.addWidget(self._title_label)
        info_layout.addWidget(self._status_label)

        # 设置按钮
        self._settings_button = QPushButton("⚙", self)
        self._settings_button.setObjectName("settings_btn")
        self._settings_button.setFixedSize(38, 38)
        self._settings_button.setToolTip("打开设置")
        self._settings_button.setFont(QFont("Segoe UI Emoji", 14))

        self._layout.addWidget(self._avatar_label)
        self._layout.addLayout(info_layout)
        self._layout.addStretch()
        self._layout.addWidget(self._settings_button)

        self.apply_style()

    def connect_signals(self) -> None:
        """连接设置按钮点击信号。"""
        self._settings_button.clicked.connect(self.settings_clicked.emit)

    def apply_style(self) -> None:
        """应用顶部栏样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            ChatHeader {
                background-color: #fffafc;
                border-bottom: 1.5px solid #fce7f3;
            }
            QLabel#header_avatar {
                background-color: #fce7f3;
                border-radius: 21px;
                border: 2px solid #fbcfe8;
            }
            QLabel#title_label {
                color: #be185d;
                background-color: transparent;
            }
            QPushButton#settings_btn {
                border: none;
                background-color: #fce7f3;
                border-radius: 19px;
                color: #be185d;
            }
            QPushButton#settings_btn:hover {
                background-color: #fbcfe8;
            }
            QPushButton#settings_btn:pressed {
                background-color: #f9a8d4;
            }
            """
        )

    def set_status(self, text: str, color: str = "#ec4899") -> None:
        """设置状态文本与颜色。

        Args:
            text: 状态文本，如 "思考中..."、"在线"。
            color: 状态文本颜色（hex）。
        """
        self._status = text
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color};")

    def set_title(self, text: str) -> None:
        """设置标题文本。

        Args:
            text: 标题文本。
        """
        self._title = text
        self._title_label.setText(text)

    def set_settings_callback(self, callback: Callable[[], None]) -> None:
        """设置设置按钮的回调函数。

        Args:
            callback: 点击设置按钮时执行的函数。
        """
        self.settings_clicked.connect(callback)

    def set_avatar(self, source: Any) -> None:
        """设置头像（预留接口）。

        Args:
            source: 头像资源，可以是图片路径或 QPixmap。
        """
        # TODO: 根据 source 类型设置 QLabel 的 pixmap
        pass
