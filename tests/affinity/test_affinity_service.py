from datetime import datetime

import pytest

from app.affinity import AffinityEvent, AffinityService


def test_default_service_returns_mvp_love_snapshot():
    service = AffinityService()

    assert service.get_love_snapshot("u1") == 77
    assert service.get_love_snapshot("u2") == 77


def test_service_accepts_event_and_keeps_users_isolated():
    service = AffinityService()

    assert service.emit_affinity_event("u1", {"type": "user_thanked"}) is None
    service.emit_affinity_event("u2", {"type": "user_complained"})

    assert [item.event for item in service.get_events("u1")] == [
        {"type": "user_thanked"}
    ]
    assert [item.event for item in service.get_events("u2")] == [
        {"type": "user_complained"}
    ]


def test_recorded_event_is_a_defensive_copy():
    service = AffinityService()
    payload = {"type": "memory_written", "memory_ids": ["m1"]}

    service.emit_affinity_event("u1", payload)
    payload["memory_ids"].append("m2")

    recorded = service.get_events("u1")[0]
    assert recorded.event == {"type": "memory_written", "memory_ids": ["m1"]}
    assert recorded.to_dict()["event"] == recorded.event
    assert datetime.fromisoformat(recorded.created_at).tzinfo is not None

    recorded.event["memory_ids"].append("m3")
    assert service.get_events("u1")[0].event["memory_ids"] == ["m1"]


def test_affinity_event_schema_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="user_id"):
        AffinityEvent(user_id="", event={"type": "feedback"})
    with pytest.raises(TypeError, match="event"):
        AffinityEvent(user_id="u1", event="feedback")  # type: ignore[arg-type]


def test_service_validates_snapshot_and_user_id():
    with pytest.raises(ValueError, match="between 0 and 100"):
        AffinityService(default_love_snapshot=101)
    with pytest.raises(TypeError, match="must be an int"):
        AffinityService(default_love_snapshot=True)

    service = AffinityService()
    with pytest.raises(ValueError, match="user_id"):
        service.get_love_snapshot(" ")
    with pytest.raises(ValueError, match="user_id"):
        service.emit_affinity_event("", {"type": "feedback"})


def test_affinity_service_can_be_replaced_without_memory_dependency():
    class DatabaseAffinityService(AffinityService):
        def get_love_snapshot(self, user_id: str) -> int:
            return 88

    replacement = DatabaseAffinityService()

    assert replacement.get_love_snapshot("u1") == 88
