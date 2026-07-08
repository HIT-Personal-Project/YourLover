import json

import pytest

from app.memory.schema import (
    EpisodicMemory,
    MemoryEvidence,
    MemoryStatus,
    MemoryType,
    SemanticMemory,
)
from app.memory.store import FileMemoryStore, MemoryStoreError


def test_load_user_memory_creates_empty_file(tmp_path):
    store = FileMemoryStore(tmp_path)

    memory_file = store.load_user_memory("u_001")
    payload = json.loads((tmp_path / "u_001.json").read_text(encoding="utf-8"))

    assert memory_file.user_id == "u_001"
    assert payload["schema_version"] == "0.1"
    assert payload["semantic_memories"] == []
    assert payload["episodic_memories"] == []
    assert payload["index"]["semantic_count"] == 0
    assert payload["index"]["episodic_count"] == 0


def test_add_semantic_memory_persists_and_reads_back(tmp_path):
    store = FileMemoryStore(tmp_path)
    memory = SemanticMemory(
        user_id="u_001",
        scope="preference",
        content="User prefers concise answers.",
        predicate="prefers_response_style",
        object="concise answers",
        evidence=MemoryEvidence(session_id="s_001", message_ids=["msg_001"]),
    )

    memory_id = store.add_memory("u_001", memory)
    restored = store.load_user_memory("u_001")

    assert memory_id == memory.id
    assert restored.index.semantic_count == 1
    assert restored.semantic_memories[0].content == "User prefers concise answers."
    assert restored.semantic_memories[0].evidence.message_ids == ["msg_001"]


def test_add_episodic_memory_persists_and_reads_back(tmp_path):
    store = FileMemoryStore(tmp_path)
    memory = EpisodicMemory(
        user_id="u_001",
        session_id="s_001",
        summary="The user was anxious, and planning helped.",
        love_snapshot=77,
        recall_triggers=["exam", "planning"],
    )

    store.add_memory("u_001", memory)
    memories = store.list_memories("u_001", MemoryType.EPISODIC)

    assert len(memories) == 1
    assert memories[0].summary == "The user was anxious, and planning helped."
    assert memories[0].love_snapshot == 77
    assert memories[0].recall_triggers == ["exam", "planning"]


def test_update_memory_updates_fields_and_index(tmp_path):
    store = FileMemoryStore(tmp_path)
    memory_id = store.add_memory(
        "u_001",
        SemanticMemory(user_id="u_001", content="User likes long answers."),
    )

    updated = store.update_memory(
        "u_001",
        memory_id,
        {
            "content": "User likes short answers.",
            "importance": 0.9,
            "tags": ["style"],
        },
    )
    restored = store.load_user_memory("u_001")

    assert updated is True
    assert restored.semantic_memories[0].content == "User likes short answers."
    assert restored.semantic_memories[0].importance == 0.9
    assert restored.semantic_memories[0].tags == ["style"]
    assert restored.index.semantic_count == 1


def test_delete_memory_soft_deletes_and_hides_from_default_list(tmp_path):
    store = FileMemoryStore(tmp_path)
    memory_id = store.add_memory(
        "u_001",
        SemanticMemory(user_id="u_001", content="Temporary fact."),
    )

    deleted = store.delete_memory("u_001", memory_id)
    active_memories = store.list_memories("u_001", MemoryType.SEMANTIC)
    all_memories = store.list_memories("u_001", MemoryType.SEMANTIC, include_deleted=True)
    restored = store.load_user_memory("u_001")

    assert deleted is True
    assert active_memories == []
    assert len(all_memories) == 1
    assert all_memories[0].status == MemoryStatus.DELETED
    assert restored.index.semantic_count == 0


def test_different_users_are_isolated(tmp_path):
    store = FileMemoryStore(tmp_path)

    store.add_memory("u_001", SemanticMemory(user_id="u_001", content="User one fact."))
    store.add_memory("u_002", SemanticMemory(user_id="u_002", content="User two fact."))

    assert (tmp_path / "u_001.json").exists()
    assert (tmp_path / "u_002.json").exists()
    assert store.list_memories("u_001")[0].content == "User one fact."
    assert store.list_memories("u_002")[0].content == "User two fact."


def test_corrupt_memory_file_raises_clear_error(tmp_path):
    (tmp_path / "u_001.json").write_text("{not-json", encoding="utf-8")
    store = FileMemoryStore(tmp_path)

    with pytest.raises(MemoryStoreError, match="not valid JSON"):
        store.load_user_memory("u_001")


def test_add_memory_rejects_cross_user_object(tmp_path):
    store = FileMemoryStore(tmp_path)

    with pytest.raises(ValueError, match="user_id mismatch"):
        store.add_memory("u_001", SemanticMemory(user_id="u_002", content="Wrong owner."))


def test_add_memory_accepts_dict_payload(tmp_path):
    store = FileMemoryStore(tmp_path)

    memory_id = store.add_memory(
        "u_001",
        {
            "type": "semantic",
            "content": "User studies at night.",
            "scope": "fact",
        },
    )
    memories = store.list_memories("u_001", "semantic")

    assert memory_id
    assert memories[0].type == MemoryType.SEMANTIC
    assert memories[0].content == "User studies at night."
