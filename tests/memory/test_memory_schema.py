import json

from agent.memory.schema import (
    EpisodicMemory,
    MemoryEvidence,
    MemoryStatus,
    MemoryType,
    ProceduralCandidate,
    SemanticMemory,
    UserMemoryFile,
)


def test_construct_semantic_memory_and_json_round_trip():
    memory = SemanticMemory(
        user_id="u_001",
        scope="preference",
        content="用户喜欢回答短一点。",
        subject="user",
        predicate="prefers_response_style",
        object="short answers",
        confidence=0.92,
        importance=0.8,
        evidence=MemoryEvidence(
            session_id="s_001",
            message_ids=["msg_001"],
            excerpt="记住：我喜欢你回答短一点。",
        ),
        tags=["style"],
    )

    payload = memory.to_dict()
    restored = SemanticMemory.from_dict(json.loads(json.dumps(payload, ensure_ascii=False)))

    assert payload["type"] == MemoryType.SEMANTIC.value
    assert payload["status"] == MemoryStatus.ACTIVE.value
    assert payload["created_at"]
    assert payload["updated_at"]
    assert payload["embedding_text"] == "用户喜欢回答短一点。"
    assert restored.user_id == "u_001"
    assert restored.scope == "preference"
    assert restored.evidence.message_ids == ["msg_001"]


def test_construct_episodic_memory_with_love_snapshot():
    memory = EpisodicMemory(
        user_id="u_001",
        session_id="s_001",
        title="期末压力陪伴对话",
        summary="用户表达期末压力，Agent 先共情再拆分复习计划，用户反馈有帮助。",
        turn_range=[3, 8],
        user_goal="缓解考试焦虑并获得复习建议",
        agent_actions=["情绪安抚", "制定复习拆分计划"],
        outcome="用户反馈有帮助",
        emotion_before={"anxiety": 0.8},
        emotion_after={"calm": 0.6},
        love_snapshot=77,
        recall_triggers=["考试压力", "复习计划"],
        evidence=MemoryEvidence(
            session_id="s_001",
            message_ids=["msg_003", "msg_008"],
            excerpt="谢谢你，我感觉好多了。",
        ),
    )

    payload = memory.to_dict()
    restored = EpisodicMemory.from_dict(payload)

    assert payload["type"] == MemoryType.EPISODIC.value
    assert payload["love_snapshot"] == 77
    assert payload["status"] == MemoryStatus.ACTIVE.value
    assert payload["created_at"]
    assert payload["updated_at"]
    assert restored.love_snapshot == 77
    assert restored.agent_actions == ["情绪安抚", "制定复习拆分计划"]


def test_construct_procedural_candidate():
    candidate = ProceduralCandidate(
        user_id="u_001",
        content="以后写周报按三段式输出。",
        rule_type="output_format",
        reason="用户给出了未来回复格式偏好。",
        evidence=MemoryEvidence(session_id="s_001", message_ids=["msg_009"]),
    )

    payload = candidate.to_dict()
    restored = ProceduralCandidate.from_dict(payload)

    assert payload["type"] == MemoryType.PROCEDURAL.value
    assert payload["needs_user_confirmation"] is True
    assert restored.rule_type == "output_format"


def test_construct_user_memory_file_matching_design_shape():
    semantic = SemanticMemory(
        user_id="u_001",
        scope="state",
        content="用户最近因为期末考试感到压力大。",
        predicate="current_state",
        object="期末考试压力大",
        expires_at="2026-08-05T12:00:00+08:00",
    )
    episodic = EpisodicMemory(
        user_id="u_001",
        session_id="s_001",
        summary="用户焦虑后接受了复习拆分计划。",
        love_snapshot=77,
    )

    memory_file = UserMemoryFile(
        user_id="u_001",
        semantic_memories=[semantic],
        episodic_memories=[episodic],
    )

    payload = memory_file.to_dict()
    restored = UserMemoryFile.from_dict(json.loads(json.dumps(payload, ensure_ascii=False)))

    assert payload["schema_version"] == "0.1"
    assert payload["user_id"] == "u_001"
    assert set(payload) == {
        "schema_version",
        "user_id",
        "semantic_memories",
        "episodic_memories",
        "procedural_candidates",
        "index",
        "created_at",
        "updated_at",
    }
    assert payload["index"]["semantic_count"] == 1
    assert payload["index"]["episodic_count"] == 1
    assert payload["procedural_candidates"] == []
    assert restored.semantic_memories[0].object == "期末考试压力大"
    assert restored.episodic_memories[0].love_snapshot == 77
