"""好感度边界模块：负责关系状态（好感度）与交互事件的管理。

- AffinityStore      好感度 SQLite 持久化（初始 0，上限 100）
- AffinityService    好感度服务：读取快照、应用增量、事件记录
- AffinityEvent      交互事件（观测与审计）

好感度增量由主 LLM 在回复末尾输出的 <<+N>> / <<-N>> 标记给出，
由 ChatAgent.judge_affinity 节点解析后调用 AffinityService.apply_delta
累加持久化（无单独的判定器组件）。
"""

from agent.affinity.affinity_store import AffinityStore, AffinityStoreError
from agent.affinity.schema import AffinityEvent
from agent.affinity.service import DEFAULT_LOVE_SNAPSHOT, AffinityService

__all__ = [
    "AffinityEvent",
    "AffinityService",
    "AffinityStore",
    "AffinityStoreError",
    "DEFAULT_LOVE_SNAPSHOT",
]
