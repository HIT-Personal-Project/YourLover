"""
聊天历史记录组件
以滚动列表形式展示所有聊天消息，支持追加、清空、滚动到底部。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from widgets.base.base_widget import BaseWidget
from widgets.chat.chat_bubble import ChatBubble, MessageData, MessageRole


class ChatHistory(BaseWidget):
    """聊天历史记录面板。

    职责：
    - 维护消息列表，按顺序渲染 ChatBubble。
    - 提供追加消息、更新最后一条消息、清空历史的能力。
    - 自动滚动到底部（可配置）。

    暴露接口：
    - append_message(role, content): 追加新消息并返回 ChatBubble。
    - update_last_message(content): 更新最后一条消息内容（流式输出）。
    - clear_history(): 清空所有消息。
    - scroll_to_bottom(): 滚动到底部。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化聊天历史面板。

        Args:
            parent: 父级 QWidget。
        """
        self._bubbles: list[ChatBubble] = []
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建滚动区域与消息列表布局。"""
        # 外层滚动区域
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # 内部容器：承载所有气泡
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)
        self._layout.addStretch()

        self._scroll_area.setWidget(self._container)

        # 自身布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._scroll_area)

        self.apply_style()

    def connect_signals(self) -> None:
        """历史面板无复杂内部信号。"""
        pass

    def apply_style(self) -> None:
        """应用滚动区域样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            QScrollArea {
                background-color: #fffafc;
                border: none;
            }
            QWidget#chat_container {
                background-color: #fffafc;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background-color: #f9a8d4;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #ec4899;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )
        self._container.setObjectName("chat_container")

    def append_message(
        self, role: MessageRole, content: str
    ) -> ChatBubble:
        """追加一条新消息。

        Args:
            role: 消息角色。
            content: 消息内容。

        Returns:
            新创建的 ChatBubble 实例，便于后续流式更新。
        """
        message_data = MessageData(role=role, content=content)
        bubble = ChatBubble(self._container)
        bubble.refresh(message_data)

        # 插入到 stretch 之前
        self._layout.insertWidget(len(self._bubbles), bubble)
        self._bubbles.append(bubble)
        self.scroll_to_bottom()
        return bubble

    def update_last_message(self, content: str) -> None:
        """更新最后一条消息的文本（用于流式输出）。

        Args:
            content: 新的完整文本。
        """
        if not self._bubbles:
            return
        self._bubbles[-1].set_content(content)
        self.scroll_to_bottom()

    def clear_history(self) -> None:
        """清空所有聊天消息。"""
        for bubble in self._bubbles:
            bubble.deleteLater()
        self._bubbles.clear()

    def scroll_to_bottom(self) -> None:
        """滚动到历史记录底部。"""
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def bubbles(self) -> list[ChatBubble]:
        """返回当前所有气泡控件。"""
        return self._bubbles.copy()
