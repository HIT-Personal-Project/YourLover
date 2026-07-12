"""Affinity boundary for relationship state and interaction events."""

from app.affinity.schema import AffinityEvent
from app.affinity.service import DEFAULT_LOVE_SNAPSHOT, AffinityService

__all__ = ["AffinityEvent", "AffinityService", "DEFAULT_LOVE_SNAPSHOT"]
