from __future__ import annotations

import json

from langchain_core.messages import AIMessage, SystemMessage

from agent.memory.llm_extractor import MemoryExtractionError
from agent.memory.profile_service import (
    ProfileCandidateExtractor,
    ProfileCandidateProposal,
)
from demos.memory_mvp_demo import DEFAULT_MODEL, run_memory_mvp_demo


class NoopProfileExtractor(ProfileCandidateExtractor):
    """测试提取器：不产生画像候选，避免测试连接真实 Ollama。"""

    def extract(
        self,
        user_id: str,
        user_message: str,
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> list[ProfileCandidateProposal]:
        return []


class FailingMemoryExtractor:
    """测试合并提取器：始终抛异常，强制 demo 走规则提取降级路径。"""

    def extract(self, fragments, previous_summary=""):
        raise MemoryExtractionError("测试环境禁用 LLM 合并提取")


class RecordingLLM:
    def __init__(self) -> None:
        self.calls: list[list] = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls.append(list(messages))
        return AIMessage(content="收到，我会记住。")


def test_demo_defaults_to_requested_ollama_model():
    assert DEFAULT_MODEL == "qwen3:8b"


def test_demo_persists_and_recalls_preference_across_fresh_sessions(tmp_path):
    llm = RecordingLLM()

    result = run_memory_mvp_demo(
        llm,
        memory_dir=tmp_path / "users",
        user_id="demo-user",
        session_database=tmp_path / "sessions.sqlite3",
        profile_database=tmp_path / "profiles.sqlite3",
        profile_extractor=NoopProfileExtractor(),
        memory_extractor=FailingMemoryExtractor(),
    )

    assert result.memory_file == tmp_path / "users" / "demo-user.json"
    assert result.memory_file.exists()
    assert result.semantic_memories == ("用户偏好：简短回答。",)
    assert "用户偏好：简短回答" in result.memory_context

    payload = json.loads(result.memory_file.read_text(encoding="utf-8"))
    assert payload["user_id"] == "demo-user"
    assert payload["index"]["semantic_count"] == 1

    second_system_prompt = llm.calls[-1][0]
    assert isinstance(second_system_prompt, SystemMessage)
    assert "用户偏好：简短回答" in second_system_prompt.content
