"""
事件总线模块
负责：
- 管理整个项目的事件系统
- 提供Signal/Slot机制，实现模块间解耦
- 所有的窗口间通信必须通过EventBus
- 不允许窗口之间互相直接调用

事件流示例：
    AgentReply -> EventBus -> ChatWindow更新 -> Avatar播放动作 -> Audio播放

使用方式：
    event_bus = EventBus()
    event_bus.agent_reply.connect(handle_reply)
    event_bus.agent_reply.emit(data)
"""