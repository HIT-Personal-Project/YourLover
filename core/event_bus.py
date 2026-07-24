"""
事件总线模块
负责：
- 管理整个项目的事件系统
- 提供 Signal/Slot 机制，实现模块间解耦
- 所有的窗口间通信必须通过 EventBus
- 不允许窗口之间互相直接调用

事件流示例：
    AgentReply -> EventBus -> ChatWindow更新 -> Avatar播放动作 -> Audio播放

使用方式：
    from core.event_bus import event_bus
    event_bus.agent_reply.connect(handle_reply)
    event_bus.agent_reply.emit(data)
"""

from typing import Any

from PySide6.QtCore import QObject, Signal

from core.agent_event import AgentEvent


class EventBus(QObject):
    """全局事件总线（基于 PyQt Signal/Slot）

    设计说明：
    - 本类以单例形式暴露（见末尾 event_bus），所有模块共用同一实例。
    - 所有信号均携带足够上下文，接收方无需回调查询发送方。
    - 新增事件类型时，直接在此添加信号并补充中文注释，保持集中管理。
    """

    # ============================================================
    # Avatar / 桌面宠物交互事件
    # ============================================================

    # 参数：部位名称（如 "head", "face", "body", "hand" ----- and so on）
    avatar_hit_area_clicked = Signal(str)

    # 参数：鼠标在屏幕上的全局坐标 x, y
    avatar_clicked = Signal(int, int)

    # 参数：拖拽初始方向（"left", "right", "up", "down"），首次定向移动时触发
    avatar_drag_started = Signal(str)

    # 参数：拖拽偏移量 dx, dy（本次移动的像素差）
    avatar_dragged = Signal(int, int)

    # 参数：拖拽方向（"left", "right", "up", "down"），拖拽过程中持续触发
    avatar_drag_direction = Signal(str)

    # 参数：拖拽结束时的全局坐标 x, y
    avatar_drag_finished = Signal(int, int)

    # 无参数，表示检测到摇晃手势
    avatar_shaken = Signal()

    # Avatar 状态变化，参数：状态名（如 "Idle", "Thinking", "Speaking"）
    avatar_state_changed = Signal(str)

    # Avatar 表情变化，参数：表情名（如 "Happy", "Sad", "Angry"）
    avatar_expression_changed = Signal(str)
    

    # ============================================================
    # 右键菜单 / 导航事件
    # ============================================================

    # 用户请求打开主页（聊天窗口）
    menu_home_requested = Signal()

    # 用户请求打开设置面板
    menu_settings_requested = Signal()

    # 用户请求退出应用
    menu_quit_requested = Signal()

    # 通用菜单项被触发，参数：item_id, payload
    menu_item_triggered = Signal(str, dict)

    # ============================================================
    # 聊天窗口事件
    # ============================================================

    # 用户发送消息，参数：文本内容
    user_message_sent = Signal(str)

    # Agent 回复事件（已封装为 AgentEvent）
    agent_reply_received = Signal(AgentEvent)

    # Agent 开始思考（用于显示思考动画/状态）
    agent_thinking_started = Signal()

    # Agent 思考结束
    agent_thinking_finished = Signal()

    # 流式回复片段，参数：当前片段文本
    agent_stream_chunk = Signal(str)


    # ============================================================
    # 状态栏控制事件
    # ============================================================
    state_emotion_change = Signal(str)

    state_love_change = Signal(int)



    # ============================================================
    # 设置面板事件
    # ============================================================

    # 设置项值发生变化，参数：setting_key, new_value
    setting_changed = Signal(str, object)

    # 批量设置变更，参数：dict[key, value]
    settings_batch_changed = Signal(dict)

    # 设置面板请求保存（可触发持久化）
    settings_save_requested = Signal()

    # ============================================================
    # 窗口管理事件
    # ============================================================

    # 请求显示聊天窗口
    show_chat_window_requested = Signal()

    # 请求隐藏聊天窗口
    hide_chat_window_requested = Signal()

    # 请求显示设置窗口/面板
    show_setting_window_requested = Signal()

    # 请求隐藏设置窗口/面板
    hide_setting_window_requested = Signal()

    # 请求隐藏所有二级窗口（保留宠物悬浮窗）
    hide_all_secondary_windows_requested = Signal()

    # 应用退出
    application_quit_requested = Signal()

    def __init__(self) -> None:
        """初始化事件总线，所有信号已作为类属性定义。"""
        super().__init__()

    # 便捷方法：安全发射信号（避免未连接时异常）
    def emit_safe(self, signal_name: str, *args: Any, **kwargs: Any) -> None:
        """按名称安全触发信号，主要用于反射或动态场景。

        Args:
            signal_name: 信号属性名。
            *args: 传递给信号的位置参数。
            **kwargs: 预留参数（Signal 不支持关键字参数，忽略）。
        """
        signal = getattr(self, signal_name, None)
        if signal is not None and isinstance(signal, Signal):
            signal.emit(*args)


# 全局唯一事件总线实例
# 所有模块均通过 from core.event_bus import event_bus 引用
event_bus = EventBus()
