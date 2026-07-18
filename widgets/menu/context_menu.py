"""
右键弹出菜单组件
基于 QMenu 实现，支持动态添加、删除菜单项，并统一处理触发事件。
"""

from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QMenu, QWidget

from widgets.base.base_widget import BaseWidget
from widgets.base.extensible_item import ExtensibleItem
from widgets.menu.menu_item import MenuItem, MenuItemType


class ContextMenu(BaseWidget):
    """通用右键弹出菜单。

    职责：
    - 管理一组 MenuItem（可扩展列表项）。
    - 在指定位置弹出菜单。
    - 提供清空、添加、移除菜单项的能力。

    暴露接口：
    - add_item(item): 添加菜单项。
    - add_separator(): 添加分隔线。
    - remove_item(item_id): 按 id 移除。
    - clear(): 清空所有项。
    - show_at(pos): 在全局坐标 pos 处弹出。

    信号：
    - item_triggered(item_id, payload): 菜单项被触发时发射。
    """

    # 内部转发信号，方便调用方直接连接（无需通过 EventBus）
    item_triggered = Signal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化右键菜单。

        Args:
            parent: 父级窗口，通常为 LoverWindow。
        """
        self._items: dict[str, ExtensibleItem] = {}
        self._menu = QMenu(parent)
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建菜单容器，设置样式与行为。"""
        self._menu.setWindowFlags(
            self._menu.windowFlags()
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        # 默认样式，后续可通过 apply_style 覆盖
        self._menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(255, 250, 252, 245);
                border: 1.5px solid #fce7f3;
                border-radius: 16px;
                padding: 10px;
                /* 模拟柔和阴影：借助边框 + 半透明背景 */
            }
            QMenu::item {
                padding: 10px 24px;
                margin: 3px 4px;
                border-radius: 12px;
                color: #1e293b;
                font-family: "Microsoft YaHei";
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(236, 72, 153, 0.15);
                color: #be185d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #fce7f3;
                margin: 6px 12px;
            }
            """
        )

    def connect_signals(self) -> None:
        """连接菜单项触发信号到内部转发信号。"""
        # 注意：单个 MenuItem 的触发已直接连接 EventBus，
        # 此处仅做本地转发，方便调用方直接监听 ContextMenu.item_triggered。
        pass

    def add_item(self, item: ExtensibleItem) -> None:
        """添加一个菜单项。

        Args:
            item: 实现 ExtensibleItem 的菜单项实例。
        """
        item_id = item.payload.item_id
        if item_id in self._items:
            # 重复 id 时先移除旧项，保证幂等性
            self.remove_item(item_id)

        action = item.create_widget(self._menu)
        self._menu.addAction(action)
        self._items[item_id] = item

    def add_separator(self) -> None:
        """添加一条分隔线。"""
        separator = MenuItem(
            item_id=f"separator_{len(self._items)}",
            title="",
            item_type=MenuItemType.SEPARATOR,
        )
        self.add_item(separator)

    def remove_item(self, item_id: str) -> None:
        """按 id 移除菜单项。

        Args:
            item_id: 要移除的菜单项 id。
        """
        item = self._items.pop(item_id, None)
        if item is not None:
            item.on_removed()
            # 重新构建菜单：简单起见清空后按顺序重建
            self._rebuild_menu()

    def clear(self) -> None:
        """清空所有菜单项。"""
        for item in self._items.values():
            item.on_removed()
        self._items.clear()
        self._menu.clear()

    def show_at(self, pos: QPoint) -> None:
        """在指定全局坐标处显示菜单。

        Args:
            pos: 全局坐标 QPoint。
        """
        self._menu.popup(pos)

    def _rebuild_menu(self) -> None:
        """根据当前 _items 重新生成菜单。"""
        self._menu.clear()
        for item in self._items.values():
            action = item.create_widget(self._menu)
            self._menu.addAction(action)

    def items(self) -> list[ExtensibleItem]:
        """返回当前所有菜单项（按添加顺序）。"""
        return list(self._items.values())
