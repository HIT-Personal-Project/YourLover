"""
设置项组件
实现 ExtensibleItem 接口，提供开关、文本、滑块、下拉等常见设置项基类。
"""

from abc import abstractmethod
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from core.event_bus import event_bus
from widgets.base.extensible_item import ExtensibleItem, ItemPayload


class SettingItem(ExtensibleItem):
    """设置项抽象基类。

    职责：
    - 定义设置项的元数据（key、标签、默认值、当前值）。
    - 规范值变化时的行为：更新内部状态 -> 发送 EventBus setting_changed。
    - 子类只需实现 create_editor() 返回具体的编辑器控件。

    暴露接口：
    - get_value(): 获取当前值。
    - set_value(value): 设置当前值并刷新编辑器。
    - create_widget(parent): 创建完整的设置项 QWidget。
    """

    def __init__(
        self,
        key: str,
        label: str,
        default_value: Any,
        icon: Any | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """初始化设置项。

        Args:
            key: 设置项唯一键，用于持久化与事件识别。
            label: 显示标签。
            default_value: 默认值。
            icon: 图标（可选）。
            extra: 扩展数据（如 help_text、min/max 等）。
        """
        self._key = key
        self._label = label
        self._default_value = default_value
        self._value = default_value
        self._payload = ItemPayload(
            item_id=key,
            title=label,
            icon=icon,
            extra=extra or {},
        )
        self._widget: QWidget | None = None

    @property
    def payload(self) -> ItemPayload:
        """返回设置项元数据。"""
        return self._payload

    @property
    def key(self) -> str:
        """返回设置项键名。"""
        return self._key

    def get_value(self) -> Any:
        """返回当前值。"""
        return self._value

    def set_value(self, value: Any) -> None:
        """设置当前值并同步到编辑器。

        Args:
            value: 新的值。
        """
        self._value = value
        self._update_editor(value)

    def on_value_changed(self, value: Any) -> None:
        """子类编辑器触发值变化时调用。

        Args:
            value: 编辑器返回的新值。
        """
        self._value = value
        event_bus.setting_changed.emit(self._key, value)

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        """创建设置项的完整 QWidget。

        Args:
            parent: 父级 QWidget。

        Returns:
            组装完成的设置项控件。
        """
        container = QWidget(parent)
        container.setObjectName(f"setting_item_{self._key}")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        # 左侧标签
        label = QLabel(self._label)
        label.setObjectName("setting_item_label")
        label.setFont(QFont("Microsoft YaHei", 10))
        label.setToolTip(self._payload.extra.get("help_text", ""))

        # 右侧编辑器（由子类实现）
        editor = self.create_editor(container)
        editor.setSizePolicy(
            editor.sizePolicy().horizontalPolicy(),
            editor.sizePolicy().verticalPolicy(),
        )

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(editor)

        # 卡片化样式：圆润白底 + 粉色边框 + hover 微提升
        container.setStyleSheet(
            """
            QWidget {
                background-color: #ffffff;
                border: 1.5px solid #fce7f3;
                border-radius: 16px;
            }
            QLabel#setting_item_label {
                color: #1e293b;
                background-color: transparent;
                border: none;
            }
            """
        )

        self._widget = container
        return container

    @abstractmethod
    def create_editor(self, parent: QWidget) -> QWidget:
        """创建具体的值编辑器控件。

        Args:
            parent: 父级 QWidget。

        Returns:
            编辑器控件。
        """
        raise NotImplementedError("子类必须实现 create_editor()")

    @abstractmethod
    def _update_editor(self, value: Any) -> None:
        """将当前值同步到编辑器显示。

        Args:
            value: 要显示的值。
        """
        raise NotImplementedError("子类必须实现 _update_editor()")

    def on_triggered(self) -> None:
        """设置项通常不响应触发，值变化通过编辑器处理。"""
        pass

    def on_removed(self) -> None:
        """移除时释放控件。"""
        if self._widget is not None:
            self._widget.deleteLater()
            self._widget = None


class ToggleSettingItem(SettingItem):
    """开关型设置项（布尔值）。"""

    def create_editor(self, parent: QWidget) -> QWidget:
        self._check_box = QCheckBox(parent)
        self._check_box.setChecked(bool(self._value))
        self._check_box.stateChanged.connect(
            lambda state: self.on_value_changed(state == Qt.CheckState.Checked)
        )
        self._check_box.setStyleSheet(
            """
            QCheckBox {
                background-color: transparent;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border-radius: 11px;
                border: 2px solid #f9a8d4;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #ec4899;
                border-color: #ec4899;
            }
            """
        )
        return self._check_box

    def _update_editor(self, value: Any) -> None:
        self._check_box.setChecked(bool(value))


class TextSettingItem(SettingItem):
    """文本型设置项（字符串）。"""

    def create_editor(self, parent: QWidget) -> QWidget:
        self._line_edit = QLineEdit(parent)
        self._line_edit.setText(str(self._value))
        self._line_edit.setMinimumWidth(180)
        self._line_edit.textChanged.connect(self.on_value_changed)
        self._line_edit.setStyleSheet(
            """
            QLineEdit {
                padding: 8px 12px;
                border: 1.5px solid #fce7f3;
                border-radius: 12px;
                background-color: #fffafc;
                color: #1e293b;
                selection-background-color: rgba(236, 72, 153, 0.2);
            }
            QLineEdit:focus {
                border: 2px solid #ec4899;
                background-color: #ffffff;
            }
            """
        )
        return self._line_edit

    def _update_editor(self, value: Any) -> None:
        self._line_edit.setText(str(value))


class SliderSettingItem(SettingItem):
    """滑块型设置项（整数，可配置 min/max）。"""

    def create_editor(self, parent: QWidget) -> QWidget:
        self._spin_box = QSpinBox(parent)
        self._spin_box.setRange(
            self._payload.extra.get("min", 0),
            self._payload.extra.get("max", 100),
        )
        self._spin_box.setValue(int(self._value))
        self._spin_box.valueChanged.connect(self.on_value_changed)
        self._spin_box.setStyleSheet(
            """
            QSpinBox {
                padding: 8px 12px;
                border: 1.5px solid #fce7f3;
                border-radius: 12px;
                background-color: #fffafc;
                color: #1e293b;
            }
            QSpinBox:focus {
                border: 2px solid #ec4899;
                background-color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                border: none;
                background-color: transparent;
            }
            """
        )
        return self._spin_box

    def _update_editor(self, value: Any) -> None:
        self._spin_box.setValue(int(value))


class OptionSettingItem(SettingItem):
    """下拉选项型设置项。"""

    def create_editor(self, parent: QWidget) -> QWidget:
        self._combo_box = QComboBox(parent)
        options = self._payload.extra.get("options", [])
        for option in options:
            self._combo_box.addItem(str(option), option)

        # 设置当前值
        index = self._combo_box.findData(self._value)
        if index >= 0:
            self._combo_box.setCurrentIndex(index)

        self._combo_box.currentIndexChanged.connect(
            lambda: self.on_value_changed(self._combo_box.currentData())
        )
        self._combo_box.setStyleSheet(
            """
            QComboBox {
                padding: 8px 14px;
                border: 1.5px solid #fce7f3;
                border-radius: 12px;
                background-color: #fffafc;
                color: #1e293b;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #f9a8d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #ec4899;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1.5px solid #fce7f3;
                border-radius: 12px;
                background-color: #ffffff;
                selection-background-color: rgba(236, 72, 153, 0.15);
                selection-color: #be185d;
                outline: none;
                padding: 4px;
            }
            """
        )
        return self._combo_box

    def _update_editor(self, value: Any) -> None:
        index = self._combo_box.findData(value)
        if index >= 0:
            self._combo_box.setCurrentIndex(index)



class TipSettingItem(SettingItem):
    """文本提示词。"""    

    def create_editor(self, parent: QWidget) -> QWidget:        # 新增一行小 tip
        self.tip_label = QLabel("💡 提示：修改设置后，请点击底部「保存」按钮生效",parent)
        # 设置样式让它看起来像温和的提示（灰色、小字号）
        self.tip_label.setStyleSheet("""
            color: #888888; 
            font-size: 12px; 
            padding: 8px 0px;
            border: none;
        """)
        # 允许文本自动换行，防止过长被截断
        self.tip_label.setWordWrap(True)
        # 设置为弱文本，在界面上不会抢占焦点
        self.tip_label.setTextInteractionFlags(Qt.NoTextInteraction)

        return self.tip_label

    def _update_editor(self, value: Any) -> None:
        pass