"""好感度边界模块：负责关系状态（好感度）与交互事件的管理。

该模块作为可替换的 MVP 边界，对外暴露好感度快照查询与事件记录能力。
后续可由真正的 affinity 实现（含评分逻辑）替换，而不影响调用方。
"""

from affinity.schema import AffinityEvent
from affinity.service import DEFAULT_LOVE_SNAPSHOT, AffinityService

__all__ = ["AffinityEvent", "AffinityService", "DEFAULT_LOVE_SNAPSHOT"]
