"""长期记忆检索器。

提供基于关键词匹配 + 重要性 + 时序衰减的轻量检索能力，
从 FileMemoryStore 中召回与当前 query 相关的语义/情节记忆。
未使用向量检索，是 MVP 阶段的规则化实现，后续可替换为向量检索。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from agent.memory.schema import EpisodicMemory, MemoryType, SemanticMemory
from agent.memory.store import FileMemoryStore, MemoryObject


class MemoryRetriever:
    """长期记忆检索器。

    检索流程：
        1. 从 store 加载用户记忆（默认仅语义与情节记忆）；
        2. 过滤掉已过期（expires_at <= now）的记忆；
        3. 对 query 分词，按关键词命中长度 + 重要性打分；
        4. 当存在 query 词时丢弃零分项，否则退化为按重要性排序；
        5. 综合 (分数, 最近使用时间) 降序排序后取 top_k。
    """

    def __init__(
        self,
        store: FileMemoryStore | None = None,
        root_dir: str | Path | None = None,
    ) -> None:
        """初始化检索器。

        参数：
            store: 可选的 FileMemoryStore 实例，未提供时按 root_dir 创建。
            root_dir: store 未提供时使用的记忆根目录。
        """
        self.store = store if store is not None else FileMemoryStore(root_dir)

    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        memory_type: str | MemoryType | None = None,
        top_k: int = 5,
    ) -> list[MemoryObject]:
        """检索与 query 相关的 top_k 条记忆。

        参数：
            user_id: 目标用户
            query: 检索文本（用户输入或空串）
            memory_type: 指定类型则只检索该类型；None 时只检索语义+情节记忆
            top_k: 返回条数上限，<1 时直接返回空列表
        返回按相关度降序的记忆列表。
        """
        if top_k < 1:
            return []

        memories = self.store.list_memories(user_id, memory_type)
        # 未指定类型时默认排除程序性候选（procedural 不直接参与对话检索）
        if memory_type is None:
            memories = [
                memory
                for memory in memories
                if isinstance(memory, (SemanticMemory, EpisodicMemory))
            ]
        terms = _query_terms(query)
        scored = [
            (_score_memory(memory, terms), _memory_recency(memory), memory)
            for memory in memories
            if not _is_expired(memory)
        ]
        # 有 query 词时只保留命中关键词的记忆
        if terms:
            scored = [item for item in scored if item[0] > 0]

        # 主排序键：相关度分数；次排序键：最近使用时间（越近越优先）
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [memory for _, _, memory in scored[:top_k]]

    def format_memory_context(self, memories: Iterable[MemoryObject]) -> str:
        """将记忆列表格式化为可注入 system prompt 的上下文字符串。

        语义记忆以 "- {content}" 形式列出，情节记忆以 "- {title}: {summary}" 形式列出，
        两类分别归入 "Semantic memories:" 与 "Episodic memories:" 小节。
        """
        semantic_lines: list[str] = []
        episodic_lines: list[str] = []

        for memory in memories:
            if isinstance(memory, SemanticMemory):
                semantic_lines.append(f"- {memory.content}")
            elif isinstance(memory, EpisodicMemory):
                label = f"{memory.title}: " if memory.title else ""
                episodic_lines.append(f"- {label}{memory.summary}")

        sections: list[str] = []
        if semantic_lines:
            sections.append("Semantic memories:\n" + "\n".join(semantic_lines))
        if episodic_lines:
            sections.append("Episodic memories:\n" + "\n".join(episodic_lines))
        return "\n\n".join(sections)


def _score_memory(memory: MemoryObject, terms: set[str]) -> float:
    """计算单条记忆与 query 词的匹配分数。

    - 无 query 词时退化为 importance（用于纯偏好召回）；
    - 有关键词时分数 = 关键词命中总长度 + importance；
    - 无任何命中返回 0，表示不相关。
    """
    if not terms:
        return float(getattr(memory, "importance", 0.0))

    text = _searchable_text(memory)
    keyword_score = sum(len(term) for term in terms if term in text)
    if keyword_score == 0:
        return 0.0
    importance = float(getattr(memory, "importance", 0.0))
    return keyword_score + importance


def _query_terms(query: str) -> set[str]:
    """从 query 中抽取检索词集合。

    处理逻辑：
        - 小写化并去首尾空白；
        - 抽取英文/数字/下划线词；
        - 抽取长度>=2 的中文连续片段，并对其做 2~4 字滑窗生成子串，
          以提升短中文 query 的召回率。
    """
    normalized = query.strip().lower()
    if not normalized:
        return set()

    terms = set(re.findall(r"[a-z0-9_]+", normalized))
    terms.update(re.findall(r"[\u4e00-\u9fff]{2,}", normalized))
    # 对中文片段再做滑窗子串，避免只匹配整段
    for match in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        max_size = min(4, len(match))
        for size in range(2, max_size + 1):
            for index in range(0, len(match) - size + 1):
                terms.add(match[index : index + size])
    return terms


def _searchable_text(memory: MemoryObject) -> str:
    """拼接记忆的可检索文本（小写）。

    根据记忆类型收集不同的字段（content/scope/tags/summary/title 等），
    并附加 evidence.excerpt，统一小写后用空格连接，便于关键词命中。
    """
    parts: list[str] = []

    if isinstance(memory, SemanticMemory):
        parts.extend(
            [
                memory.content,
                memory.scope,
                memory.subject,
                memory.predicate,
                memory.object,
                memory.embedding_text,
                *memory.tags,
            ]
        )
    elif isinstance(memory, EpisodicMemory):
        parts.extend(
            [
                memory.title,
                memory.summary,
                memory.user_goal,
                memory.outcome,
                *memory.agent_actions,
                *memory.tools_called,
                *memory.recall_triggers,
            ]
        )
    else:
        parts.extend([getattr(memory, "content", None), *getattr(memory, "tags", [])])

    evidence = getattr(memory, "evidence", None)
    parts.append(getattr(evidence, "excerpt", None))
    return " ".join(part.lower() for part in parts if part)


def _is_expired(memory: MemoryObject) -> bool:
    """判断记忆是否已过期（expires_at <= 当前 UTC 时间）。

    无 expires_at 或解析失败时视为不过期。
    """
    expires_at = getattr(memory, "expires_at", None)
    if not expires_at:
        return False

    expires_at_datetime = _parse_datetime(expires_at)
    if expires_at_datetime is None:
        return False
    return expires_at_datetime <= datetime.now(timezone.utc)


def _memory_recency(memory: MemoryObject) -> float:
    """返回记忆的最近活跃时间戳（last_used_at 优先，否则 updated_at）。

    用于检索排序的次级键：越近用过的记忆优先级越高。解析失败返回 0。
    """
    value = getattr(memory, "last_used_at", None) or getattr(memory, "updated_at", None)
    parsed = _parse_datetime(value)
    if parsed is None:
        return 0.0
    return parsed.timestamp()


def _parse_datetime(value: str | None) -> datetime | None:
    """解析 ISO 8601 时间字符串为 UTC datetime。

    兼容以 'Z' 结尾的 UTC 标记，无时区信息时按 UTC 处理，解析失败返回 None。
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
