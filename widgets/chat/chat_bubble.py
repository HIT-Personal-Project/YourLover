"""
聊天气泡组件
显示单条聊天消息，支持用户消息与助手消息的不同对齐与样式。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from widgets.base.base_widget import BaseWidget


class MessageRole(Enum):
    """消息角色枚举。"""

    USER = auto()   # 用户发送的消息
    AGENT = auto()  # 助手（Agent）回复的消息
    SYSTEM = auto() # 系统提示消息


@dataclass
class MessageData:
    """单条消息的数据封装。

    Attributes:
        role: 消息角色。
        content: 消息文本内容。
        timestamp: 发送时间。
        extra: 扩展字段（如附件、工具调用状态等）。
    """

    role: MessageRole
    content: str
    timestamp: datetime = None
    extra: dict = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.extra is None:
            self.extra = {}


class ChatBubble(BaseWidget):
    """单条聊天气泡。

    职责：
    - 根据角色显示左/右对齐的气泡。
    - 提供文本内容展示（后续可接入 Markdown 渲染）。
    - 暴露 refresh(data) 接口，便于外部更新。

    暴露接口：
    - refresh(message_data): 根据 MessageData 刷新显示。
    - set_content(text): 更新文本（流式输出时可用）。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化气泡。

        Args:
            parent: 父级 QWidget。
        """
        self._message: MessageData | None = None
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建气泡布局与控件。"""
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(10, 6, 10, 6)
        self._main_layout.setSpacing(8)

        # 消息内容标签
        self._content_label = QLabel(self)
        self._content_label.setObjectName("bubble_content")
        self._content_label.setWordWrap(True)
        self._content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._content_label.setFont(QFont("Microsoft YaHei", 10))

        # 时间戳标签
        self._time_label = QLabel(self)
        self._time_label.setObjectName("bubble_time")
        self._time_label.setFont(QFont("Microsoft YaHei", 8))

        # 垂直容器：内容 + 时间
        self._bubble_layout = QVBoxLayout()
        self._bubble_layout.setSpacing(2)
        self._bubble_layout.addWidget(self._content_label)
        self._bubble_layout.addWidget(self._time_label)

        # 占位 stretch（根据角色动态调整位置：左 / 右）
        self._left_stretch = QWidget()
        self._left_stretch.setSizePolicy(
            self._left_stretch.sizePolicy().horizontalPolicy(),
            self._left_stretch.sizePolicy().verticalPolicy(),
        )
        self._left_stretch.setMinimumWidth(0)

        self._right_stretch = QWidget()
        self._right_stretch.setSizePolicy(
            self._right_stretch.sizePolicy().horizontalPolicy(),
            self._right_stretch.sizePolicy().verticalPolicy(),
        )
        self._right_stretch.setMinimumWidth(0)

        # 气泡容器：固定宽度范围
        self._bubble_container = QWidget(self)
        self._bubble_container.setObjectName("bubble_container")
        self._bubble_container.setMaximumWidth(460)
        bubble_main = QHBoxLayout(self._bubble_container)
        bubble_main.setContentsMargins(0, 0, 0, 0)
        bubble_main.addLayout(self._bubble_layout)

        # 默认顺序：左 stretch + 气泡 + 右 stretch（apply_style 会调整）
        self._main_layout.addWidget(self._left_stretch, stretch=1)
        self._main_layout.addWidget(self._bubble_container)
        self._main_layout.addWidget(self._right_stretch, stretch=1)

        self.setMaximumWidth(720)
        self.apply_style()

    def connect_signals(self) -> None:
        """气泡内部无特殊信号需要连接。"""
        pass

    def apply_style(self) -> None:
        """根据当前消息角色应用样式（卡通游戏风）。"""
        if self._message is None:
            return

        # 重置 stretch 的可见性，确保切换角色时正确显示位置
        self._left_stretch.setVisible(True)
        self._right_stretch.setVisible(True)

        if self._message.role == MessageRole.USER:
            # 用户消息：粉色渐变气泡，右对齐
            self._content_label.setStyleSheet(
                """
                QLabel#bubble_content {
                    background-color: #ec4899;
                    color: #ffffff;
                    border-radius: 18px;
                    border-bottom-right-radius: 6px;
                    padding: 12px 16px;
                    font-weight: 500;
                }
                """
            )
            self._time_label.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

            # 用户消息：左 stretch 占据剩余空间，右 stretch 隐藏（气泡靠右）
            self._left_stretch.setVisible(True)
            self._right_stretch.setVisible(False)

        elif self._message.role == MessageRole.AGENT:
            # Agent 消息：白色卡片 + 粉色边框，左对齐
            self._content_label.setStyleSheet(
                """
                QLabel#bubble_content {
                    background-color: #ffffff;
                    color: #1e293b;
                    border-radius: 18px;
                    border-bottom-left-radius: 6px;
                    border: 1.5px solid #fce7f3;
                    padding: 12px 16px;
                }
                """
            )
            self._time_label.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            self._time_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

            # Agent 消息：左 stretch 隐藏（气泡靠左），右 stretch 占据剩余空间
            self._left_stretch.setVisible(False)
            self._right_stretch.setVisible(True)

        else:
            # 系统消息：淡黄色提示，居中
            self._content_label.setStyleSheet(
                """
                QLabel#bubble_content {
                    background-color: #fef3c7;
                    color: #92400e;
                    border-radius: 14px;
                    padding: 8px 14px;
                }
                """
            )
            self._time_label.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            self._time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._left_stretch.setVisible(False)
            self._right_stretch.setVisible(False)

    def refresh(self, data: MessageData | None = None) -> None:
        """根据消息数据刷新气泡。

        Args:
            data: MessageData 实例。
        """
        if data is not None:
            self._message = data
        if self._message is None:
            return

        self._content_label.setText(self._message.content)
        self._time_label.setText(self._message.timestamp.strftime("%H:%M"))
        self.apply_style()

    def set_content(self, text: str) -> None:
        """更新气泡文本（流式输出时追加使用）。

        Args:
            text: 新的完整文本内容。
        """
        if self._message is not None:
            self._message.content = text
        self._content_label.setText(text)

    def message(self) -> MessageData | None:
        """返回当前气泡绑定的消息数据。"""
        return self._message
