"""
右键菜单项组件
实现 ExtensibleItem 接口，用于构建可扩展的右键菜单。
"""

from enum import Enum, auto
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QWidget

from core.event_bus import event_bus
from widgets.base.extensible_item import ExtensibleItem, ItemPayload


class MenuItemType(Enum):
    """预定义的菜单项类型。

    扩展说明：
    - 新增类型时在此枚举中添加，并在 MenuItem.create_widget 中处理对应图标/样式。
    - 对于业务自定义菜单项，建议使用 CUSTOM 类型并携带 extra 数据。
    """

    HOME = auto()       # 打开主页
    SETTINGS = auto()   # 打开设置
    HIDE = auto()       # 隐藏宠物
    QUIT = auto()       # 退出应用
    SEPARATOR = auto()  # 分隔线
    CUSTOM = auto()     # 自定义业务菜单项


class MenuItem(ExtensibleItem):
    """单个右键菜单项。

    职责：
    - 封装菜单项的元数据（id、文本、图标、类型）。
    - 负责创建 QAction 并绑定触发行为。
    - 触发时向 EventBus 发送 menu_item_triggered，并可选执行本地回调。

    暴露接口：
    - payload: 返回 ItemPayload 元数据。
    - create_widget(parent): 创建 QAction（QWidget 子类）。
    - on_triggered(): 处理点击。
    """

    def __init__(
        self,
        item_id: str,
        title: str,
        item_type: MenuItemType = MenuItemType.CUSTOM,
        icon: Any | None = None,
        extra: dict[str, Any] | None = None,
        on_triggered_callback: Callable[[], None] | None = None,
    ) -> None:
        """初始化菜单项。

        Args:
            item_id: 唯一标识。
            title: 显示文本。
            item_type: 菜单项类型，影响默认行为与图标。
            icon: 图标路径或 QIcon 实例。
            extra: 业务扩展数据。
            on_triggered_callback: 点击后的额外回调（可选）。
        """
        self._payload = ItemPayload(
            item_id=item_id,
            title=title,
            icon=icon,
            extra=extra or {},
        )
        self.item_type = item_type
        self.on_triggered_callback = on_triggered_callback
        self._action: QAction | None = None

    @property
    def payload(self) -> ItemPayload:
        """返回菜单项元数据。"""
        return self._payload

    def create_widget(self, parent: QWidget | None = None) -> QAction:
        """创建 QAction 控件。

        Args:
            parent: 父级菜单或窗口。

        Returns:
            配置完成的 QAction。分隔线类型返回 isSeparator 为 True 的 QAction。
        """
        action = QAction(self._payload.title, parent)

        if self.item_type == MenuItemType.SEPARATOR:
            action.setSeparator(True)
            self._action = action
            return action

        # 设置图标
        icon = self._payload.icon
        if isinstance(icon, str):
            action.setIcon(QIcon(icon))
        elif isinstance(icon, QIcon):
            action.setIcon(icon)

        # 绑定触发
        action.triggered.connect(self.on_triggered)

        # 对于预定义类型，在 extra 中注入类型标记，便于接收方识别
        self._payload.extra["menu_item_type"] = self.item_type.name

        self._action = action
        return action

    def on_triggered(self) -> None:
        """菜单项被点击时调用。

        行为：
        1. 发送 menu_item_triggered 事件到 EventBus（携带 item_id 与 extra）。
        2. 根据 item_type 发送对应的导航事件（HOME/SETTINGS/QUIT 等）。
        3. 执行可选的本地回调。
        """
        event_bus.menu_item_triggered.emit(
            self._payload.item_id, self._payload.extra
        )

        # 预定义类型的默认导航事件
        if self.item_type == MenuItemType.HOME:
            event_bus.menu_home_requested.emit()
            event_bus.show_chat_window_requested.emit()
        elif self.item_type == MenuItemType.SETTINGS:
            event_bus.menu_settings_requested.emit()
            event_bus.show_setting_window_requested.emit()
        elif self.item_type == MenuItemType.QUIT:
            event_bus.menu_quit_requested.emit()
            event_bus.application_quit_requested.emit()

        if self.on_triggered_callback is not None:
            self.on_triggered_callback()

    def on_removed(self) -> None:
        """从菜单中移除时释放 QAction。"""
        if self._action is not None:
            self._action.deleteLater()
            self._action = None
