"""
聊天会话列表组件
显示在聊天窗口左侧，展示所有历史会话，支持新建会话、切换会话、删除会话。

设计说明：
- 本组件只负责会话列表的 UI 与交互，不直接操作数据。
- 用户点击会话项时发射 session_clicked(session_id) 信号。
- 用户点击"新建会话"时发射 new_session_requested 信号。
- 用户点击会话项右侧删除按钮时发射 session_deleted(session_id) 信号。
- 实际的会话数据管理（加载、保存、切换）由外部监听者（如 ChatWindow 或 Agent 模块）处理。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from widgets.base.base_widget import BaseWidget


@dataclass
class SessionData:
    """单个会话的数据模型。

    Attributes:
        session_id: 会话唯一标识。
        title: 会话标题（通常是首条用户消息摘要）。
        preview: 最后一条消息预览。
        updated_at: 最后更新时间。
        avatar: 会话头像（emoji 或图片路径），可选。
        extra: 扩展数据。
    """

    session_id: str
    title: str
    preview: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    avatar: str = "💬"
    extra: dict = field(default_factory=dict)


class SessionItem(QFrame):
    """单个会话列表项。

    职责：
    - 展示头像、标题、预览、时间。
    - hover 时显示删除按钮。
    - 点击时发射 clicked 信号。
    """

    clicked = Signal(str)         # 会话被点击，参数：session_id
    delete_clicked = Signal(str)  # 会话被请求删除，参数：session_id

    def __init__(self, data: SessionData, parent: QWidget | None = None) -> None:
        """初始化会话项。

        Args:
            data: 会话数据。
            parent: 父级 QWidget。
        """
        super().__init__(parent)
        self._data = data
        self._selected = False
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """创建会话项内部 UI。"""
        self.setObjectName("session_item")
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(10)

        # 头像（emoji 占位）
        self._avatar_label = QLabel(self._data.avatar, self)
        self._avatar_label.setObjectName("session_avatar")
        self._avatar_label.setFixedSize(40, 40)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setFont(QFont("Segoe UI Emoji", 18))

        # 中间文字区
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self._title_label = QLabel(self._data.title, self)
        self._title_label.setObjectName("session_title")
        self._title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        self._title_label.setWordWrap(False)

        self._preview_label = QLabel(self._data.preview, self)
        self._preview_label.setObjectName("session_preview")
        self._preview_label.setFont(QFont("Microsoft YaHei", 9))
        self._preview_label.setWordWrap(False)

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._preview_label)

        # 右侧：删除按钮（默认隐藏，hover 时显示）
        self._delete_button = QPushButton("×", self)
        self._delete_button.setObjectName("session_delete_btn")
        self._delete_button.setFixedSize(22, 22)
        self._delete_button.setToolTip("删除会话")
        self._delete_button.hide()

        layout.addWidget(self._avatar_label)
        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self._delete_button)

        # 信号
        self._delete_button.clicked.connect(
            lambda: self.delete_clicked.emit(self._data.session_id)
        )

    def _apply_style(self) -> None:
        """应用会话项样式。"""
        self.setStyleSheet(
            """
            QFrame#session_item {
                background-color: transparent;
                border: none;
                border-radius: 14px;
            }
            QFrame#session_item:hover {
                background-color: rgba(236, 72, 153, 0.08);
            }
            QFrame#session_item[selected="true"] {
                background-color: rgba(236, 72, 153, 0.15);
                border: 1.5px solid rgba(236, 72, 153, 0.4);
            }
            QLabel#session_avatar {
                background-color: #fce7f3;
                border-radius: 20px;
                border: none;
            }
            QLabel#session_title {
                color: #1e293b;
                background-color: transparent;
                border: none;
            }
            QLabel#session_preview {
                color: #94a3b8;
                background-color: transparent;
                border: none;
            }
            QPushButton#session_delete_btn {
                background-color: #fee2e2;
                color: #ef4444;
                border: none;
                border-radius: 11px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton#session_delete_btn:hover {
                background-color: #fecaca;
            }
            """
        )

    def set_selected(self, selected: bool) -> None:
        """设置选中状态。

        Args:
            selected: 是否选中。
        """
        self._selected = selected
        # 使用动态属性驱动 QSS 选择器
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def update_data(self, data: SessionData) -> None:
        """更新会话数据并刷新显示。

        Args:
            data: 新的会话数据。
        """
        self._data = data
        self._avatar_label.setText(data.avatar)
        self._title_label.setText(data.title)
        self._preview_label.setText(data.preview)

    def session_id(self) -> str:
        """返回当前会话 ID。"""
        return self._data.session_id

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """鼠标点击：发射 clicked 信号。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._data.session_id)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        """鼠标进入：显示删除按钮。"""
        self._delete_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        """鼠标离开：隐藏删除按钮。"""
        self._delete_button.hide()
        super().leaveEvent(event)


class ChatSessionList(BaseWidget):
    """聊天会话列表组件。

    职责：
    - 展示所有历史会话（SessionItem）。
    - 顶部提供"新建会话"按钮。
    - 支持动态增删会话。
    - 管理选中状态，切换会话时发射信号。

    暴露接口：
    - add_session(data): 添加会话。
    - remove_session(session_id): 删除会话。
    - update_session(data): 更新会话数据。
    - select_session(session_id): 选中某个会话。
    - clear(): 清空所有会话。

    信号：
    - session_clicked(session_id): 会话被点击。
    - session_deleted(session_id): 会话被请求删除。
    - new_session_requested(): 请求新建会话。
    """

    session_clicked = Signal(str)
    session_deleted = Signal(str)
    new_session_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化会话列表。

        Args:
            parent: 父级 QWidget。
        """
        self._items: dict[str, SessionItem] = {}
        self._current_session_id: str | None = None
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建会话列表布局。"""
        self.setObjectName("chat_session_list")
        self.setFixedWidth(240)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 12, 10, 12)
        main_layout.setSpacing(10)

        # 顶部标题 + 新建按钮
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(6)

        self._title_label = QLabel("💬 对话", self)
        self._title_label.setObjectName("session_list_title")
        self._title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))

        self._new_button = QPushButton("✨", self)
        self._new_button.setObjectName("new_session_btn")
        self._new_button.setFixedSize(32, 32)
        self._new_button.setToolTip("新建对话")
        self._new_button.setFont(QFont("Segoe UI Emoji", 14))
        self._new_button.setCursor(Qt.CursorShape.PointingHandCursor)

        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._new_button)

        # 滚动会话列表
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self._container = QWidget()
        self._container.setObjectName("session_container")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()

        self._scroll_area.setWidget(self._container)

        main_layout.addLayout(header_layout)
        main_layout.addWidget(self._scroll_area, stretch=1)

        self.apply_style()

    def connect_signals(self) -> None:
        """连接内部信号。"""
        self._new_button.clicked.connect(self.new_session_requested.emit)

    def apply_style(self) -> None:
        """应用会话列表样式。"""
        self.setStyleSheet(
            """
            QWidget#chat_session_list {
                background-color: #fdf2f8;
                border-right: 1px solid #fce7f3;
            }
            QLabel#session_list_title {
                color: #be185d;
                background-color: transparent;
            }
            QPushButton#new_session_btn {
                background-color: #ec4899;
                color: white;
                border: none;
                border-radius: 16px;
                font-weight: bold;
            }
            QPushButton#new_session_btn:hover {
                background-color: #db2777;
            }
            QPushButton#new_session_btn:pressed {
                background-color: #be185d;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QWidget#session_container {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 6px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background-color: #f9a8d4;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #f472b6;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )

    def add_session(self, data: SessionData) -> None:
        """添加一个会话。

        Args:
            data: 会话数据。
        """
        if data.session_id in self._items:
            self.remove_session(data.session_id)

        item = SessionItem(data, self._container)
        item.clicked.connect(self._on_item_clicked)
        item.delete_clicked.connect(self.session_deleted.emit)

        # 插入到 stretch 之前
        self._container_layout.insertWidget(len(self._items), item)
        self._items[data.session_id] = item

        # 默认选中新添加的
        self.select_session(data.session_id)

    def remove_session(self, session_id: str) -> None:
        """移除会话。

        Args:
            session_id: 会话 ID。
        """
        item = self._items.pop(session_id, None)
        if item is not None:
            item.deleteLater()

        if self._current_session_id == session_id:
            self._current_session_id = None
            # 默认切换到第一个
            if self._items:
                first_id = next(iter(self._items))
                self.select_session(first_id)

    def update_session(self, data: SessionData) -> None:
        """更新会话数据。

        Args:
            data: 新的会话数据。
        """
        item = self._items.get(data.session_id)
        if item is not None:
            item.update_data(data)

    def select_session(self, session_id: str) -> None:
        """选中某个会话。

        Args:
            session_id: 要选中的会话 ID。
        """
        if session_id not in self._items:
            return

        # 取消之前的选中
        for item in self._items.values():
            item.set_selected(False)

        # 选中新的
        self._items[session_id].set_selected(True)
        self._current_session_id = session_id
        self.session_clicked.emit(session_id)

    def clear(self) -> None:
        """清空所有会话。"""
        for item in self._items.values():
            item.deleteLater()
        self._items.clear()
        self._current_session_id = None

    def current_session_id(self) -> str | None:
        """返回当前选中的会话 ID。"""
        return self._current_session_id

    def _on_item_clicked(self, session_id: str) -> None:
        """会话项被点击时的内部处理。"""
        self.select_session(session_id)
