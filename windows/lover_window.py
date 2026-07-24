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

from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from core.event_bus import event_bus
from windows.base_window import BaseWindow
from widgets.menu.context_menu import ContextMenu
from widgets.menu.menu_builder import MenuBuilder

from core.config import settings



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

        # 拖拽动画控制：只有真正发生定向移动后才触发拖拽动画
        self._drag_started_emitted: bool = False  # 是否已发射 avatar_drag_started
        self._drag_move_threshold: int = 100        # 触发拖拽动画的最小累计移动距离（像素）

        # 摇晃检测：记录最近 N 次水平拖拽位移
        self._drag_history: deque[int] = deque(maxlen=20)
        self._shake_threshold: int = 3  # 方向变化次数阈值
        self._shake_cooldown: bool = False
        self._shake_triggered: bool = False  # 本次按下-释放过程中是否触发过摇晃
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
        ########## TODO #############
        self.setFixedSize(*settings.CHARACTER_WINDOW_SIZE)

        # 默认右键菜单
        self._context_menu = (
            MenuBuilder()
            .add_home("聊天")
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
        - 注入后会让 widget 鼠标事件穿透，并安装事件过滤器作为后备。

        鼠标事件处理（双重保险）：
        1. WA_TransparentForMouseEvents：让 Avatar widget 不接收鼠标事件，
           事件直接穿透到本窗口的 mousePressEvent 等（参考 Simplel2dTest 做法）。
        2. installEventFilter：作为后备，若穿透未生效则由事件过滤器拦截。
        两者互不冲突：若穿透生效，事件过滤器不会被触发。

        Args:
            widget: Avatar 渲染控件，需为 QWidget 子类。
        """
        # 移除旧 widget 的事件过滤器
        if self._avatar_widget is not None:
            self._avatar_widget.removeEventFilter(self)
            self._avatar_widget.setParent(None)
            self._avatar_widget.deleteLater()

        self._avatar_widget = widget
        self.setCentralWidget(widget)

        # ★ 关键：让 Avatar widget 鼠标事件穿透到本窗口
        # 这样 mousePressEvent / mouseMoveEvent / mouseReleaseEvent 能正常触发
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # 后备：安装事件过滤器（穿透生效时不会被触发，无副作用）
        widget.installEventFilter(self)

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
    # 事件过滤器（拦截 Avatar widget 的鼠标事件）
    # ============================================================

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        """事件过滤器：拦截 Avatar widget 的鼠标事件。

        设计说明：
        - Avatar widget（如 QOpenGLWidget）作为 central widget 覆盖整个客户区，
          默认会消费鼠标事件，导致本窗口的 mousePressEvent 等无法触发。
        - 这里在事件到达 Avatar widget 之前拦截，转交给 _handle_mouse_* 统一处理。
        - 返回 True 表示事件已处理，不再传递给 Avatar widget（避免重复消费）。

        Args:
            obj: 事件目标对象。
            event: 事件对象。

        Returns:
            True 表示已处理并拦截；False 表示放行。
        """
        if obj is self._avatar_widget:
            etype = event.type()
            if etype == QEvent.Type.MouseButtonPress:
                self._handle_mouse_press(event)
                return True
            elif etype == QEvent.Type.MouseMove:
                self._handle_mouse_move(event)
                return True
            elif etype == QEvent.Type.MouseButtonRelease:
                self._handle_mouse_release(event)
                return True
        return super().eventFilter(obj, event)

    def _map_to_window(self, pos: QPoint) -> QPoint:
        """将 Avatar widget 本地坐标转换为 LoverWindow 本地坐标。

        Args:
            pos: 相对于 Avatar widget 的坐标。

        Returns:
            相对于 LoverWindow 客户区的坐标。
        """
        if self._avatar_widget is not None:
            return self._avatar_widget.mapTo(self, pos)
        return pos

    # ============================================================
    # 拖拽交互
    # ============================================================

    def set_draggable(self, enabled: bool) -> None:
        """启用或禁用窗口拖拽。

        Args:
            enabled: True 表示可拖拽，False 表示固定位置。
        """
        self._draggable = enabled

    def _handle_mouse_press(self, event: QMouseEvent) -> None:
        """处理鼠标按下（由 mousePressEvent 或事件过滤器调用）。

        设计说明：
        - 按下时不立即触发拖拽动画，只记录起点。
        - 只有在后续 mouseMove 中累计移动超过阈值后，才发射 avatar_drag_started。
        - 这样快速点击（按下立即释放）不会误触发拖拽动画。

        Args:
            event: 鼠标事件。event.position() 是相对于事件来源 widget 的坐标。
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            # 坐标统一转换为 LoverWindow 本地坐标
            self._drag_start_pos = self._map_to_window(event.position().toPoint())
            self._drag_start_global_pos = event.globalPosition().toPoint()
            # 重置拖拽动画标志：等真正移动后才触发
            self._drag_started_emitted = False
            # 重置摇晃标志：本次按下-释放周期开始
            self._shake_triggered = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def _handle_mouse_move(self, event: QMouseEvent) -> None:
        """处理鼠标移动：执行窗口拖拽并检测摇晃手势。

        设计说明：
        - 只有累计移动超过阈值后才发射 avatar_drag_started（避免快速点击误触发）。
        - 拖拽过程中根据本次移动增量方向，发射 avatar_drag_direction。
        """
        if not self._draggable or not self._dragging:
            return

        # 本次移动的增量（_drag_start_global_pos 每帧更新，所以 delta 是单帧增量）
        delta = event.globalPosition().toPoint() - self._drag_start_global_pos

        # 首次定向移动才触发拖拽动画
        if not self._drag_started_emitted:
            move_distance = delta.manhattanLength()
            if move_distance >= self._drag_move_threshold:
                # 累计移动超过阈值，确认是拖拽而非点击
                self._drag_started_emitted = True
                direction = self._calc_drag_direction(delta.x(), delta.y())
                # 拖拽开始，携带初始方向
                event_bus.avatar_drag_started.emit(direction)

        # 执行窗口移动
        self.move(self.pos() + delta)
        self._drag_start_global_pos = event.globalPosition().toPoint()
        event_bus.avatar_dragged.emit(delta.x(), delta.y())

        # 摇晃检测：记录水平位移方向变化
        self._drag_history.append(delta.x())
        self._detect_shake()

    @staticmethod
    def _calc_drag_direction(dx: int, dy: int) -> str:
        """根据单帧移动增量计算主方向。

        判定逻辑：
        - 比较水平/垂直位移绝对值，取较大者作为主方向。
        - dx > 0 → "right"，dx < 0 → "left"
        - dy > 0 → "down"（屏幕 y 轴向下为正），dy < 0 → "up"

        Args:
            dx: 水平增量（像素）。
            dy: 垂直增量（像素）。

        Returns:
            方向字符串："left" / "right" / "up" / "down"。
        """
        if abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"

    def _handle_mouse_release(self, event: QMouseEvent) -> None:
        """处理鼠标释放：根据本次按下-释放过程的行为，触发对应事件。

        设计说明（三者互斥）：
        - 若本次发生过摇晃（_shake_triggered）：不触发任何事件，摇晃动画已在检测时播放。
        - 若本次发生过拖拽（_drag_started_emitted）：触发 avatar_drag_finished → on_drag_end。
        - 若本次是快速点击（未移动）：触发 on_avatar_clicked。
        - 其他情况（轻微移动但未达拖拽阈值）：忽略，不触发任何事件。
        """
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False

            if self._shake_triggered:
                # 摇晃过：摇晃动画已播放，释放时不触发任何事件
                pass
            elif self._drag_started_emitted:
                # 拖拽过：触发拖拽结束动画
                event_bus.avatar_drag_finished.emit(
                    event.globalPosition().toPoint().x(),
                    event.globalPosition().toPoint().y(),
                )
            else:
                # 未发生拖拽/摇晃，判断是否为快速点击
                local_pos = self._map_to_window(event.position().toPoint())
                move_distance = (local_pos - self._drag_start_pos).manhattanLength()
                if move_distance < 5:
                    self.on_avatar_clicked(local_pos)
                # else: 轻微移动但未达拖拽阈值，忽略

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标按下事件（点击在窗口空白区域时触发，Avatar 区域由事件过滤器处理）。"""
        self._handle_mouse_press(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标移动事件。"""
        self._handle_mouse_move(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """鼠标释放事件。"""
        self._handle_mouse_release(event)

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
            self._shake_triggered = True   # 标记本次发生过摇晃，释放时不触发点击/拖拽结束
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
