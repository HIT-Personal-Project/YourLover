"""
窗口基类
所有桌面窗口的公共基类，统一生命周期管理与事件总线接入。
"""

from abc import abstractmethod
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QWidget

from core.event_bus import event_bus


class BaseWindow(QMainWindow):
    """所有桌面窗口的抽象基类。

    设计目标：
    - 统一窗口的显示/隐藏/关闭行为。
    - 提供默认的 Qt 窗口标志配置。
    - 通过 EventBus 与外部模块通信，避免窗口间直接调用。
    - 子类化时只需关注业务布局与交互。

    子类必须实现：
    - setup_ui(): 创建窗口内部控件与布局。
    - connect_signals(): 连接内部信号与 EventBus。

    暴露接口：
    - show_window(): 显示窗口。
    - hide_window(): 隐藏窗口（默认不销毁）。
    - toggle(): 切换显示/隐藏。
    - set_content_widget(widget): 设置窗口中央控件。
    """

    # 窗口可见性变化信号
    visibility_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化窗口基类。

        Args:
            parent: 父级窗口，None 表示顶层窗口。
        """
        super().__init__(parent)
        self._setup_window_flags()
        self.setup_ui()
        self.connect_signals()
        self.apply_style()

    def _setup_window_flags(self) -> None:
        """配置默认窗口标志。

        默认行为：
        - 关闭时隐藏而非退出（子类可覆盖 closeEvent 实现）。
        """
        # 默认标准窗口，子类可按需覆盖
        self.setWindowFlags(Qt.WindowType.Window)

    @abstractmethod
    def setup_ui(self) -> None:
        """创建窗口内部 UI。"""
        raise NotImplementedError("子类必须实现 setup_ui()")

    @abstractmethod
    def connect_signals(self) -> None:
        """连接内部信号与 EventBus。"""
        raise NotImplementedError("子类必须实现 connect_signals()")

    def apply_style(self) -> None:
        """应用窗口样式。默认空实现。"""
        pass

    def show_window(self) -> None:
        """显示窗口并发射可见性变化信号。"""
        self.show()
        self.raise_()
        self.activateWindow()
        self.visibility_changed.emit(True)

    def hide_window(self) -> None:
        """隐藏窗口并发射可见性变化信号（默认不销毁）。"""
        self.hide()
        self.visibility_changed.emit(False)

    def toggle(self) -> None:
        """切换窗口显示/隐藏。"""
        if self.isVisible():
            self.hide_window()
        else:
            self.show_window()

    def set_content_widget(self, widget: QWidget) -> None:
        """设置窗口中央控件。

        Args:
            widget: 要设置为中央控件的 QWidget。
        """
        self.setCentralWidget(widget)

    def closeEvent(self, event) -> None:  # noqa: N802
        """默认关闭事件：隐藏窗口而非退出。

        Args:
            event: 关闭事件对象。
        """
        event.ignore()
        self.hide_window()
