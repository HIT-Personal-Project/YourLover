"""
设置面板组件
以滚动列表形式展示所有 SettingItem，支持动态增删与批量取值。
"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.event_bus import event_bus
from widgets.base.base_widget import BaseWidget
from widgets.settings.setting_item import SettingItem


class SettingPanel(BaseWidget):
    """设置选项列表面板。

    职责：
    - 管理一组 SettingItem，按垂直列表展示。
    - 支持动态添加、移除设置项。
    - 收集所有设置项的当前值。

    暴露接口：
    - add_item(item): 添加设置项。
    - remove_item(key): 按 key 移除。
    - get_value(key): 获取单个设置值。
    - get_values(): 获取所有设置值字典。
    - set_values(values): 批量设置值。
    - clear(): 清空所有设置项。

    信号：
    - item_value_changed(key, value): 任意设置项变化时转发。
    """

    item_value_changed = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化设置面板。

        Args:
            parent: 父级 QWidget。
        """
        self._items: dict[str, SettingItem] = {}
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建滚动区域与设置项列表布局。"""
        # 滚动区域
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # 内部容器
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

        self._scroll_area.setWidget(self._container)

        # 自身布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._scroll_area)

        self.apply_style()

    def connect_signals(self) -> None:
        """连接 EventBus，将 setting_changed 事件转发为本地信号。"""
        event_bus.setting_changed.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value: Any) -> None:
        """EventBus 设置变化事件的转发处理。

        Args:
            key: 设置项键名。
            value: 新值。
        """
        if key in self._items:
            self.item_value_changed.emit(key, value)

    def apply_style(self) -> None:
        """应用面板样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            QScrollArea {
                background-color: #fdf2f8;
                border: none;
            }
            QWidget#setting_container {
                background-color: #fdf2f8;
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
        self._container.setObjectName("setting_container")

    def add_item(self, item: SettingItem) -> None:
        """添加一个设置项。

        Args:
            item: SettingItem 实例。
        """
        key = item.key
        if key in self._items:
            self.remove_item(key)

        widget = item.create_widget(self._container)
        # 插入到 stretch 之前
        self._layout.insertWidget(len(self._items), widget)
        self._items[key] = item

    def remove_item(self, key: str) -> None:
        """按 key 移除设置项。

        Args:
            key: 设置项键名。
        """
        item = self._items.pop(key, None)
        if item is not None:
            item.on_removed()

    def get_value(self, key: str) -> Any:
        """获取单个设置项的当前值。

        Args:
            key: 设置项键名。

        Returns:
            设置值；若不存在返回 None。
        """
        item = self._items.get(key)
        return item.get_value() if item is not None else None

    def get_values(self) -> dict[str, Any]:
        """获取所有设置项的当前值。"""
        return {key: item.get_value() for key, item in self._items.items()}

    def set_values(self, values: dict[str, Any]) -> None:
        """批量设置多个设置项的值。

        Args:
            values: key -> value 的字典。
        """
        for key, value in values.items():
            item = self._items.get(key)
            if item is not None:
                item.set_value(value)

    def clear(self) -> None:
        """清空所有设置项。"""
        for item in list(self._items.values()):
            item.on_removed()
        self._items.clear()

    def items(self) -> list[SettingItem]:
        """返回当前所有设置项。"""
        return list(self._items.values())
