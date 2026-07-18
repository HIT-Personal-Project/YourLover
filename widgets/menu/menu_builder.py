"""
菜单构建器
用于以链式/声明式方式组装右键菜单，方便后续扩展新的菜单项。
"""

from typing import Any, Callable

from widgets.menu.context_menu import ContextMenu
from widgets.menu.menu_item import MenuItem, MenuItemType


class MenuBuilder:
    """右键菜单构建器。

    使用示例：
        menu = (
            MenuBuilder()
            .add_home()
            .add_settings()
            .add_separator()
            .add_custom("custom_1", "切换模型", callback=on_switch_model)
            .build(parent=lover_window)
        )
        menu.show_at(pos)

    暴露接口：
    - add_home(callback): 添加主页项。
    - add_settings(callback): 添加设置项。
    - add_custom(...): 添加自定义项。
    - add_separator(): 添加分隔线。
    - build(parent): 生成 ContextMenu 实例。
    """

    def __init__(self) -> None:
        """初始化构建器，维护一个菜单项配置列表。"""
        self._configs: list[tuple[MenuItemType, dict[str, Any]]] = []

    def add_home(
        self,
        title: str = "主页",
        icon: Any | None = None,
        callback: Callable[[], None] | None = None,
    ) -> "MenuBuilder":
        """添加主页菜单项。"""
        self._configs.append(
            (
                MenuItemType.HOME,
                {"title": title, "icon": icon, "callback": callback},
            )
        )
        return self

    def add_settings(
        self,
        title: str = "设置",
        icon: Any | None = None,
        callback: Callable[[], None] | None = None,
    ) -> "MenuBuilder":
        """添加设置菜单项。"""
        self._configs.append(
            (
                MenuItemType.SETTINGS,
                {"title": title, "icon": icon, "callback": callback},
            )
        )
        return self

    def add_quit(
        self,
        title: str = "退出",
        icon: Any | None = None,
        callback: Callable[[], None] | None = None,
    ) -> "MenuBuilder":
        """添加退出应用菜单项。"""
        self._configs.append(
            (
                MenuItemType.QUIT,
                {"title": title, "icon": icon, "callback": callback},
            )
        )
        return self

    def add_custom(
        self,
        item_id: str,
        title: str,
        icon: Any | None = None,
        extra: dict[str, Any] | None = None,
        callback: Callable[[], None] | None = None,
    ) -> "MenuBuilder":
        """添加自定义菜单项。"""
        self._configs.append(
            (
                MenuItemType.CUSTOM,
                {
                    "item_id": item_id,
                    "title": title,
                    "icon": icon,
                    "extra": extra,
                    "callback": callback,
                },
            )
        )
        return self

    def add_separator(self) -> "MenuBuilder":
        """添加分隔线。"""
        self._configs.append((MenuItemType.SEPARATOR, {}))
        return self

    def build(self, parent: Any | None = None) -> ContextMenu:
        """根据当前配置生成 ContextMenu。

        Args:
            parent: 父级窗口，用于 Qt 对象树管理。

        Returns:
            组装完成的 ContextMenu 实例。
        """
        menu = ContextMenu(parent)
        for item_type, kwargs in self._configs:
            if item_type == MenuItemType.SEPARATOR:
                menu.add_separator()
                continue

            if item_type == MenuItemType.HOME:
                item = MenuItem(
                    item_id="menu_home",
                    title=kwargs.get("title", "主页"),
                    item_type=MenuItemType.HOME,
                    icon=kwargs.get("icon"),
                    on_triggered_callback=kwargs.get("callback"),
                )
            elif item_type == MenuItemType.SETTINGS:
                item = MenuItem(
                    item_id="menu_settings",
                    title=kwargs.get("title", "设置"),
                    item_type=MenuItemType.SETTINGS,
                    icon=kwargs.get("icon"),
                    on_triggered_callback=kwargs.get("callback"),
                )
            elif item_type == MenuItemType.QUIT:
                item = MenuItem(
                    item_id="menu_quit",
                    title=kwargs.get("title", "退出"),
                    item_type=MenuItemType.QUIT,
                    icon=kwargs.get("icon"),
                    on_triggered_callback=kwargs.get("callback"),
                )
            else:
                item = MenuItem(
                    item_id=kwargs["item_id"],
                    title=kwargs["title"],
                    item_type=MenuItemType.CUSTOM,
                    icon=kwargs.get("icon"),
                    extra=kwargs.get("extra"),
                    on_triggered_callback=kwargs.get("callback"),
                )

            menu.add_item(item)

        return menu
