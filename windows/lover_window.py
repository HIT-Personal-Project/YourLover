"""
桌面角色窗口模块
负责：
- 透明窗口渲染
- 悬浮窗口管理
- 拖拽交互
- 右键菜单
- Live2D模型显示
- 点击HitArea检测

不负责：
- 聊天功能（由ChatWindow负责）
- 设置功能（由SettingWindow负责）

事件流示例：
    Mouse点击 -> LoverWindow -> Avatar -> HitArea -> EventBus -> Agent
"""

from typing import Any, Callable

from collections import deque

from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from core.event_bus import event_bus
from windows.base_window import BaseWindow
from widgets.menu.context_menu import ContextMenu
from widgets.menu.menu_builder import MenuBuilder


class LoverWindow(BaseWindow):
    """虚拟伴侣悬浮窗口。

    职责：
    - 承载 Avatar 渲染控件（由外部注入，本窗口不直接依赖 live2d-py）。
    - 实现无边框、透明、置顶悬浮。
    - 实现鼠标拖拽移动。
    - 实现右键弹出菜单（主页、设置、自定义扩展项）。
    - 管理点击区域（HitArea），将点击事件通过 EventBus 转发。
    - 提供摇晃检测接口（具体动画委托给 AvatarController）。

    暴露接口：
    - set_avatar_widget(widget): 注入 Avatar 渲染控件。
    - register_hit_area(name, rect): 注册可点击区域。
    - unregister_hit_area(name): 注销可点击区域。
    - set_context_menu(menu): 设置右键菜单。
    - set_draggable(enabled): 启用/禁用拖拽。
    - shake_avatar(): 触发摇晃动画（委托 AvatarController）。
    - on_avatar_clicked(pos): 处理 Avatar 点击，执行 HitArea 检测。

    信号：
    - hit_area_clicked(name): 点击到某个 HitArea 时发射。
    """

    hit_area_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化悬浮窗口。

        Args:
            parent: 父级窗口，通常为空。
        """
        self._avatar_widget: QWidget | None = None
        self._hit_areas: dict[str, QRect] = {}
        self._context_menu: ContextMenu | None = None
        self._draggable: bool = True
        self._dragging: bool = False
        self._drag_start_pos: QPoint = QPoint()
        self._drag_start_global_pos: QPoint = QPoint()

        # 摇晃检测：记录最近 N 次水平拖拽位移
        self._drag_history: deque[int] = deque(maxlen=10)
        self._shake_threshold: int = 6  # 方向变化次数阈值
        self._shake_cooldown: bool = False
        super().__init__(parent)

    def _setup_window_flags(self) -> None:
        """配置悬浮窗口标志：无边框、透明、置顶、不在任务栏显示。"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def setup_ui(self) -> None:
        """创建窗口基础布局。"""
        # 中央占位控件，等待 Avatar 渲染控件注入
        self._central_widget = QWidget(self)
        self._central_widget.setObjectName("lover_central")
        self.setCentralWidget(self._central_widget)

        # 默认尺寸，后续可根据 Avatar 模型尺寸调整
        self.setFixedSize(320, 400)

        # 默认右键菜单
        self._context_menu = (
            MenuBuilder()
            .add_home("主页")
            .add_settings("设置")
            .add_separator()
            .add_quit("退出")
            .build(parent=self)
        )

        self.apply_style()

    def connect_signals(self) -> None:
        """连接事件总线与本窗口相关信号。"""
        self.hit_area_clicked.connect(event_bus.avatar_hit_area_clicked.emit)

    def apply_style(self) -> None:
        """应用悬浮窗透明样式。"""
        self.setStyleSheet(
            """
            #lover_central {
                background-color: transparent;
            }
            """
        )

    # ============================================================
    # Avatar 与 HitArea 接口
    # ============================================================

    def set_avatar_widget(self, widget: QWidget) -> None:
        """注入 Avatar 渲染控件。

        设计说明：
        - LoverWindow 不直接依赖 live2d-py，只负责提供渲染容器。
        - Avatar 渲染控件由外部（如 WindowManager 或 AvatarController）创建并注入。

        Args:
            widget: Avatar 渲染控件，需为 QWidget 子类。
        """
        if self._avatar_widget is not None:
            self._avatar_widget.setParent(None)
            self._avatar_widget.deleteLater()

        self._avatar_widget = widget
        self.setCentralWidget(widget)

    def register_hit_area(self, name: str, rect: QRect) -> None:
        """注册一个可点击区域（HitArea）。

        Args:
            name: 区域名称，如 "head", "face", "body"。
            rect: 相对于窗口客户区的 QRect。
        """
        self._hit_areas[name] = rect

    def unregister_hit_area(self, name: str) -> None:
        """注销可点击区域。

        Args:
            name: 要注销的区域名称。
        """
        self._hit_areas.pop(name, None)

    def clear_hit_areas(self) -> None:
        """清空所有 HitArea。"""
        self._hit_areas.clear()

    def on_avatar_clicked(self, pos: QPoint) -> None:
        """处理 Avatar 区域内的点击。

        Args:
            pos: 相对于窗口客户区的点击坐标。

        行为：
        - 检测是否命中某个 HitArea，命中则发射 hit_area_clicked 与 EventBus 事件。
        - 未命中任何区域也发射 avatar_clicked，供业务层处理。
        """
        event_bus.avatar_clicked.emit(pos.x(), pos.y())

        for name, rect in self._hit_areas.items():
            if rect.contains(pos):
                self.hit_area_clicked.emit(name)
                return

    # ============================================================
    # 拖拽交互
    # ============================================================

    def set_draggable(self, enabled: bool) -> None:
        """启用或禁用窗口拖拽。

        Args:
            enabled: True 表示可拖拽，False 表示固定位置。
        """
        self._draggable = enabled

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标按下事件：记录拖拽起点，右键弹出菜单。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.position().toPoint()
            self._drag_start_global_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标移动事件：执行窗口拖拽并检测摇晃手势。"""
        if not self._draggable or not self._dragging:
            return

        delta = event.globalPosition().toPoint() - self._drag_start_global_pos
        self.move(self.pos() + delta)
        self._drag_start_global_pos = event.globalPosition().toPoint()
        event_bus.avatar_dragged.emit(delta.x(), delta.y())

        # 摇晃检测：记录水平位移方向变化
        self._drag_history.append(delta.x())
        self._detect_shake()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标释放事件：结束拖拽，同时处理点击。"""
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            event_bus.avatar_drag_finished.emit(
                event.globalPosition().toPoint().x(),
                event.globalPosition().toPoint().y(),
            )

            # 若移动距离很小，视为点击而非拖拽
            move_distance = (
                event.position().toPoint() - self._drag_start_pos
            ).manhattanLength()
            if move_distance < 5:
                self.on_avatar_clicked(event.position().toPoint())

    # ============================================================
    # 右键菜单
    # ============================================================

    def set_context_menu(self, menu: ContextMenu) -> None:
        """设置自定义右键菜单。

        Args:
            menu: ContextMenu 实例。
        """
        if self._context_menu is not None:
            self._context_menu.deleteLater()
        self._context_menu = menu

    def add_context_menu_item(self, item: Any) -> None:
        """向当前右键菜单添加一个菜单项。

        Args:
            item: 实现 ExtensibleItem 的菜单项实例。
        """
        if self._context_menu is not None:
            self._context_menu.add_item(item)

    def _show_context_menu(self, pos: QPoint) -> None:
        """在指定位置显示右键菜单。

        Args:
            pos: 全局坐标。
        """
        if self._context_menu is not None:
            self._context_menu.show_at(pos)

    # ============================================================
    # 动画与效果接口（委托给 AvatarController）
    # ============================================================

    def _detect_shake(self) -> None:
        """基于拖拽历史检测摇晃手势。

        判定逻辑：
        - 最近 10 次水平位移中，方向变化次数超过阈值视为摇晃。
        - 加入冷却时间，避免连续触发。
        """
        if self._shake_cooldown or len(self._drag_history) < 4:
            return

        direction_changes = 0
        last_direction = 0
        for dx in self._drag_history:
            if dx == 0:
                continue
            direction = 1 if dx > 0 else -1
            if last_direction != 0 and direction != last_direction:
                direction_changes += 1
            last_direction = direction

        if direction_changes >= self._shake_threshold:
            self.shake_avatar()
            self._shake_cooldown = True
            self._drag_history.clear()
            QTimer.singleShot(1000, self._reset_shake_cooldown)

    def _reset_shake_cooldown(self) -> None:
        """重置摇晃检测冷却状态。"""
        self._shake_cooldown = False

    def shake_avatar(self) -> None:
        """触发角色摇晃动画。

        说明：
        - 本窗口只负责调用，具体动画由 AvatarController 实现。
        - 当前为预留接口，后续接入 avatar 模块后填充实现。
        """
        event_bus.avatar_shaken.emit()
        # TODO: 调用 AvatarController.play_motion("shake") 或类似接口

    def play_expression(self, expression_name: str) -> None:
        """触发角色表情变化（预留接口）。

        Args:
            expression_name: 表情名称。
        """
        # TODO: 委托 AvatarController.change_expression(expression_name)
        pass

    def set_avatar_state(self, state: str) -> None:
        """设置 Avatar 状态（预留接口）。

        Args:
            state: 状态名称，如 "Idle", "Thinking", "Speaking"。
        """
        event_bus.avatar_state_changed.emit(state)
        # TODO: 委托 AvatarController.set_state(state)
