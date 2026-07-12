from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app.memory.profile_candidate import ProfileCandidate
from app.memory.schema import EpisodicMemory, MemoryEvidence, ProceduralCandidate, SemanticMemory


STATE_TTL_DAYS = 30


@dataclass(frozen=True)
class MemoryCandidateDecision:
    should_store: bool
    memory_types: tuple[str, ...]
    reason: str
    confidence: float
    needs_user_confirmation: bool = False


@dataclass(frozen=True)
class _MessageView:
    role: str
    content: str
    message_id: str | None
    session_id: str | None
    index: int


class MemoryClassifier:
    """Rule-based MVP for deciding and extracting long-term memory candidates.

    This class only creates candidates. It intentionally does not persist them,
    mutate a user profile, or update affinity state.
    """

    def __init__(self, state_ttl_days: int = STATE_TTL_DAYS) -> None:
        if state_ttl_days < 1:
            raise ValueError("state_ttl_days must be greater than or equal to 1")
        self.state_ttl_days = state_ttl_days

    def classify_memory_candidate(self, messages: list[Any]) -> list[MemoryCandidateDecision]:
        decisions: list[MemoryCandidateDecision] = []
        for message in _view_messages(messages):
            if message.role != "user" or not message.content:
                continue
            if _is_model_inference(message.content):
                decisions.append(
                    MemoryCandidateDecision(
                        should_store=False,
                        memory_types=("profile_candidate",),
                        reason="模型推断缺少用户直接证据，需要先向用户确认。",
                        confidence=0.4,
                        needs_user_confirmation=True,
                    )
                )
                continue

            scopes = _semantic_scopes(message.content)
            types: list[str] = ["semantic"] if scopes else []
            if _looks_procedural(message.content):
                types.append("procedural")
            if _profile_field_value(message.content) is not None:
                types.append("profile_candidate")
            if types:
                decisions.append(
                    MemoryCandidateDecision(
                        should_store=True,
                        memory_types=tuple(dict.fromkeys(types)),
                        reason="用户提供了明确的身份、偏好、状态、目标或未来交互规则。",
                        confidence=0.95 if _has_strong_trigger(message.content) else 0.85,
                    )
                )

        if self._episodic_parts(messages) is not None:
            decisions.append(
                MemoryCandidateDecision(
                    should_store=True,
                    memory_types=("episodic",),
                    reason="对话包含明确的问题、Agent 行动和用户反馈结果。",
                    confidence=0.9,
                )
            )
        return decisions

    def extract_semantic_memories(
        self, messages: list[Any], user_id: str
    ) -> list[SemanticMemory]:
        _require_user_id(user_id)
        memories: list[SemanticMemory] = []
        seen: set[tuple[str, str]] = set()
        for message in _view_messages(messages):
            if message.role != "user" or _is_model_inference(message.content):
                continue
            for scope in _semantic_scopes(message.content):
                content, predicate, value = _semantic_value(message.content, scope)
                key = (scope, content)
                if key in seen:
                    continue
                seen.add(key)
                memories.append(
                    SemanticMemory(
                        user_id=user_id,
                        scope=scope,
                        content=content,
                        predicate=predicate,
                        object=value,
                        confidence=0.98 if _has_strong_trigger(message.content) else 0.9,
                        importance=0.8 if scope in {"preference", "profile_candidate"} else 0.7,
                        expires_at=self._state_expiry() if scope == "state" else None,
                        tags=[scope],
                        evidence=_evidence(message),
                    )
                )
        return memories

    def summarize_episodic_memory(
        self,
        messages: list[Any],
        user_id: str,
        love_snapshot: int | None = None,
    ) -> EpisodicMemory | None:
        _require_user_id(user_id)
        parts = self._episodic_parts(messages)
        if parts is None:
            return None
        problem, actions, result, views = parts
        ids = [item.message_id for item in views if item.message_id]
        session_id = next((item.session_id for item in views if item.session_id), None)
        before = {"anxiety": 0.8} if _contains_any(problem, ("焦虑", "压力", "紧张")) else {}
        after = {"calm": 0.7} if _contains_any(result, ("好多", "缓解", "平静", "放心")) else {}
        triggers = _recall_triggers(problem)
        return EpisodicMemory(
            user_id=user_id,
            session_id=session_id,
            title=_episode_title(problem),
            summary=f"用户表达{_trim(problem)}；Agent {_trim('；'.join(actions))}；随后用户反馈{_trim(result)}。",
            turn_range=[views[0].index, views[-1].index],
            user_goal=_trim(problem),
            agent_actions=[_trim(action) for action in actions],
            outcome=_trim(result),
            emotion_before=before,
            emotion_after=after,
            love_snapshot=love_snapshot,
            importance=0.8,
            confidence=0.9,
            recall_triggers=triggers,
            evidence=MemoryEvidence(
                session_id=session_id,
                message_ids=ids,
                excerpt=" | ".join(_trim(item.content, 80) for item in views),
            ),
        )

    def extract_procedural_candidates(
        self, messages: list[Any], user_id: str
    ) -> list[ProceduralCandidate]:
        _require_user_id(user_id)
        candidates: list[ProceduralCandidate] = []
        for message in _view_messages(messages):
            if message.role != "user" or _is_model_inference(message.content):
                continue
            if _looks_procedural(message.content):
                candidates.append(
                    ProceduralCandidate(
                        user_id=user_id,
                        content=_trim(message.content),
                        rule_type="interaction_rule",
                        reason="用户明确给出了未来交互或输出规则。",
                        needs_user_confirmation=True,
                        confidence=0.9,
                        importance=0.7,
                        evidence=_evidence(message),
                        tags=["rule_candidate"],
                    )
                )
        return candidates

    def extract_profile_candidates(
        self, messages: list[Any], user_id: str
    ) -> list[ProfileCandidate]:
        _require_user_id(user_id)
        candidates: list[ProfileCandidate] = []
        for message in _view_messages(messages):
            if message.role != "user":
                continue
            if _is_model_inference(message.content):
                candidates.append(
                    ProfileCandidate(
                        user_id=user_id,
                        field="inferred_preference",
                        value=_trim(message.content),
                        reason="该内容来自模型推断而非用户明确陈述。",
                        needs_user_confirmation=True,
                        confidence=0.4,
                        evidence=_evidence(message),
                    )
                )
                continue
            profile = _profile_field_value(message.content)
            if profile is not None:
                field, value, reason = profile
                candidates.append(
                    ProfileCandidate(
                        user_id=user_id,
                        field=field,
                        value=value,
                        reason=reason,
                        evidence=_evidence(message),
                    )
                )
        return candidates

    def _state_expiry(self) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=self.state_ttl_days)).isoformat()

    def _episodic_parts(
        self, messages: list[Any]
    ) -> tuple[str, list[str], str, list[_MessageView]] | None:
        views = _view_messages(messages)
        problems = [
            item for item in views
            if item.role == "user" and _contains_any(item.content, _PROBLEM_WORDS)
        ]
        actions = [
            item for item in views
            if item.role == "assistant" and item.content.strip()
        ]
        results = [
            item for item in views
            if item.role == "user" and _contains_any(item.content, _RESULT_WORDS)
        ]
        if not problems or not actions or not results:
            return None
        problem = problems[0]
        result = next((item for item in results if item.index > actions[0].index), None)
        if result is None or result.index <= problem.index:
            return None
        relevant_actions = [
            item.content for item in actions if problem.index < item.index < result.index
        ]
        if not relevant_actions:
            return None
        relevant_views = [item for item in views if problem.index <= item.index <= result.index]
        return problem.content, relevant_actions, result.content, relevant_views


_PROBLEM_WORDS = ("焦虑", "压力", "紧张", "难过", "失眠", "困扰", "问题", "怎么办")
_RESULT_WORDS = (
    "好多了", "好一些", "缓解", "平静", "有帮助", "有用", "解决了", "明白了", "谢谢"
)


def _view_messages(messages: Iterable[Any]) -> list[_MessageView]:
    return [_message_view(message, index) for index, message in enumerate(messages)]


def _message_view(message: Any, index: int) -> _MessageView:
    if isinstance(message, str):
        return _MessageView("user", message.strip(), None, None, index)
    if isinstance(message, dict):
        role = message.get("role") or message.get("type") or "user"
        content = message.get("content", "")
        message_id = message.get("id") or message.get("message_id")
        metadata = message.get("metadata") or message.get("additional_kwargs") or {}
        session_id = message.get("session_id") or metadata.get("session_id")
    else:
        role = getattr(message, "role", None) or getattr(message, "type", None)
        role = role or _role_from_class_name(message.__class__.__name__)
        content = getattr(message, "content", "")
        message_id = getattr(message, "id", None) or getattr(message, "message_id", None)
        metadata = (
            getattr(message, "metadata", None)
            or getattr(message, "additional_kwargs", None)
            or {}
        )
        session_id = getattr(message, "session_id", None) or metadata.get("session_id")
    if isinstance(content, list):
        content = " ".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in content
        )
    return _MessageView(
        _normalize_role(str(role)), str(content).strip(), message_id, session_id, index
    )


def _role_from_class_name(name: str) -> str:
    lowered = name.lower()
    if "human" in lowered:
        return "user"
    if "ai" in lowered or "assistant" in lowered:
        return "assistant"
    return "user"


def _normalize_role(role: str) -> str:
    role = role.lower()
    if role in {"human", "user"}:
        return "user"
    if role in {"ai", "assistant"}:
        return "assistant"
    return role


def _semantic_scopes(text: str) -> list[str]:
    scopes: list[str] = []
    if re.search(r"(?:我喜欢|我不喜欢|喜欢你回答|回答.{0,8}(?:短|简洁)|别叫我|叫我)", text):
        scopes.append("preference")
    if re.search(r"(?:我最近|最近我)", text):
        scopes.append("state")
    if re.search(r"(?:我叫|我是)", text):
        scopes.append("profile_candidate")
    if re.search(r"(?:我想|我的目标是|我打算)", text):
        scopes.append("fact")
    if _has_strong_trigger(text) and not scopes:
        scopes.append("fact")
    return scopes


def _semantic_value(text: str, scope: str) -> tuple[str, str, str]:
    cleaned = _clean_trigger(text)
    if scope == "preference":
        if re.search(r"(?:回答.{0,8}(?:短|简洁)|简短回答|回答短一点)", cleaned):
            value = "简短回答"
        else:
            value = cleaned
        return f"用户偏好：{value}。", "preference", value
    if scope == "state":
        return f"用户当前状态：{cleaned}。", "current_state", cleaned
    if scope == "profile_candidate":
        return f"用户画像候选：{cleaned}。", "profile", cleaned
    return f"用户陈述：{cleaned}。", "fact", cleaned


def _profile_field_value(text: str) -> tuple[str, str, str] | None:
    correction = re.search(r"别叫我[^，。,.！!]*[，, ]*叫我(?P<value>[^，。,.！!]+)", text)
    if correction:
        return "nickname", correction.group("value").strip(), "用户明确纠正了称呼。"
    name = re.search(r"我叫(?P<value>[^，。,.！!]+)", text)
    if name:
        return "name", name.group("value").strip(), "用户明确提供了姓名。"
    identity = re.search(r"我是(?P<value>[^，。,.！!]+)", text)
    if identity:
        return "identity", identity.group("value").strip(), "用户明确提供了身份信息。"
    return None


def _looks_procedural(text: str) -> bool:
    return bool(re.search(r"(?:以后|今后|每次).{0,30}(?:要|记得|按照|按|先|不要)", text))


def _has_strong_trigger(text: str) -> bool:
    return bool(re.search(r"(?:记住|请记得|你要记得)", text))


def _is_model_inference(text: str) -> bool:
    return _contains_any(text, ("模型猜测", "模型推断", "推测用户", "猜测用户", "可能喜欢"))


def _clean_trigger(text: str) -> str:
    cleaned = re.sub(r"^\s*(?:请)?(?:记住|记得)[，,:：\s]*", "", text.strip())
    return cleaned.rstrip("。.!！ ")


def _evidence(message: _MessageView) -> MemoryEvidence:
    return MemoryEvidence(
        session_id=message.session_id,
        message_ids=[message.message_id] if message.message_id else [],
        excerpt=message.content,
    )


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _trim(text: str, limit: int = 100) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().strip("。.!！")
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 1]}…"


def _episode_title(problem: str) -> str:
    if _contains_any(problem, ("考试", "期末", "复习")):
        return "考试压力支持对话"
    return "问题解决对话"


def _recall_triggers(problem: str) -> list[str]:
    triggers = [word for word in ("期末", "考试", "复习", "焦虑", "压力", "失眠") if word in problem]
    return triggers or [_trim(problem, 20)]


def _require_user_id(user_id: str) -> None:
    if not user_id or not user_id.strip():
        raise ValueError("user_id must not be empty")
