from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.affinity import AffinityService
from app.agent.ChatAgent import ChatAgent
from app.config import Settings
from app.memory.retriever import MemoryRetriever
from app.memory.schema import SemanticMemory
from app.memory.store import FileMemoryStore


class RecordingLLM:
    def __init__(self) -> None:
        self.calls: list[list] = []

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.calls.append(list(messages))
        return AIMessage(content="好的，我会温柔地陪着你。")


class ToolCallingLLM(RecordingLLM):
    def invoke(self, messages):
        self.calls.append(list(messages))
        if len(self.calls) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "3**2+5"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content="计算结果是 14。")


def _agent(tmp_path, llm=None, **kwargs):
    store = FileMemoryStore(tmp_path)
    retriever = MemoryRetriever(store)
    affinity = AffinityService()
    agent = ChatAgent(
        llm or RecordingLLM(),
        Settings(),
        {"configurable": {"thread_id": "default"}},
        memory_store=store,
        memory_retriever=retriever,
        affinity_service=affinity,
        **kwargs,
    )
    return agent, store, affinity


def test_explicit_preference_is_written_and_recalled_in_new_session(tmp_path):
    llm = RecordingLLM()
    agent, store, affinity = _agent(tmp_path, llm)

    first = agent.invoke(
        {
            "user_input": "记住我喜欢回答短一点",
            "user_id": "user-a",
            "session_id": "session-1",
        }
    )

    semantics = store.list_memories("user-a", "semantic")
    assert len(semantics) == 1
    assert isinstance(semantics[0], SemanticMemory)
    assert semantics[0].scope == "preference"
    assert first["memory_write_ids"] == [semantics[0].id]

    second = agent.invoke(
        {
            "user_input": "今天过得怎么样？",
            "user_id": "user-a",
            "session_id": "session-2",
        }
    )

    assert "用户偏好：简短回答" in second["memory_context"]
    system_prompt = llm.calls[-1][0]
    assert isinstance(system_prompt, SystemMessage)
    assert "用户偏好：简短回答" in system_prompt.content
    assert "当前好感度快照：77" in system_prompt.content
    assert affinity.get_events("user-a")[-1].event["type"] == "memory_write_completed"


def test_long_term_memory_is_isolated_by_user_id(tmp_path):
    llm = RecordingLLM()
    agent, store, _ = _agent(tmp_path, llm)
    agent.invoke(
        {
            "user_input": "记住我喜欢回答短一点",
            "user_id": "user-a",
            "session_id": "session-a",
        }
    )

    state_b = agent.invoke(
        {
            "user_input": "你好",
            "user_id": "user-b",
            "session_id": "session-b",
        }
    )

    assert state_b["memory_context"] == ""
    assert store.list_memories("user-b") == []
    assert "简短回答" not in llm.calls[-1][0].content


def test_short_term_messages_are_trimmed_by_complete_turn(tmp_path):
    agent, _, _ = _agent(tmp_path, max_messages=4, keep_recent_turns=1)
    session = {"configurable": {"thread_id": "trim-session", "user_id": "user-a"}}

    agent.invoke({"user_input": "第一轮"}, session=session)
    agent.invoke({"user_input": "第二轮"}, session=session)
    state = agent.invoke({"user_input": "第三轮"}, session=session)

    assert [message.content for message in state["messages"]] == [
        "第三轮",
        "好的，我会温柔地陪着你。",
    ]
    assert "第一轮" in state["session_summary"]
    assert "第二轮" in state["session_summary"]


def test_existing_tool_loop_still_returns_tool_result_to_llm(tmp_path):
    llm = ToolCallingLLM()
    agent, _, _ = _agent(tmp_path, llm)

    state = agent.invoke(
        {"user_input": "计算 3**2+5", "user_id": "user-a", "session_id": "tools"}
    )

    assert state["messages"][-1].content == "计算结果是 14。"
    assert any(
        isinstance(message, ToolMessage) and message.content == "14"
        for message in llm.calls[1]
    )
