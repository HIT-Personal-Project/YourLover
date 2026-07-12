from __future__ import annotations

import json

from langchain_core.messages import AIMessage, SystemMessage

from demos.memory_mvp_demo import DEFAULT_MODEL, run_memory_mvp_demo


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

    result = run_memory_mvp_demo(llm, memory_dir=tmp_path, user_id="demo-user")

    assert result.memory_file == tmp_path / "demo-user.json"
    assert result.memory_file.exists()
    assert result.semantic_memories == ("用户偏好：简短回答。",)
    assert "用户偏好：简短回答" in result.memory_context

    payload = json.loads(result.memory_file.read_text(encoding="utf-8"))
    assert payload["user_id"] == "demo-user"
    assert payload["index"]["semantic_count"] == 1

    second_system_prompt = llm.calls[-1][0]
    assert isinstance(second_system_prompt, SystemMessage)
    assert "用户偏好：简短回答" in second_system_prompt.content
