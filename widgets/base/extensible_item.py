"""
可扩展列表项接口
用于统一右键菜单项、设置项等需要被动态增删的组件行为。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtWidgets import QWidget


@dataclass
class ItemPayload:
    """列表项携带的通用负载数据。

    Attributes:
        item_id: 全局唯一标识，用于区分不同菜单项/设置项。
        title: 显示文本。
        icon: 图标路径或 Qt 图标对象，可选。
        extra: 任意扩展数据，由具体业务填充。
    """

    item_id: str
    title: str
    icon: Any | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ExtensibleItem(ABC):
    """可扩展列表项接口。

    适用场景：
    - 右键菜单项（ContextMenu）
    - 设置面板项（SettingPanel）
    - 未来可能扩展的快捷操作栏、工具栏等

    设计说明：
    - 与具体 QWidget 解耦：ExtensibleItem 只定义行为契约。
    - 具体实现类负责返回 QWidget，供容器动态添加/删除。
    """

    @property
    @abstractmethod
    def payload(self) -> ItemPayload:
        """返回当前项的元数据。"""
        raise NotImplementedError

    @abstractmethod
    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        """创建并返回该列表项对应的 QWidget 实例。

        Args:
            parent: 父级 QWidget。

        Returns:
            配置完成的列表项控件。
        """
        raise NotImplementedError

    @abstractmethod
    def on_triggered(self) -> None:
        """当用户触发该列表项时调用（点击、回车等）。

        子类可在此发送事件到 EventBus 或执行本地回调。
        """
        raise NotImplementedError

    def on_removed(self) -> None:
        """当该项从容器中移除时调用，用于释放资源。

        默认空实现，子类按需重写。
        """
        pass
