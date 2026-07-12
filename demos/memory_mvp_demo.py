"""M8 end-to-end demo for durable memory across chat sessions.

Run from the repository root with::

    conda run -n chatbot_py310 python demos/memory_mvp_demo.py
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama

# Support the documented ``python demos/memory_mvp_demo.py`` invocation.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.agent.ChatAgent import ChatAgent
from app.config import Settings
from app.memory.retriever import MemoryRetriever
from app.memory.schema import SemanticMemory
from app.memory.store import FileMemoryStore


DEFAULT_MODEL = "qwen3:8b"
DEFAULT_USER_ID = "memory-mvp-demo-user"
DEFAULT_MEMORY_DIR = REPOSITORY_ROOT / "data" / "memory" / "users"


@dataclass(frozen=True)
class MemoryDemoResult:
    """Observable evidence produced by the two-session demo."""

    memory_file: Path
    first_response: str
    second_response: str
    memory_context: str
    semantic_memories: tuple[str, ...]


def run_memory_mvp_demo(
    llm: Any,
    memory_dir: str | Path = DEFAULT_MEMORY_DIR,
    user_id: str = DEFAULT_USER_ID,
) -> MemoryDemoResult:
    """Write a preference in one session and recall it in a fresh session.

    The second ``ChatAgent`` and ``FileMemoryStore`` are deliberately recreated.
    This makes the demo verify durable JSON memory rather than LangGraph's
    in-process short-term checkpointer.
    """

    memory_dir = Path(memory_dir)
    first_store = FileMemoryStore(memory_dir)
    first_agent = _build_agent(llm, first_store, thread_id="memory-demo-session-1")
    first_state = first_agent.invoke(
        {
            "user_input": "记住我喜欢回答短一点",
            "user_id": user_id,
            "session_id": "memory-demo-session-1",
        }
    )

    # Simulate a new process/session by rebuilding all memory-facing services.
    second_store = FileMemoryStore(memory_dir)
    second_agent = _build_agent(llm, second_store, thread_id="memory-demo-session-2")
    second_state = second_agent.invoke(
        {
            "user_input": "我今天有点累，给我一句建议。",
            "user_id": user_id,
            "session_id": "memory-demo-session-2",
        }
    )

    semantic_memories = tuple(
        memory.content
        for memory in second_store.list_memories(user_id, "semantic")
        if isinstance(memory, SemanticMemory)
    )
    memory_context = str(second_state.get("memory_context") or "")
    if not semantic_memories:
        raise RuntimeError("M8 demo failed: session 1 did not persist semantic memory")
    if "简短回答" not in memory_context:
        raise RuntimeError("M8 demo failed: session 2 did not recall the stored preference")

    return MemoryDemoResult(
        memory_file=memory_dir / f"{user_id}.json",
        first_response=_last_message_content(first_state),
        second_response=_last_message_content(second_state),
        memory_context=memory_context,
        semantic_memories=semantic_memories,
    )


def _build_agent(llm: Any, store: FileMemoryStore, thread_id: str) -> ChatAgent:
    return ChatAgent(
        llm,
        Settings(),
        {"configurable": {"thread_id": thread_id}},
        memory_store=store,
        memory_retriever=MemoryRetriever(store),
    )


def _last_message_content(state: dict[str, Any]) -> str:
    messages = state.get("messages") or []
    return str(getattr(messages[-1], "content", "")) if messages else ""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Demonstrate persistent long-term memory across two ChatAgent sessions."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama chat model name")
    parser.add_argument(
        "--memory-dir",
        type=Path,
        default=DEFAULT_MEMORY_DIR,
        help="Directory containing per-user memory JSON files",
    )
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    print(f"使用 Ollama 模型：{args.model}")
    result = run_memory_mvp_demo(
        ChatOllama(model=args.model, temperature=0),
        memory_dir=args.memory_dir,
        user_id=args.user_id,
    )
    print(f"会话 1 回复：{result.first_response}")
    print(f"长期记忆文件：{result.memory_file}")
    print("会话 2 召回上下文：")
    print(result.memory_context)
    print(f"会话 2 回复：{result.second_response}")
    print("M8 验收通过：已在新 session 中召回持久化偏好。")


if __name__ == "__main__":
    main()
