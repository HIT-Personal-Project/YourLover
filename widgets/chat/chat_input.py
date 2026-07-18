"""
聊天输入框组件
包含多行文本输入与发送按钮，支持快捷键发送、禁用/启用状态。
"""

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QWidget,
)

from widgets.base.base_widget import BaseWidget


class _SendShortcutFilter(QObject):
    """拦截 QTextEdit 的 Ctrl+Enter 快捷键并触发发送。

    说明：
    - 由于 QTextEdit 会消费键盘事件，父级 ChatInput 无法直接收到。
    - 通过事件过滤器在 QTextEdit 处理事件前捕获 Ctrl+Enter。
    """

    send_triggered = Signal()

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_triggered.emit()
                return True
        return super().eventFilter(obj, event)


class ChatInput(BaseWidget):
    """聊天输入区域。

    职责：
    - 接收用户文本输入。
    - 提供发送按钮与 Ctrl+Enter 快捷键。
    - 控制输入框启用/禁用状态（等待 Agent 回复时禁用）。

    暴露接口：
    - get_text(): 获取当前输入文本。
    - set_text(text): 设置输入文本。
    - clear(): 清空输入框。
    - set_enabled(enabled): 启用/禁用输入与发送按钮。
    - focus(): 聚焦输入框。

    信号：
    - send_clicked(text): 用户点击发送或按快捷键时发射。
    """

    send_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化输入框组件。

        Args:
            parent: 父级 QWidget。
        """
        super().__init__(parent)

    def setup_ui(self) -> None:
        """创建输入框与发送按钮。"""
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(10)

        # 多行输入框
        self._text_edit = QTextEdit(self)
        self._text_edit.setPlaceholderText("输入消息，Ctrl+Enter 发送...")
        self._text_edit.setFixedHeight(64)
        self._text_edit.setFont(QFont("Microsoft YaHei", 10))

        # 发送按钮
        self._send_button = QPushButton("发送", self)
        self._send_button.setFixedSize(72, 64)
        self._send_button.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))

        self._layout.addWidget(self._text_edit)
        self._layout.addWidget(self._send_button)

        self.apply_style()

    def connect_signals(self) -> None:
        """连接发送按钮与键盘事件。"""
        self._send_button.clicked.connect(self._on_send)

        # 安装快捷键事件过滤器到 QTextEdit
        self._shortcut_filter = _SendShortcutFilter(self)
        self._shortcut_filter.send_triggered.connect(self._on_send)
        self._text_edit.installEventFilter(self._shortcut_filter)

    def apply_style(self) -> None:
        """应用输入区域样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            ChatInput {
                background-color: #fffafc;
                border-top: 1.5px solid #fce7f3;
            }
            """
        )
        self._text_edit.setStyleSheet(
            """
            QTextEdit {
                border: 1.5px solid #fce7f3;
                border-radius: 18px;
                padding: 12px 14px;
                background-color: #fffafc;
                color: #1e293b;
                selection-background-color: rgba(236, 72, 153, 0.2);
            }
            QTextEdit:focus {
                border: 2px solid #ec4899;
                background-color: #ffffff;
            }
            """
        )
        self._send_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ec4899;
                color: white;
                border: none;
                border-radius: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #db2777;
            }
            QPushButton:pressed {
                background-color: #be185d;
            }
            QPushButton:disabled {
                background-color: #fbcfe8;
            }
            """
        )

    def _on_send(self) -> None:
        """处理发送逻辑：非空时发射 send_clicked 并清空输入框。"""
        text = self.get_text().strip()
        if not text:
            return
        self.send_clicked.emit(text)
        self.clear()

    def get_text(self) -> str:
        """获取当前输入框文本。"""
        return self._text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        """设置输入框文本。

        Args:
            text: 要设置的文本。
        """
        self._text_edit.setPlainText(text)

    def clear(self) -> None:
        """清空输入框。"""
        self._text_edit.clear()

    def set_enabled(self, enabled: bool) -> None:
        """启用或禁用输入与发送按钮。

        Args:
            enabled: True 表示启用，False 表示禁用。
        """
        self._text_edit.setEnabled(enabled)
        self._send_button.setEnabled(enabled)

    def focus(self) -> None:
        """聚焦到输入框。"""
        self._text_edit.setFocus()
