from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.memory.schema import MemoryEvidence, now_iso


@dataclass
class ProfileCandidate:
    """A proposed profile update that must be applied by another subsystem."""

    user_id: str
    field: str
    value: str
    reason: str
    needs_user_confirmation: bool = False
    confidence: float = 1.0
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if isinstance(self.evidence, dict):
            self.evidence = MemoryEvidence.from_dict(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "field": self.field,
            "value": self.value,
            "reason": self.reason,
            "needs_user_confirmation": self.needs_user_confirmation,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileCandidate":
        return cls(
            user_id=data["user_id"],
            field=data["field"],
            value=data["value"],
            reason=data["reason"],
            needs_user_confirmation=bool(data.get("needs_user_confirmation", False)),
            confidence=float(data.get("confidence", 1.0)),
            evidence=MemoryEvidence.from_dict(data.get("evidence")),
            created_at=data.get("created_at") or now_iso(),
        )
