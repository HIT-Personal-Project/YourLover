"""基于 LangGraph 的情感陪伴聊天 Agent，集成 M7 长期记忆能力。

该模块定义 ChatAgent，通过 LangGraph 编排一个多节点工作流，
在每一轮对话中完成：加载运行时上下文 -> 检索长期记忆 -> 注入用户输入 ->
情感分析（存根）-> LLM/工具调用 -> 写入长期记忆候选 -> 发射好感度事件 ->
裁剪短期窗口。

工作流节点通过 EmotionState 共享状态，使用 MemorySaver 作为 checkpointer
保留短期会话状态。
"""

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

from agent.affinity.service import AffinityService
from core.config import Settings
from agent.memory.classifier import MemoryClassifier
from agent.memory.EmotionMemory import EmotionState
from agent.memory.MemoryItem import MemoryItem
from agent.memory.retriever import MemoryRetriever
from agent.memory.schema import MemoryType, SemanticMemory
from agent.memory.session_store import SessionStore
from agent.memory.store import FileMemoryStore
from agent.memory.window import select_messages_for_memory_write, trim_messages
from agent.tools import tool_map


class ChatAgent:
    """情感陪伴 Agent：由 memory 模块各边界组合而成的 LangGraph 代理。

    核心职责：
        1. 组装记忆存储/检索器/分类器/好感度服务等依赖；
        2. 构建 LangGraph 工作流并暴露 invoke 入口；
        3. 在每轮对话中完成长期记忆的检索、写入与短期窗口裁剪。

    依赖注入：memory_store/memory_retriever/memory_classifier/affinity_service
    均可由调用方传入，便于测试与替换。
    """

    def __init__(
        self,
        llm: Any,
        config: Settings,
        session: dict[str, Any],
        *,
        memory_store: FileMemoryStore | None = None,
        memory_retriever: MemoryRetriever | None = None,
        memory_classifier: MemoryClassifier | None = None,
        session_store: SessionStore | None = None,
        affinity_service: AffinityService | None = None,
        max_messages: int = 20,
        keep_recent_turns: int = 6,
    ) -> None:
        """初始化 Agent 并构建工作流。

        参数：
            llm: LangChain LLM 实例（需支持 bind_tools）
            config: 全局配置（含 system prompt 等）
            session: 运行时会话配置（含 configurable 等）
            memory_store: 长期记忆存储，未提供则用默认 FileMemoryStore
            memory_retriever: 记忆检索器，未提供则基于 memory_store 创建
            memory_classifier: 记忆分类器，未提供则用默认 MemoryClassifier
            session_store: 短期 Session 存储，未提供则使用默认 SQLite 存储
            affinity_service: 好感度服务，未提供则用默认 AffinityService
            max_messages: 短期窗口消息上限，必须 >=1
            keep_recent_turns: 裁剪时保留的最近对话轮次数，必须 >=0
        """
        if max_messages < 1:
            raise ValueError("max_messages must be greater than or equal to 1")
        if keep_recent_turns < 0:
            raise ValueError("keep_recent_turns must be greater than or equal to 0")

        self.config = config
        self.session = session
        self.session_id = None
        self.llm = llm
        self.tools = tool_map
        self.system_prompt = config.TEST_SYSTEM_PROMPT
        self.memory_store = memory_store or FileMemoryStore()
        self.memory_retriever = memory_retriever or MemoryRetriever(self.memory_store)
        self.memory_classifier = memory_classifier or MemoryClassifier()
        # 测试传入临时长期存储时，把 Session 数据库也放入临时目录。
        self.session_store = session_store or (
            SessionStore(memory_store.root_dir / "sessions.sqlite3")
            if memory_store is not None
            else SessionStore()
        )
        self.affinity_service = affinity_service or AffinityService()
        self.max_messages = max_messages
        self.keep_recent_turns = keep_recent_turns
        # 若 LLM 支持 bind_tools 则绑定工具，否则直接使用原 LLM
        self.llm_with_tools = (
            self.llm.bind_tools(list(self.tools.values()))
            if hasattr(self.llm, "bind_tools")
            else self.llm
        )
        self.__build_workflow()

    def invoke(
        self, user_input: dict[str, Any], session: dict[str, Any] | None = None
    ) -> EmotionState:
        """执行一轮对话。

        参数：
            user_input: 用户输入负载，可含 user_id/session_id 与文本内容
            session: 可选的运行时会话配置，覆盖初始化时的 session

        user_id 标识长期记忆归属；session_id（或 LangGraph 的 thread_id）
        标识短期会话状态。两者缺省时分别回退到 "default-user"/"default-session"。
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
        """将工作流图导出为 PNG 图片，便于可视化调试。"""
        graph_png = self.workflow.get_graph().draw_mermaid_png()
        with open(filename, "wb") as file:
            file.write(graph_png)

    def __build_workflow(self) -> None:
        """构建 LangGraph 工作流。

        节点流转：
            START --(条件)--> session_id 切换时走加载链路，否则直达 user_input
            加载链路: load_runtime_context -> retrieve_long_term_memory
                      -> load_short_term_memory -> user_input
            公共链路: user_input -> emotion_analysis -> llm
                      -> (条件) tools 或 write_memory_candidates
            tools -> llm（工具执行后回到 LLM 继续生成）
            write_memory_candidates -> emit_affinity_event
                 -> trim_short_term_window -> save_short_term_memory -> END
        使用 MemorySaver 作为 checkpointer，按 thread_id 隔离不同会话。
        同一 session_id 的后续轮次由 checkpointer 恢复状态（含已加载的记忆上下文），
        因此跳过加载链路直达 user_input。
        """
        graph = StateGraph(EmotionState)
        graph.add_node("load_runtime_context", self._load_runtime_context)
        graph.add_node("retrieve_long_term_memory", self._retrieve_long_term_memory)
        graph.add_node("load_short_term_memory", self._load_short_term_memory)
        graph.add_node("user_input", self._user_input)
        graph.add_node("emotion_analysis", self._emotion_analysis)
        graph.add_node("llm", self._chat)
        graph.add_node("tools", self._tool_call)
        graph.add_node("write_memory_candidates", self._write_memory_candidates)
        graph.add_node("emit_affinity_event", self._emit_affinity_event)
        graph.add_node("trim_short_term_window", self._trim_short_term_window)
        graph.add_node("save_short_term_memory", self._save_short_term_memory)

        graph.add_conditional_edges(
            START,
            self._route_on_session,
            {"load": "load_runtime_context", "skip": "user_input"},
        )
        graph.add_edge("load_runtime_context", "retrieve_long_term_memory")
        graph.add_edge("retrieve_long_term_memory", "load_short_term_memory")
        graph.add_edge("load_short_term_memory", "user_input")
        graph.add_edge("user_input", "emotion_analysis")
        graph.add_edge("emotion_analysis", "llm")
        graph.add_conditional_edges(
            "llm", self._should_call_tool, {"tools": "tools", "write": "write_memory_candidates"}
        )
        graph.add_edge("tools", "llm")
        graph.add_edge("write_memory_candidates", "emit_affinity_event")
        graph.add_edge("emit_affinity_event", "trim_short_term_window")
        graph.add_edge("trim_short_term_window", "save_short_term_memory")
        graph.add_edge("save_short_term_memory", END)
        self.workflow = graph.compile(checkpointer=MemorySaver())

    def _route_on_session(self, state: EmotionState) -> Literal["load", "skip"]:
        """START 条件路由：判断本轮是否需要加载记忆。

        判断依据：self.session_id 是否等于当前 session_id。
            - 相等：记忆已为本会话加载过，跳过加载链路直达 user_input
              （同一 session_id 的后续轮次由 MemorySaver 恢复状态，含已加载的
              memory_context / love_snapshot 等，无需重复加载）。
            - 不等（含首次进入 self.session_id 为 None、session_id 切换）：走完整加载链路。
        """
        if self.session_id == state.get("session_id"):
            return "skip"
        return "load"

    def _should_call_tool(self, state: EmotionState) -> Literal["tools", "write"]:
        """条件路由：LLM 最后一条消息含 tool_calls 则进入工具节点，否则进入记忆写入。"""
        messages = state.get("messages") or []
        if messages and getattr(messages[-1], "tool_calls", None):
            return "tools"
        return "write"

    def _load_runtime_context(self, state: EmotionState) -> dict[str, Any]:
        """加载运行时上下文：取当前好感度快照，并初始化记忆上下文与写入 ID 列表。"""
        user_id = state["user_id"]
        return {
            "love_snapshot": self.affinity_service.get_love_snapshot(user_id),
            "memory_context": "",
            "memory_write_ids": [],
        }

    def _retrieve_long_term_memory(self, state: EmotionState) -> dict[str, str]:
        """检索长期记忆并格式化为上下文字符串。

        逻辑：
            1. 按当前 user_input 检索 top5 相关记忆；
            2. 额外检索用户偏好类语义记忆（scope=preference），保证稳定偏好
               即使与本轮主题无关也能影响回复；
            3. 合并去重后取前 5 条，格式化为 memory_context 注入 system prompt。
        """
        user_id = state["user_id"]
        query = state.get("user_input", "")
        recalled = self.memory_retriever.retrieve_memories(user_id, query, top_k=5)

        # 稳定的用户偏好应即使在无关的普通对话中也影响回复
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

    def _load_short_term_memory(self, state: EmotionState) -> dict[str, Any]:
        """加载短期记忆：恢复 Session 摘要和最近消息。

        逻辑：若 LangGraph 已恢复当前线程状态则不重复加载；否则从 SQLite
        读取最近消息，恢复为 messages 和 MemoryItem history。
        """
        user_id = state["user_id"]
        session_id = state["session_id"]
        self.session_id = session_id

        # 切回进程内已有的 LangGraph 线程时，checkpoint 已经包含短期状态。
        if state.get("messages") or state.get("session_summary"):
            return {}

        snapshot = self.session_store.load_session(
            user_id,
            session_id,
            recent_limit=self.max_messages,
        )
        if snapshot is None:
            self.session_store.create_session(user_id, session_id)
            return {}

        history = [record.item for record in snapshot.items]
        return {
            "messages": [item.message for item in history],
            "history": history,
            "session_summary": snapshot.session.summary,
        }
    
    def _save_short_term_memory(self, state: EmotionState) -> dict[str, Any]:
        """保存短期记忆：持久化本轮新增事件并同步 Session 摘要。

        逻辑：从 history 中找到本轮最后一条用户输入，只保存它及其后的
        AI/工具事件；消息 ID 缺失时用时间戳生成稳定事件 ID，避免重复写入。
        """
        user_id = state["user_id"]
        session_id = state["session_id"]
        history = list(state.get("history") or [])
        user_input = state.get("user_input", "")

        # 从后向前定位本轮用户事件，避免重复保存之前的 history。
        turn_start = next(
            (
                index
                for index in range(len(history) - 1, -1, -1)
                if history[index].speaker.lower() == "user"
                and getattr(history[index].message, "content", None) == user_input
            ),
            None,
        )
        turn_items = history[turn_start:] if turn_start is not None else []

        if turn_items:
            event_ids = [
                str(getattr(item.message, "id", None))
                if getattr(item.message, "id", None)
                else f"{session_id}:{item.speak_time!r}:{index}"
                for index, item in enumerate(turn_items)
            ]
            self.session_store.save_memory_items(
                user_id,
                session_id,
                turn_items,
                event_ids=event_ids,
            )
        else:
            self.session_store.create_session(user_id, session_id)

        session = self.session_store.get_session(user_id, session_id)
        summary = state.get("session_summary") or ""
        if session is not None and summary != session.summary:
            records = self.session_store.load_memory_item_records(user_id, session_id)
            retained_count = len(state.get("messages") or [])
            removed_count = max(0, len(records) - retained_count)
            summarized_through = session.summarized_through_sequence
            if removed_count:
                summarized_through = max(
                    summarized_through,
                    records[removed_count - 1].sequence_no,
                )
            self.session_store.update_session_summary(
                user_id,
                session_id,
                summary,
                summarized_through,
            )
        return {}


    def _user_input(self, state: EmotionState) -> dict[str, Any]:
        """把本轮用户输入包装为 HumanMessage，并写入 history 视图。"""
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
        """情感分析节点（M7 存根）：当前不做真实分析，保留节点边界供后续替换。"""
        # M7 keeps the existing node boundary; a real analyzer can replace this stub.
        return {"user_emo": None}

    def _chat(self, state: EmotionState) -> dict[str, Any]:
        """调用 LLM 生成回复。

        组装 system prompt（含好感度、长期记忆上下文、会话摘要）后连同
        当前消息列表调用 LLM。若 LLM 未发起工具调用，则把 AI 回复写入
        history 视图。
        """
        system_message = SystemMessage(content=self._assemble_system_prompt(state))
        response = self.llm_with_tools.invoke([system_message, *(state.get("messages") or [])])
        result: dict[str, Any] = {"messages": [response]}
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
        """组装 system prompt：基础提示 + 好感度 + 长期记忆上下文 + 会话摘要。

        明确提示 LLM：长期记忆仅供辅助回复，不应当作用户本轮新说的话。
        """
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
        """执行 LLM 发起的工具调用。

        遍历最后一条消息的 tool_calls，逐个调用对应工具：
            - 工具不存在时返回错误字符串；
            - 工具执行异常时把异常信息回传给 LLM（让 LLM 自行处理失败）。
        每个工具调用结果包装为 ToolMessage，并同步写入 history 视图。
        """
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
                except Exception as exc:  # 工具失败时把错误回传给 LLM
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
        """把本轮被裁剪的消息与当前用户输入写入长期记忆。

        逻辑：
            1. 对当前消息做裁剪，取出被移除的消息作为候选；
            2. 显式"记住..."类用户输入即使未被裁剪也要立即落地；
            3. 调用分类器提取语义记忆（去重）、程序性候选、情节摘要并持久化；
            4. 返回本轮写入的记忆 ID 列表。
        """
        messages = state.get("messages") or []
        _, removed = trim_messages(messages, self.max_messages, self.keep_recent_turns)
        candidates: list[BaseMessage] = select_messages_for_memory_write(removed)

        # 显式"记住..."类陈述必须立即持久化，即使短期窗口还未大到需要裁剪
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
        # 语义记忆：与已存在记忆按 (scope, content) 去重
        for memory in self.memory_classifier.extract_semantic_memories(candidates, user_id):
            if not self._semantic_exists(user_id, memory):
                memory_ids.append(self.memory_store.add_memory(user_id, memory))
        # 程序性候选：直接追加（默认需用户确认）
        for memory in self.memory_classifier.extract_procedural_candidates(candidates, user_id):
            memory_ids.append(self.memory_store.add_memory(user_id, memory))
        # 情节记忆：仅当构成完整"问题-行动-结果"时生成
        episode = self.memory_classifier.summarize_episodic_memory(
            candidates, user_id, love_snapshot=state["love_snapshot"]
        )
        if episode is not None:
            memory_ids.append(self.memory_store.add_memory(user_id, episode))
        return {"memory_write_ids": memory_ids}

    def _semantic_exists(self, user_id: str, candidate: SemanticMemory) -> bool:
        """判断用户已有的语义记忆中是否已存在相同 (scope, content) 的记忆，避免重复写入。"""
        return any(
            isinstance(item, SemanticMemory)
            and item.scope == candidate.scope
            and item.content == candidate.content
            for item in self.memory_store.list_memories(user_id, MemoryType.SEMANTIC)
        )

    def _emit_affinity_event(self, state: EmotionState) -> dict[str, Any]:
        """向好感度服务发射"记忆写入完成"事件，供后续好感度计算消费。"""
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
        """裁剪短期窗口并更新会话摘要。

        逻辑：
            1. 对当前消息做裁剪，生成 RemoveMessage 列表让 LangGraph 移除旧消息；
            2. 从被裁剪消息中提取可记忆内容，拼成新的会话摘要片段；
            3. 把新片段追加到既有 session_summary，并截断到 1000 字以内。
        """
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
    """按记忆 id 去重，保留首次出现的顺序。

    用于合并"偏好召回"与"相关召回"两路结果时避免重复。
    """
    unique: list[Any] = []
    seen: set[str] = set()
    for memory in memories:
        memory_id = str(getattr(memory, "id", id(memory)))
        if memory_id not in seen:
            unique.append(memory)
            seen.add(memory_id)
    return unique
