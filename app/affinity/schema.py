from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AffinityEvent:
    """An interaction signal accepted by the affinity boundary.

    M6 records the signal only. Interpreting it or changing the authoritative
    relationship score belongs to a future affinity implementation.
    """

    user_id: str
    event: dict[str, Any]
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("user_id must not be empty")
        if not isinstance(self.event, dict):
            raise TypeError("event must be a dict")
        object.__setattr__(self, "event", deepcopy(self.event))

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "event": deepcopy(self.event),
            "created_at": self.created_at,
        }
