from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


SCHEMA_VERSION = "0.1"


class MemoryType(str, Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}_{timestamp}_{uuid4().hex[:8]}"


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _serialize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _coerce_enum(enum_cls: type[Enum], value: Any) -> Enum:
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


@dataclass
class MemoryEvidence:
    session_id: str | None = None
    message_ids: list[str] = field(default_factory=list)
    excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "MemoryEvidence":
        if not data:
            return cls()
        return cls(
            session_id=data.get("session_id"),
            message_ids=list(data.get("message_ids") or []),
            excerpt=data.get("excerpt"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SemanticMemory:
    user_id: str
    content: str
    scope: str = "fact"
    subject: str = "user"
    predicate: str = "fact"
    object: str | None = None
    confidence: float = 1.0
    importance: float = 0.5
    sensitivity: str = "normal"
    status: MemoryStatus = MemoryStatus.ACTIVE
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    last_used_at: str | None = None
    expires_at: str | None = None
    tags: list[str] = field(default_factory=list)
    embedding_text: str | None = None
    id: str = field(default_factory=lambda: _new_id("sem"))
    type: MemoryType = MemoryType.SEMANTIC

    def __post_init__(self) -> None:
        self.type = MemoryType.SEMANTIC
        self.status = _coerce_enum(MemoryStatus, self.status)
        if isinstance(self.evidence, dict):
            self.evidence = MemoryEvidence.from_dict(self.evidence)
        if self.embedding_text is None:
            self.embedding_text = self.content

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticMemory":
        return cls(
            id=data.get("id") or _new_id("sem"),
            user_id=data["user_id"],
            content=data["content"],
            scope=data.get("scope", "fact"),
            subject=data.get("subject", "user"),
            predicate=data.get("predicate", "fact"),
            object=data.get("object"),
            confidence=float(data.get("confidence", 1.0)),
            importance=float(data.get("importance", 0.5)),
            sensitivity=data.get("sensitivity", "normal"),
            status=MemoryStatus(data.get("status", MemoryStatus.ACTIVE.value)),
            evidence=MemoryEvidence.from_dict(data.get("evidence")),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
            last_used_at=data.get("last_used_at"),
            expires_at=data.get("expires_at"),
            tags=list(data.get("tags") or []),
            embedding_text=data.get("embedding_text"),
        )


@dataclass
class EpisodicMemory:
    user_id: str
    summary: str
    session_id: str | None = None
    title: str | None = None
    turn_range: list[int] = field(default_factory=list)
    user_goal: str | None = None
    agent_actions: list[str] = field(default_factory=list)
    outcome: str | None = None
    emotion_before: dict[str, float] = field(default_factory=dict)
    emotion_after: dict[str, float] = field(default_factory=dict)
    love_snapshot: int | None = None
    tools_called: list[str] = field(default_factory=list)
    importance: float = 0.5
    confidence: float = 1.0
    status: MemoryStatus = MemoryStatus.ACTIVE
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    last_used_at: str | None = None
    recall_triggers: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("epi"))
    type: MemoryType = MemoryType.EPISODIC

    def __post_init__(self) -> None:
        self.type = MemoryType.EPISODIC
        self.status = _coerce_enum(MemoryStatus, self.status)
        if isinstance(self.evidence, dict):
            self.evidence = MemoryEvidence.from_dict(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodicMemory":
        return cls(
            id=data.get("id") or _new_id("epi"),
            user_id=data["user_id"],
            summary=data["summary"],
            session_id=data.get("session_id"),
            title=data.get("title"),
            turn_range=list(data.get("turn_range") or []),
            user_goal=data.get("user_goal"),
            agent_actions=list(data.get("agent_actions") or []),
            outcome=data.get("outcome"),
            emotion_before=dict(data.get("emotion_before") or {}),
            emotion_after=dict(data.get("emotion_after") or {}),
            love_snapshot=data.get("love_snapshot"),
            tools_called=list(data.get("tools_called") or []),
            importance=float(data.get("importance", 0.5)),
            confidence=float(data.get("confidence", 1.0)),
            status=MemoryStatus(data.get("status", MemoryStatus.ACTIVE.value)),
            evidence=MemoryEvidence.from_dict(data.get("evidence")),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
            last_used_at=data.get("last_used_at"),
            recall_triggers=list(data.get("recall_triggers") or []),
        )


@dataclass
class ProceduralCandidate:
    user_id: str
    content: str
    rule_type: str = "candidate"
    reason: str | None = None
    needs_user_confirmation: bool = True
    confidence: float = 0.5
    importance: float = 0.5
    status: MemoryStatus = MemoryStatus.ACTIVE
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: _new_id("proc"))
    type: MemoryType = MemoryType.PROCEDURAL

    def __post_init__(self) -> None:
        self.type = MemoryType.PROCEDURAL
        self.status = _coerce_enum(MemoryStatus, self.status)
        if isinstance(self.evidence, dict):
            self.evidence = MemoryEvidence.from_dict(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProceduralCandidate":
        return cls(
            id=data.get("id") or _new_id("proc"),
            user_id=data["user_id"],
            content=data["content"],
            rule_type=data.get("rule_type", "candidate"),
            reason=data.get("reason"),
            needs_user_confirmation=bool(data.get("needs_user_confirmation", True)),
            confidence=float(data.get("confidence", 0.5)),
            importance=float(data.get("importance", 0.5)),
            status=MemoryStatus(data.get("status", MemoryStatus.ACTIVE.value)),
            evidence=MemoryEvidence.from_dict(data.get("evidence")),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
            tags=list(data.get("tags") or []),
        )


@dataclass
class UserMemoryIndex:
    semantic_count: int = 0
    episodic_count: int = 0
    last_compacted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _serialize(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UserMemoryIndex":
        if not data:
            return cls()
        return cls(
            semantic_count=int(data.get("semantic_count", 0)),
            episodic_count=int(data.get("episodic_count", 0)),
            last_compacted_at=data.get("last_compacted_at"),
        )


@dataclass
class UserMemoryFile:
    user_id: str
    schema_version: str = SCHEMA_VERSION
    semantic_memories: list[SemanticMemory] = field(default_factory=list)
    episodic_memories: list[EpisodicMemory] = field(default_factory=list)
    procedural_candidates: list[ProceduralCandidate] = field(default_factory=list)
    index: UserMemoryIndex = field(default_factory=UserMemoryIndex)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        self.semantic_memories = [
            item if isinstance(item, SemanticMemory) else SemanticMemory.from_dict(item)
            for item in self.semantic_memories
        ]
        self.episodic_memories = [
            item if isinstance(item, EpisodicMemory) else EpisodicMemory.from_dict(item)
            for item in self.episodic_memories
        ]
        self.procedural_candidates = [
            item if isinstance(item, ProceduralCandidate) else ProceduralCandidate.from_dict(item)
            for item in self.procedural_candidates
        ]
        if isinstance(self.index, dict):
            self.index = UserMemoryIndex.from_dict(self.index)
        self.refresh_index()

    def refresh_index(self) -> None:
        self.index.semantic_count = sum(
            1 for item in self.semantic_memories if item.status != MemoryStatus.DELETED
        )
        self.index.episodic_count = sum(
            1 for item in self.episodic_memories if item.status != MemoryStatus.DELETED
        )

    def to_dict(self) -> dict[str, Any]:
        self.refresh_index()
        return {
            "schema_version": self.schema_version,
            "user_id": self.user_id,
            "semantic_memories": [item.to_dict() for item in self.semantic_memories],
            "episodic_memories": [item.to_dict() for item in self.episodic_memories],
            "procedural_candidates": [item.to_dict() for item in self.procedural_candidates],
            "index": self.index.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserMemoryFile":
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            user_id=data["user_id"],
            semantic_memories=[
                SemanticMemory.from_dict(item) for item in data.get("semantic_memories", [])
            ],
            episodic_memories=[
                EpisodicMemory.from_dict(item) for item in data.get("episodic_memories", [])
            ],
            procedural_candidates=[
                ProceduralCandidate.from_dict(item)
                for item in data.get("procedural_candidates", [])
            ],
            index=UserMemoryIndex.from_dict(data.get("index")),
            created_at=data.get("created_at") or now_iso(),
            updated_at=data.get("updated_at") or now_iso(),
        )
