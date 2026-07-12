from datetime import datetime, timezone

from app.memory.classifier import MemoryClassifier
from app.memory.profile_candidate import ProfileCandidate


def test_explicit_short_answer_preference_creates_semantic_memory():
    classifier = MemoryClassifier()
    messages = [{"role": "user", "content": "记住我喜欢简短回答", "id": "m1"}]

    memories = classifier.extract_semantic_memories(messages, "u1")

    assert len(memories) == 1
    assert memories[0].scope == "preference"
    assert memories[0].object == "简短回答"
    assert memories[0].evidence.message_ids == ["m1"]
    assert memories[0].expires_at is None


def test_recent_exam_anxiety_creates_expiring_state_memory():
    classifier = MemoryClassifier(state_ttl_days=30)

    memories = classifier.extract_semantic_memories(
        [{"role": "user", "content": "我最近因为期末很焦虑"}], "u1"
    )

    assert len(memories) == 1
    assert memories[0].scope == "state"
    assert memories[0].predicate == "current_state"
    expires_at = datetime.fromisoformat(memories[0].expires_at)
    remaining_days = (expires_at - datetime.now(timezone.utc)).total_seconds() / 86400
    assert 29.9 < remaining_days <= 30


def test_anxiety_to_relief_conversation_creates_episodic_summary():
    classifier = MemoryClassifier()
    messages = [
        {
            "role": "user",
            "content": "期末快到了，我很焦虑，完全不知道怎么复习。",
            "id": "m1",
            "session_id": "s1",
        },
        {
            "role": "assistant",
            "content": "我先陪你把任务按科目拆开，再排一个三天复习计划。",
            "id": "m2",
            "session_id": "s1",
        },
        {
            "role": "user",
            "content": "这样清楚多了，我感觉好多了，谢谢。",
            "id": "m3",
            "session_id": "s1",
        },
    ]

    episode = classifier.summarize_episodic_memory(messages, "u1", love_snapshot=77)

    assert episode is not None
    assert "焦虑" in episode.summary
    assert "复习计划" in episode.summary
    assert "好多了" in episode.summary
    assert episode.session_id == "s1"
    assert episode.love_snapshot == 77
    assert episode.emotion_before == {"anxiety": 0.8}
    assert episode.emotion_after == {"calm": 0.7}
    assert episode.evidence.message_ids == ["m1", "m2", "m3"]


def test_model_inference_is_confirmation_candidate_not_semantic_memory():
    classifier = MemoryClassifier()
    messages = [{"role": "user", "content": "模型猜测用户喜欢先安慰再建议。"}]

    assert classifier.extract_semantic_memories(messages, "u1") == []
    decisions = classifier.classify_memory_candidate(messages)
    profiles = classifier.extract_profile_candidates(messages, "u1")

    assert len(decisions) == 1
    assert decisions[0].should_store is False
    assert decisions[0].needs_user_confirmation is True
    assert len(profiles) == 1
    assert profiles[0].needs_user_confirmation is True


def test_nickname_correction_creates_preference_and_profile_candidate():
    classifier = MemoryClassifier()
    messages = [{"role": "user", "content": "别叫我小王，叫我阿辰。", "id": "m9"}]

    semantics = classifier.extract_semantic_memories(messages, "u1")
    profiles = classifier.extract_profile_candidates(messages, "u1")

    assert semantics[0].scope == "preference"
    assert profiles == [
        ProfileCandidate(
            user_id="u1",
            field="nickname",
            value="阿辰",
            reason="用户明确纠正了称呼。",
            evidence=profiles[0].evidence,
            created_at=profiles[0].created_at,
        )
    ]
    assert profiles[0].evidence.message_ids == ["m9"]


def test_future_output_rule_creates_procedural_candidate():
    classifier = MemoryClassifier()
    messages = [{"role": "user", "content": "以后写周报要按三段式输出。"}]

    candidates = classifier.extract_procedural_candidates(messages, "u1")

    assert len(candidates) == 1
    assert candidates[0].rule_type == "interaction_rule"
    assert candidates[0].needs_user_confirmation is True


def test_low_value_chat_is_not_selected_and_incomplete_episode_is_skipped():
    classifier = MemoryClassifier()
    messages = [
        {"role": "user", "content": "今天天气不错。"},
        {"role": "assistant", "content": "是呀。"},
    ]

    assert classifier.classify_memory_candidate(messages) == []
    assert classifier.extract_semantic_memories(messages, "u1") == []
    assert classifier.summarize_episodic_memory(messages, "u1") is None


def test_langchain_message_objects_are_supported():
    class HumanMessage:
        type = "human"

        def __init__(self, content, message_id):
            self.content = content
            self.id = message_id

    class AIMessage:
        type = "ai"

        def __init__(self, content, message_id):
            self.content = content
            self.id = message_id

    classifier = MemoryClassifier()
    messages = [
        HumanMessage(content="我最近考试压力很大", message_id="m1"),
        AIMessage(content="我们把复习任务拆开安排。", message_id="m2"),
        HumanMessage(content="这个建议很有用，我放心多了。", message_id="m3"),
    ]

    assert classifier.extract_semantic_memories(messages, "u1")[0].scope == "state"
    assert classifier.summarize_episodic_memory(messages, "u1") is not None


def test_profile_candidate_round_trip():
    candidate = ProfileCandidate(
        user_id="u1",
        field="name",
        value="小王",
        reason="用户明确提供了姓名。",
    )

    assert ProfileCandidate.from_dict(candidate.to_dict()).to_dict() == candidate.to_dict()
