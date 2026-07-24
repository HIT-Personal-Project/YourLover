from widgets.settings.setting_item import TipSettingItem
"""
设置窗口模块
负责：
- 模型设置（Live2D模型选择）
- 换装设置（模型外观、服装）
- API设置（Agent API配置）
- Prompt设置（系统提示词）
- Agent设置（Agent参数）
- 声音设置（TTS、音量）
- 快捷键设置
"""

from typing import Any

from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.event_bus import event_bus
from windows.base_window import BaseWindow
from widgets.settings.setting_item import (
    OptionSettingItem,
    SettingItem,
    SliderSettingItem,
    TextSettingItem,
    ToggleSettingItem,
)
from widgets.settings.setting_panel import SettingPanel


class SettingWindow(BaseWindow):
    """设置面板窗口。

    职责：
    - 以滑出面板形式展示所有设置项。
    - 支持动态添加/移除设置项，便于业务扩展。
    - 收集设置值并通过 EventBus 广播变化。
    - 提供保存与取消入口。

    暴露接口：
    - add_setting_item(item): 添加设置项。
    - remove_setting_item(key): 移除设置项。
    - get_setting_value(key): 获取单个值。
    - get_all_values(): 获取所有值。
    - slide_in(): 滑入显示。
    - slide_out(): 滑出隐藏。
    - save_settings(): 保存设置（触发 EventBus）。

    信号：
    - saved(): 点击保存时发射。
    """

    saved = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化设置窗口。

        Args:
            parent: 父级窗口，通常为空或 ChatWindow。
        """
        self._animation: QPropertyAnimation | None = None
        self._expanded_width: int = 360
        super().__init__(parent)

    def _setup_window_flags(self) -> None:
        """配置设置窗口：无边框、可作为侧边栏弹出。"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("YourLover - 设置")
        self.resize(self._expanded_width, 600)

    def setup_ui(self) -> None:
        """创建设置窗口布局。"""
        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("setting_window_central")
        self.setCentralWidget(self._central_widget)

        self._layout = QVBoxLayout(self._central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        # 顶部标题栏
        self._header_layout = QHBoxLayout()
        self._header_layout.setContentsMargins(16, 12, 16, 12)
        self._header_layout.setSpacing(8)

        self._title_label = QLabel("设置")
        self._title_label.setObjectName("setting_title")

        # 将固定尺寸改为稍大的值，确保文字有足够空间
        self._close_button = QPushButton("✕")  # 建议使用图标字符代替"关闭"二字
        self._close_button.setFixedSize(32, 32)
        self._close_button.setToolTip("关闭设置")
        self._close_button.setObjectName("close_button")  # ← 关键：添加 objectName

        self._header_layout.addWidget(self._title_label)
        self._header_layout.addStretch()
        self._header_layout.addWidget(self._close_button)

        # 设置列表面板
        self._setting_panel = SettingPanel(self)

        # 底部操作栏
        self._footer_layout = QHBoxLayout()
        self._footer_layout.setContentsMargins(16, 12, 16, 12)
        self._footer_layout.setSpacing(10)

        self._save_button = QPushButton("保存")
        self._cancel_button = QPushButton("取消")

        self._footer_layout.addStretch()
        self._footer_layout.addWidget(self._cancel_button)
        self._footer_layout.addWidget(self._save_button)

        # 组装
        header_widget = QWidget()
        header_widget.setLayout(self._header_layout)
        footer_widget = QWidget()
        footer_widget.setLayout(self._footer_layout)

        self._layout.addWidget(header_widget)
        self._layout.addWidget(self._setting_panel, stretch=1)
        self._layout.addWidget(footer_widget)

        self.apply_style()

    def connect_signals(self) -> None:
        """连接按钮信号与 EventBus。"""
        self._close_button.clicked.connect(self.hide_window)
        self._cancel_button.clicked.connect(self.hide_window)
        self._save_button.clicked.connect(self.save_settings)

        # 设置项变化 -> EventBus（SettingPanel 已处理，此处监听本地信号方便调试）
        self._setting_panel.item_value_changed.connect(
            lambda key, value: print(f"[SettingWindow] {key} = {value}")
        )

    def apply_style(self) -> None:
        """应用设置窗口样式（卡通游戏风）。"""
        self.setStyleSheet(
            """
            #setting_window_central {
                background-color: #fdf2f8;
                border-left: 1.5px solid #fce7f3;
            }
            #setting_title {
                font-family: "Microsoft YaHei";
                font-size: 16px;
                font-weight: bold;
                color: #be185d;
            }
            QPushButton {
                padding: 8px 18px;
                border-radius: 14px;
                border: 1.5px solid #fce7f3;
                background-color: #ffffff;
                color: #be185d;
                font-family: "Microsoft YaHei";
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #fce7f3;
                border-color: #f9a8d4;
            }
            QPushButton#save_button {
                background-color: #ec4899;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton#save_button:hover {
                background-color: #db2777;
            }
            QPushButton#save_button:pressed {
                background-color: #be185d;
            }
            QPushButton#close_button {
                padding: 0px;
                border: none;
                background-color: transparent;
                color: #be185d;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#close_button:hover {
                background-color: #fce7f3;
                border-radius: 16px;
            }

            """
        )
        self._save_button.setObjectName("save_button")

    # ============================================================
    # 设置项管理接口
    # ============================================================

    def add_setting_item(self, item: SettingItem) -> None:
        """添加一个设置项。

        Args:
            item: SettingItem 子类实例。
        """
        self._setting_panel.add_item(item)

    def remove_setting_item(self, key: str) -> None:
        """按 key 移除设置项。

        Args:
            key: 设置项键名。
        """
        self._setting_panel.remove_item(key)

    def get_setting_value(self, key: str) -> Any:
        """获取单个设置项的值。

        Args:
            key: 设置项键名。

        Returns:
            当前值，不存在返回 None。
        """
        return self._setting_panel.get_value(key)

    def get_all_values(self) -> dict[str, Any]:
        """获取所有设置项的当前值。"""
        return self._setting_panel.get_values()

    def set_values(self, values: dict[str, Any]) -> None:
        """批量设置多个值。

        Args:
            values: key -> value 字典。
        """
        self._setting_panel.set_values(values)

    def save_settings(self) -> None:
        """保存设置。

        行为：
        - 收集当前所有值。
        - 发射 saved() 信号。
        - 通过 EventBus 通知其他模块保存。
        """
        values = self.get_all_values()
        self.saved.emit()
        event_bus.settings_save_requested.emit()
        event_bus.settings_batch_changed.emit(values)
        self.hide_window()

    # ============================================================
    # 滑入/滑出动画
    # ============================================================

    def slide_in(self, anchor: QWidget | None = None) -> None:
        """从右侧滑入显示。

        Args:
            anchor: 锚定窗口，用于计算显示位置；为空时居中。
        """
        self.show_window()
        self._setup_position(anchor)

        # 简单动画：从右侧外部移动到目标位置
        target_rect = self.geometry()
        start_rect = QRect(
            target_rect.x() + self._expanded_width,
            target_rect.y(),
            target_rect.width(),
            target_rect.height(),
        )
        self._animate_geometry(start_rect, target_rect)

    def slide_out(self) -> None:
        """向右侧滑出隐藏。"""
        target_rect = self.geometry()
        end_rect = QRect(
            target_rect.x() + self._expanded_width,
            target_rect.y(),
            target_rect.width(),
            target_rect.height(),
        )
        self._animate_geometry(target_rect, end_rect)
        if self._animation is not None:
            self._animation.finished.connect(self.hide_window)

    def _setup_position(self, anchor: QWidget | None = None) -> None:
        """根据锚定窗口设置自身位置。

        Args:
            anchor: 锚定窗口。
        """
        if anchor is None:
            screen_geo = self.screen().availableGeometry()
            x = screen_geo.right() - self._expanded_width - 40
            y = (screen_geo.height() - self.height()) // 2
        else:
            anchor_geo = anchor.geometry()
            x = anchor_geo.right() + 8
            y = anchor_geo.y()

        self.move(x, y)

    def _animate_geometry(self, start_rect: QRect, end_rect: QRect) -> None:
        """执行窗口几何动画。

        Args:
            start_rect: 起始矩形。
            end_rect: 结束矩形。
        """
        self.setGeometry(start_rect)
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(250)
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()

    
    # 窗口可移动
    def mousePressEvent(self, event) -> None:
        """记录鼠标按下时的全局偏移量。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            # 记录鼠标全局位置与窗口左上角的差值
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        """根据偏移量实时更新窗口位置。"""
        if self._dragging and self._drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """释放鼠标时停止拖拽。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_position = None
            event.accept()

    # ============================================================
    # 预置常用设置项（便于快速扩展）
    # ============================================================

    def add_default_settings(self) -> None:
        """添加一组默认设置项作为示例。"""
        self.add_setting_item(
            OptionSettingItem(
                key="live2d_model",
                label="Live2D 模型",
                default_value="miku",
                extra={"options": ["miku", "rem", "custom"]},
            )
        )
        self.add_setting_item(
            SliderSettingItem(
                key="volume",
                label="音量",
                default_value=80,
                extra={"min": 0, "max": 100, "help_text": "TTS 与音效音量"},
            )
        )
        self.add_setting_item(
            TextSettingItem(
                key="api_base",
                label="API 地址",
                default_value="http://localhost:11434",
            )
        )
        self.add_setting_item(
            TipSettingItem(
                key="tip",
                label="提示",
                default_value="",
            )
        )

