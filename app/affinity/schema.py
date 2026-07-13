from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    """生成当前 UTC 时间的 ISO 8601 字符串，作为事件创建时间戳。"""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AffinityEvent:
    """好感度边界接收到的交互信号。

    该数据类为不可变（frozen）对象，用于记录一次用户与 Agent 的交互事件。
    M6 阶段仅做信号记录，不对事件进行解释，也不修改权威的好感度分数；
    事件的解读与关系分数的更新由后续真正的 affinity 实现负责。

    字段说明：
        user_id: 用户唯一标识
        event: 事件原始负载（dict），可包含任意事件元数据
        created_at: 事件创建时间（UTC ISO 字符串），默认取当前时间
    """

    user_id: str
    event: dict[str, Any]
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        """初始化后校验：确保 user_id 非空、event 为 dict，并对 event 做深拷贝以避免外部可变引用。"""
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("user_id must not be empty")
        if not isinstance(self.event, dict):
            raise TypeError("event must be a dict")
        # frozen dataclass 无法直接赋值，需通过 object.__setattr__ 写入深拷贝后的 event
        object.__setattr__(self, "event", deepcopy(self.event))

    def to_dict(self) -> dict[str, Any]:
        """将事件序列化为字典，event 字段返回深拷贝以避免外部修改污染内部数据。"""
        return {
            "user_id": self.user_id,
            "event": deepcopy(self.event),
            "created_at": self.created_at,
        }
