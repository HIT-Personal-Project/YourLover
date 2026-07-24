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
    QProgressBar,          # 新增导入
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
        self._title: str = "YourLover"
        self._status: str = "在线"
        # 新增内部状态，便于后续更新
        self._affection_value: int = 100
        self._emotional_state: str = "开心😊"
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

        #好感度和情绪
        affection_layout = QHBoxLayout()
        affection_layout.setSpacing(0)          # 改为0，让爱心、进度条、百分比紧贴
        affection_layout.setContentsMargins(0, 0, 0, 0)


        # 原有的 _affection_label 改为显示百分比数值（保留原属性名）
        self._affection_label = QLabel(f"  {self._affection_value}❤️", self)
        self._affection_label.setObjectName("affection_label")
        self._affection_label.setFont(QFont("Microsoft YaHei", 9))
        self._affection_label.setStyleSheet("color: #be185d; font-weight: bold;")


        # 新增好感度进度条
        self._affection_progress = QProgressBar(self)
        self._affection_progress.setObjectName("affection_progress")
        self._affection_progress.setRange(0, 100)
        self._affection_progress.setValue(self._affection_value)
        self._affection_progress.setTextVisible(False)
        self._affection_progress.setFixedWidth(120)
        self._affection_progress.setFixedHeight(16)

        # 将图标、进度条和数值标签依次加入好感度布局
        affection_layout.addWidget(self._affection_progress)
        affection_layout.addWidget(self._affection_label)

        # 情绪标签（保留原有属性，但样式改为圆角背景）
        self._emotional_label = QLabel(self._emotional_state, self)
        self._emotional_label.setObjectName("emotional_label")
        self._emotional_label.setFont(QFont("Microsoft YaHei", 9))
        self._emotional_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._emotional_label.setFixedHeight(24)
        # 初始样式在 apply_style 中统一设置

        # 将好感度和情绪放在同一行，方便与标题对齐
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setSpacing(12)
        status_layout.addLayout(affection_layout)
        status_layout.addWidget(self._emotional_label)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # 设置按钮
        self._settings_button = QPushButton("⚙", self)
        self._settings_button.setObjectName("settings_btn")
        self._settings_button.setFixedSize(38, 38)
        self._settings_button.setToolTip("打开设置")
        self._settings_button.setFont(QFont("Segoe UI Emoji", 14))

        self._layout.addWidget(self._avatar_label)
        self._layout.addLayout(info_layout)
        self._layout.addWidget(status_widget, 1)   # 占用弹性空间
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
            /* 新增进度条样式 */
            QProgressBar#affection_progress {
                border: none;
                background-color: #fce7f3;
                border-radius: 8px;
                height: 16px;
                margin: 0;          /* 去除外边距 */
                padding: 0;         /* 去除内边距 */
            }
            QProgressBar#affection_progress::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f472b6, stop:1 #be185d);
                border-radius: 8px;
            }
            /* 情绪标签样式（在代码中动态更新，这里保留默认） */
            QLabel#emotional_label {
                background-color: #fce7f3;
                border-radius: 12px;
                padding: 0 12px;
                color: #be185d;
            }
            """
        )

    # ---------- 新增更新接口（保留原有接口不变） ----------
    def set_affection(self, value: int) -> None:
        """更新好感度数值（0~100），进度条和数值同步变化"""
        clamped = max(0, min(100, value))
        self._affection_value = clamped
        self._affection_progress.setValue(clamped)
        self._affection_label.setText(f"{clamped}%")

    def set_emotional(self, state: str, color: str = "#be185d", bg_color: str = "#fce7f3") -> None:
        """更新情绪状态，可自定义文字颜色和背景色"""
        self._emotional_state = state
        self._emotional_label.setText(state)
        self._emotional_label.setStyleSheet(
            f"""
            QLabel#emotional_label {{
                background-color: {bg_color};
                border-radius: 12px;
                padding: 0 12px;
                color: {color};
            }}
            """
        )

    # ------------------ 以下为原有接口（完全保留） ------------------
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