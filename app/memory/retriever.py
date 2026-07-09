from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.memory.schema import EpisodicMemory, MemoryType, SemanticMemory
from app.memory.store import FileMemoryStore, MemoryObject


class MemoryRetriever:
    def __init__(
        self,
        store: FileMemoryStore | None = None,
        root_dir: str | Path | None = None,
    ) -> None:
        self.store = store if store is not None else FileMemoryStore(root_dir)

    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        memory_type: str | MemoryType | None = None,
        top_k: int = 5,
    ) -> list[MemoryObject]:
        if top_k < 1:
            return []

        memories = self.store.list_memories(user_id, memory_type)
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
        if terms:
            scored = [item for item in scored if item[0] > 0]

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [memory for _, _, memory in scored[:top_k]]

    def format_memory_context(self, memories: Iterable[MemoryObject]) -> str:
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
    if not terms:
        return float(getattr(memory, "importance", 0.0))

    text = _searchable_text(memory)
    keyword_score = sum(len(term) for term in terms if term in text)
    if keyword_score == 0:
        return 0.0
    importance = float(getattr(memory, "importance", 0.0))
    return keyword_score + importance


def _query_terms(query: str) -> set[str]:
    normalized = query.strip().lower()
    if not normalized:
        return set()

    terms = set(re.findall(r"[a-z0-9_]+", normalized))
    terms.update(re.findall(r"[\u4e00-\u9fff]{2,}", normalized))
    for match in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        max_size = min(4, len(match))
        for size in range(2, max_size + 1):
            for index in range(0, len(match) - size + 1):
                terms.add(match[index : index + size])
    return terms


def _searchable_text(memory: MemoryObject) -> str:
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
    expires_at = getattr(memory, "expires_at", None)
    if not expires_at:
        return False

    expires_at_datetime = _parse_datetime(expires_at)
    if expires_at_datetime is None:
        return False
    return expires_at_datetime <= datetime.now(timezone.utc)


def _memory_recency(memory: MemoryObject) -> float:
    value = getattr(memory, "last_used_at", None) or getattr(memory, "updated_at", None)
    parsed = _parse_datetime(value)
    if parsed is None:
        return 0.0
    return parsed.timestamp()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
