"""
窗口管理器
负责：
- 协调 LoverWindow、ChatWindow、SettingWindow 的生命周期。
- 订阅 EventBus 事件并路由到对应窗口。
- 注入 Avatar 渲染控件到 LoverWindow。
- 管理窗口之间的显示/隐藏关系（例如打开设置时隐藏聊天、显示设置）。

设计说明：
- 本模块是窗口层与业务层之间的唯一协调者。
- 窗口之间不直接互相调用，所有通信通过 EventBus。
"""

from typing import Any

from PySide6.QtWidgets import QApplication, QWidget

from core.agent_event import AgentEvent
from core.event_bus import event_bus
from avatar.avatar_controller_protocol import AvatarControllerProtocol
from windows.chat_window import ChatWindow
from windows.lover_window import LoverWindow
from windows.setting_window import SettingWindow


class WindowManager:
    """桌面窗口管理器。

    职责：
    - 创建并持有所有窗口实例。
    - 将 EventBus 事件分发到对应窗口。
    - 维护窗口层级与联动行为。
    - 作为 LoverWindow 与 AvatarController 之间的适配层。

    暴露接口：
    - run(): 启动并显示悬浮窗。
    - quit(): 退出应用。
    - set_avatar_widget(widget): 将 Avatar 控件注入 LoverWindow。
    - set_avatar_controller(controller): 注入 AvatarController，自动转发点击/摇晃事件。
    - show_chat(): 显示聊天窗口。
    - show_settings(): 显示设置面板。
    - hide_secondary_windows(): 隐藏所有二级窗口。
    """

    def __init__(self, app: QApplication) -> None:
        """初始化窗口管理器。

        Args:
            app: QApplication 实例，用于退出应用。
        """
        self._app = app
        self._avatar_controller: AvatarControllerProtocol | None = None

        # 创建窗口实例
        self._lover_window = LoverWindow()
        self._chat_window = ChatWindow()
        self._setting_window = SettingWindow()

        # 加载默认设置项（可替换为从配置文件读取）
        self._setting_window.add_default_settings()

        self._setup_event_routing()

    def _setup_event_routing(self) -> None:
        """配置 EventBus 事件路由。"""
        # 菜单/导航事件
        event_bus.show_chat_window_requested.connect(self.show_chat)
        event_bus.hide_chat_window_requested.connect(self._chat_window.hide_window)
        event_bus.show_setting_window_requested.connect(self.show_settings)
        event_bus.hide_setting_window_requested.connect(self._setting_window.hide_window)
        event_bus.hide_all_secondary_windows_requested.connect(
            self.hide_secondary_windows
        )
        event_bus.application_quit_requested.connect(self.quit)

        # 聊天事件：用户发送消息后同步显示到历史记录
        event_bus.user_message_sent.connect(self._chat_window.append_user_message)

        # Avatar 交互事件：转发给 AvatarController
        event_bus.avatar_clicked.connect(self._on_avatar_clicked)
        event_bus.avatar_hit_area_clicked.connect(self._on_avatar_hit_area)
        event_bus.avatar_shaken.connect(self._on_avatar_shaken)
        event_bus.avatar_state_changed.connect(self._on_avatar_state_changed)
        # 拖拽动画：开始时播放被抓住动画，结束时播放放下动画，过程中传方向
        event_bus.avatar_drag_started.connect(self._on_avatar_drag_started)
        event_bus.avatar_drag_finished.connect(self._on_avatar_drag_finished)

        # 示例：收到 Agent 回复后更新聊天窗口（后续由 AgentClient 发送事件）
        event_bus.agent_reply_received.connect(self._on_agent_reply)

    # ============================================================
    # 公共接口
    # ============================================================

    def run(self) -> None:
        """启动窗口管理器，显示悬浮宠物窗口。"""
        self._lover_window.show_window()

    def quit(self) -> None:
        """退出应用。"""
        self._app.quit()

    def set_avatar_widget(self, widget: QWidget) -> None:
        """将 Avatar 渲染控件注入 LoverWindow。

        Args:
            widget: Avatar 渲染控件。
        """
        self._lover_window.set_avatar_widget(widget)

    def set_avatar_controller(self, controller: AvatarControllerProtocol) -> None:
        """注入 AvatarController 并自动注入其渲染控件。

        说明：
        - 注入后，点击/摇晃等交互事件会自动转发给 controller。
        - controller.get_render_widget() 会被注入到 LoverWindow。

        Args:
            controller: 实现 AvatarControllerProtocol 的控制器实例。
        """
        self._avatar_controller = controller
        self.set_avatar_widget(controller.get_render_widget())

    def show_chat(self) -> None:
        """显示聊天窗口，并使其位于悬浮窗附近。"""
        # 将聊天窗口定位在悬浮窗右侧
        lover_geo = self._lover_window.geometry()
        self._chat_window.move(lover_geo.right() + 20, lover_geo.y())
        self._chat_window.show_window()
        self._chat_window.raise_()

    def show_settings(self) -> None:
        """显示设置面板。

        行为：
        - 若聊天窗口可见，则作为其侧边栏滑出。
        - 否则独立显示。
        """
        anchor = self._chat_window if self._chat_window.isVisible() else None
        self._setting_window.slide_in(anchor)
        self._setting_window.raise_()

    def hide_secondary_windows(self) -> None:
        """隐藏聊天窗口与设置面板，保留悬浮窗。"""
        self._chat_window.hide_window()
        self._setting_window.hide_window()

    # ============================================================
    # 事件处理
    # ============================================================

    def _on_avatar_clicked(self, x: int, y: int) -> None:
        """将原始点击坐标转发给 AvatarController（用于 Live2D HitTest）。

        Args:
            x: 相对于 Avatar 渲染控件的 x 坐标。
            y: 相对于 Avatar 渲染控件的 y 坐标。
        """
        if self._avatar_controller is not None:
            self._avatar_controller.on_click(x, y)

    def _on_avatar_hit_area(self, area_name: str) -> None:
        """将 HitArea 点击事件转发给 AvatarController。

        Args:
            area_name: 被点击的区域名称，如 "head", "body"。
        """
        if self._avatar_controller is not None:
            self._avatar_controller.on_hit_area(area_name)

    def _on_avatar_shaken(self) -> None:
        """将摇晃手势转发给 AvatarController。"""
        if self._avatar_controller is not None:
            self._avatar_controller.on_shake()

    def _on_avatar_drag_started(self, direction: str) -> None:
        """将拖拽开始事件转发给 AvatarController（播放被抓住的动画）。

        Args:
            direction: 拖拽初始方向 "left"/"right"/"up"/"down"。
        """
        if self._avatar_controller is not None:
            self._avatar_controller.on_drag_start(direction)


    def _on_avatar_drag_finished(self, x: int, y: int) -> None:
        """将拖拽结束事件转发给 AvatarController（播放放下的动画）。

        Args:
            x: 拖拽结束时的全局 x 坐标。
            y: 拖拽结束时的全局 y 坐标。
        """
        if self._avatar_controller is not None:
            self._avatar_controller.on_drag_end()

    def _on_avatar_state_changed(self, state_name: str) -> None:
        """将 Avatar 状态变化转发给 AvatarController。

        Args:
            state_name: 新状态名，如 "Idle", "Thinking"。
        """
        if self._avatar_controller is not None:
            self._avatar_controller.set_state(state_name)

    def _on_agent_reply(self, event: AgentEvent) -> None:
        """处理 Agent 回复事件。

        Args:
            event: AgentEvent 事件对象。
        """
        # 确保聊天窗口可见
        if not self._chat_window.isVisible():
            self.show_chat()

        # 由 ChatWindow 自身订阅 agent_reply_received 做更新，
        # 此处仅做窗口管理层的补充逻辑（如震动宠物）。
        self._lover_window.shake_avatar()

    # ============================================================
    # 属性访问
    # ============================================================

    @property
    def lover_window(self) -> LoverWindow:
        """返回悬浮宠物窗口。"""
        return self._lover_window

    @property
    def chat_window(self) -> ChatWindow:
        """返回聊天窗口。"""
        return self._chat_window

    @property
    def setting_window(self) -> SettingWindow:
        """返回设置窗口。"""
        return self._setting_window
