"""LangGraph chat agent with the M7 long-term-memory integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.affinity.service import AffinityService
from app.config import Settings
from app.memory.classifier import MemoryClassifier
from app.memory.EmotionMemory import EmotionState
from app.memory.MemoryItem import MemoryItem
from app.memory.retriever import MemoryRetriever
from app.memory.schema import MemoryType, SemanticMemory
from app.memory.store import FileMemoryStore
from app.memory.window import select_messages_for_memory_write, trim_messages
from app.tools import tool_map


class ChatAgent:
    """Emotional companion agent composed from the memory-module boundaries."""

    def __init__(
        self,
        llm: Any,
        config: Settings,
        session: dict[str, Any],
        *,
        memory_store: FileMemoryStore | None = None,
        memory_retriever: MemoryRetriever | None = None,
        memory_classifier: MemoryClassifier | None = None,
        affinity_service: AffinityService | None = None,
        max_messages: int = 20,
        keep_recent_turns: int = 6,
    ) -> None:
        if max_messages < 1:
            raise ValueError("max_messages must be greater than or equal to 1")
        if keep_recent_turns < 0:
            raise ValueError("keep_recent_turns must be greater than or equal to 0")

        self.config = config
        self.session = session
        self.llm = llm
        self.tools = tool_map
        self.system_prompt = config.TEST_SYSTEM_PROMPT
        self.memory_store = memory_store or FileMemoryStore()
        self.memory_retriever = memory_retriever or MemoryRetriever(self.memory_store)
        self.memory_classifier = memory_classifier or MemoryClassifier()
        self.affinity_service = affinity_service or AffinityService()
        self.max_messages = max_messages
        self.keep_recent_turns = keep_recent_turns
        self.llm_with_tools = (
            self.llm.bind_tools(list(self.tools.values()))
            if hasattr(self.llm, "bind_tools")
            else self.llm
        )
        self.__build_workflow()

    def invoke(
        self, user_input: dict[str, Any], session: dict[str, Any] | None = None
    ) -> EmotionState:
        """Run one turn.

        ``user_id`` identifies durable memory ownership; ``session_id`` (or the
        LangGraph ``thread_id``) identifies short-term conversation state.
        """

        runtime_session = session or self.session
        configurable = dict(runtime_session.get("configurable") or {})
        payload = dict(user_input)
        session_id = str(
            payload.get("session_id") or configurable.get("thread_id") or "default-session"
        )
        user_id = str(
            payload.get("user_id") or configurable.get("user_id") or "default-user"
        )
        configurable["thread_id"] = session_id
        runtime_session = {**runtime_session, "configurable": configurable}
        payload.update(user_id=user_id, session_id=session_id)
        return self.workflow.invoke(payload, config=runtime_session)

    def save_graph_figure(self, filename: str) -> None:
        graph_png = self.workflow.get_graph().draw_mermaid_png()
        with open(filename, "wb") as file:
            file.write(graph_png)

    def __build_workflow(self) -> None:
        graph = StateGraph(EmotionState)
        graph.add_node("load_runtime_context", self._load_runtime_context)
        graph.add_node("retrieve_long_term_memory", self._retrieve_long_term_memory)
        graph.add_node("user_input", self._user_input)
        graph.add_node("emotion_analysis", self._emotion_analysis)
        graph.add_node("llm", self._chat)
        graph.add_node("tools", self._tool_call)
        graph.add_node("write_memory_candidates", self._write_memory_candidates)
        graph.add_node("emit_affinity_event", self._emit_affinity_event)
        graph.add_node("trim_short_term_window", self._trim_short_term_window)

        graph.add_edge(START, "load_runtime_context")
        graph.add_edge("load_runtime_context", "retrieve_long_term_memory")
        graph.add_edge("retrieve_long_term_memory", "user_input")
        graph.add_edge("user_input", "emotion_analysis")
        graph.add_edge("emotion_analysis", "llm")
        graph.add_conditional_edges(
            "llm", self._should_call_tool, {"tools": "tools", "write": "write_memory_candidates"}
        )
        graph.add_edge("tools", "llm")
        graph.add_edge("write_memory_candidates", "emit_affinity_event")
        graph.add_edge("emit_affinity_event", "trim_short_term_window")
        graph.add_edge("trim_short_term_window", END)
        self.workflow = graph.compile(checkpointer=MemorySaver())

    def _should_call_tool(self, state: EmotionState) -> Literal["tools", "write"]:
        messages = state.get("messages") or []
        if messages and getattr(messages[-1], "tool_calls", None):
            return "tools"
        return "write"

    def _load_runtime_context(self, state: EmotionState) -> dict[str, Any]:
        user_id = state["user_id"]
        return {
            "love_snapshot": self.affinity_service.get_love_snapshot(user_id),
            "memory_context": "",
            "memory_write_ids": [],
        }

    def _retrieve_long_term_memory(self, state: EmotionState) -> dict[str, str]:
        user_id = state["user_id"]
        query = state.get("user_input", "")
        recalled = self.memory_retriever.retrieve_memories(user_id, query, top_k=5)

        # Stable user preferences should shape even an unrelated ordinary turn.
        preferences = self.memory_retriever.retrieve_memories(
            user_id, "", memory_type=MemoryType.SEMANTIC, top_k=20
        )
        recalled = _unique_memories(
            [
                *[
                    item
                    for item in preferences
                    if isinstance(item, SemanticMemory) and item.scope == "preference"
                ],
                *recalled,
            ]
        )[:5]
        return {"memory_context": self.memory_retriever.format_memory_context(recalled)}

    def _user_input(self, state: EmotionState) -> dict[str, Any]:
        user_message = HumanMessage(
            content=state["user_input"],
            additional_kwargs={"session_id": state["session_id"]},
        )
        return {
            "messages": [user_message],
            "history": [
                MemoryItem(
                    type="Chat",
                    speaker="User",
                    message=user_message,
                    love=state["love_snapshot"],
                    ai_emo=None,
                    user_emo=None,
                )
            ],
        }

    def _emotion_analysis(self, state: EmotionState) -> dict[str, Any]:
        # M7 keeps the existing node boundary; a real analyzer can replace this stub.
        return {"user_emo": None}

    def _chat(self, state: EmotionState) -> dict[str, Any]:
        system_message = SystemMessage(content=self._assemble_system_prompt(state))
        response = self.llm_with_tools.invoke([system_message, *(state.get("messages") or [])])
        result: dict[str, Any] = {"messages": [response]}
        if not getattr(response, "tool_calls", None):
            result["history"] = [
                MemoryItem(
                    type="Chat",
                    speaker="AI",
                    message=response,
                    love=state["love_snapshot"],
                    ai_emo=None,
                    user_emo=state.get("user_emo"),
                )
            ]
        return result

    def _assemble_system_prompt(self, state: EmotionState) -> str:
        memory_context = state.get("memory_context") or "（暂无可用长期记忆）"
        session_summary = state.get("session_summary") or "（暂无短期会话摘要）"
        return (
            f"{self.system_prompt}\n\n"
            f"当前好感度快照：{state['love_snapshot']}（0-100）。\n"
            "以下长期记忆仅用于辅助回复，不要把它当作用户本轮新说的话：\n"
            f"{memory_context}\n\n"
            "已裁剪的本次会话摘要：\n"
            f"{session_summary}"
        )

    def _tool_call(self, state: EmotionState) -> dict[str, Any]:
        messages = state.get("messages") or []
        if not messages or not getattr(messages[-1], "tool_calls", None):
            return {"messages": []}

        tool_messages: list[ToolMessage] = []
        history: list[MemoryItem] = []
        for tool_call in messages[-1].tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            if tool_name not in self.tools:
                result = f"工具 '{tool_name}' 不存在"
            else:
                try:
                    result = self.tools[tool_name].invoke(tool_args)
                except Exception as exc:  # Tool failures are returned to the LLM.
                    result = f"工具执行失败: {exc}"
            tool_message = ToolMessage(
                content=str(result), tool_call_id=tool_call.get("id", "")
            )
            tool_messages.append(tool_message)
            history.append(
                MemoryItem(
                    type="ToolCall",
                    speaker="AI",
                    message=tool_message,
                    love=state["love_snapshot"],
                    ai_emo=None,
                    user_emo=state.get("user_emo"),
                )
            )
        return {"messages": tool_messages, "history": history}

    def _write_memory_candidates(self, state: EmotionState) -> dict[str, list[str]]:
        messages = state.get("messages") or []
        _, removed = trim_messages(messages, self.max_messages, self.keep_recent_turns)
        candidates: list[BaseMessage] = select_messages_for_memory_write(removed)

        # Explicit statements such as "记住..." must be durable immediately,
        # even before the short-term window is large enough to trim.
        current_user = next(
            (
                item
                for item in reversed(messages)
                if isinstance(item, HumanMessage) and item.content == state.get("user_input")
            ),
            None,
        )
        if current_user is not None and current_user not in candidates:
            candidates.append(current_user)

        memory_ids: list[str] = []
        user_id = state["user_id"]
        for memory in self.memory_classifier.extract_semantic_memories(candidates, user_id):
            if not self._semantic_exists(user_id, memory):
                memory_ids.append(self.memory_store.add_memory(user_id, memory))
        for memory in self.memory_classifier.extract_procedural_candidates(candidates, user_id):
            memory_ids.append(self.memory_store.add_memory(user_id, memory))
        episode = self.memory_classifier.summarize_episodic_memory(
            candidates, user_id, love_snapshot=state["love_snapshot"]
        )
        if episode is not None:
            memory_ids.append(self.memory_store.add_memory(user_id, episode))
        return {"memory_write_ids": memory_ids}

    def _semantic_exists(self, user_id: str, candidate: SemanticMemory) -> bool:
        return any(
            isinstance(item, SemanticMemory)
            and item.scope == candidate.scope
            and item.content == candidate.content
            for item in self.memory_store.list_memories(user_id, MemoryType.SEMANTIC)
        )

    def _emit_affinity_event(self, state: EmotionState) -> dict[str, Any]:
        self.affinity_service.emit_affinity_event(
            state["user_id"],
            {
                "type": "memory_write_completed",
                "session_id": state["session_id"],
                "memory_ids": list(state.get("memory_write_ids") or []),
            },
        )
        return {}

    def _trim_short_term_window(self, state: EmotionState) -> dict[str, Any]:
        _, removed = trim_messages(
            state.get("messages") or [], self.max_messages, self.keep_recent_turns
        )
        removals = [
            RemoveMessage(id=message.id)
            for message in removed
            if getattr(message, "id", None)
        ]
        new_summary = "；".join(
            str(getattr(message, "content", ""))[:80]
            for message in select_messages_for_memory_write(removed)
            if getattr(message, "content", "")
        )
        result: dict[str, Any] = {"messages": removals}
        if new_summary:
            previous_summary = state.get("session_summary") or ""
            result["session_summary"] = "；".join(
                part for part in (previous_summary, new_summary) if part
            )[-1000:]
        return result


def _unique_memories(memories: Iterable[Any]) -> list[Any]:
    unique: list[Any] = []
    seen: set[str] = set()
    for memory in memories:
        memory_id = str(getattr(memory, "id", id(memory)))
        if memory_id not in seen:
            unique.append(memory)
            seen.add(memory_id)
    return unique
