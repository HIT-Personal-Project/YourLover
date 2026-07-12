from __future__ import annotations

from threading import Lock

from app.affinity.schema import AffinityEvent


DEFAULT_LOVE_SNAPSHOT = 77


class AffinityService:
    """Replaceable MVP boundary for the authoritative affinity system.

    The stub returns a fixed snapshot and keeps emitted events in memory for
    later processing. It intentionally does not read or write memory-module
    data and does not implement affinity scoring.
    """

    def __init__(self, default_love_snapshot: int = DEFAULT_LOVE_SNAPSHOT) -> None:
        if isinstance(default_love_snapshot, bool) or not isinstance(
            default_love_snapshot, int
        ):
            raise TypeError("default_love_snapshot must be an int")
        if not 0 <= default_love_snapshot <= 100:
            raise ValueError("default_love_snapshot must be between 0 and 100")
        self._default_love_snapshot = default_love_snapshot
        self._events: list[AffinityEvent] = []
        self._events_lock = Lock()

    def get_love_snapshot(self, user_id: str) -> int:
        _require_user_id(user_id)
        return self._default_love_snapshot

    def emit_affinity_event(self, user_id: str, event: dict) -> None:
        recorded_event = AffinityEvent(user_id=user_id, event=event)
        with self._events_lock:
            self._events.append(recorded_event)

    def get_events(self, user_id: str | None = None) -> tuple[AffinityEvent, ...]:
        """Return an immutable snapshot of recorded MVP events."""

        if user_id is not None:
            _require_user_id(user_id)
        with self._events_lock:
            events = tuple(
                AffinityEvent(
                    user_id=item.user_id,
                    event=item.event,
                    created_at=item.created_at,
                )
                for item in self._events
            )
        if user_id is None:
            return events
        return tuple(item for item in events if item.user_id == user_id)


def _require_user_id(user_id: str) -> None:
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must not be empty")
