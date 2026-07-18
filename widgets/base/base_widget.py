"""
通用组件基类
所有 widgets 包中的可复用组件均应继承此类。
"""

from abc import abstractmethod
from typing import Any

from PySide6.QtWidgets import QWidget


class BaseWidget(QWidget):
    """可复用组件的抽象基类。

    设计目标：
    - 统一组件初始化流程：创建 UI -> 连接信号 -> 刷新状态。
    - 提供数据绑定与样式刷新的标准扩展点。
    - 屏蔽不同 Qt 版本之间的差异（若后续迁移 PyQt6/PySide，可在此统一适配）。

    子类必须实现：
    - setup_ui(): 创建并布局子控件。
    - connect_signals(): 连接内部信号与槽。

    子类可选重写：
    - refresh(data): 根据外部数据刷新显示。
    - apply_style(): 应用自定义样式表。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化基类并调用子类实现的 UI 与信号绑定。

        Args:
            parent: 父级 QWidget，None 表示独立顶层控件。
        """
        super().__init__(parent)
        self.setup_ui()
        self.connect_signals()
        self.apply_style()

    @abstractmethod
    def setup_ui(self) -> None:
        """创建并布局所有子控件。

        子类必须实现。建议在此方法中只创建控件、设置布局，不触发业务逻辑。
        """
        raise NotImplementedError("子类必须实现 setup_ui()")

    @abstractmethod
    def connect_signals(self) -> None:
        """连接控件自身的信号与槽。

        子类必须实现。避免在 setup_ui 中混合信号连接，保持职责单一。
        """
        raise NotImplementedError("子类必须实现 connect_signals()")

    def refresh(self, data: Any | None = None) -> None:
        """根据外部数据刷新组件显示。

        Args:
            data: 任意类型的数据，由具体组件定义其结构。

        默认空实现，子类按需重写。
        """
        pass

    def apply_style(self) -> None:
        """应用自定义 QSS 或调整控件外观。

        默认空实现，子类按需重写。
        """
        pass
