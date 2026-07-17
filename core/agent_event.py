"""Agent 与桌面应用之间的事件数据封装"""


from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class AgentEvent:
    """Agent 与桌面应用之间传递的事件数据
    
    用于封装 Agent 的回复、状态变化等信息，供桌面应用各模块消费。
    """
    
    # 事件类型: "reply" | "thinking" | "error" | "affinity_change"
    type: str
    
    # 事件负载数据
    payload: dict[str, Any] = field(default_factory=dict)
    
    # 会话 ID
    session_id: str = ""
    
    # 用户 ID
    user_id: str = ""
    
    # 事件时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 好感度快照（可选）
    love_snapshot: int | None = None
    
    # 记忆上下文（可选）
    memory_context: str | None = None