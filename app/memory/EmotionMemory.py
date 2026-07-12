from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.memory.MemoryItem import MemoryItem


class EmotionState(TypedDict, total=False):
    """Runtime state shared by the ChatAgent LangGraph nodes."""

    messages: Annotated[list[BaseMessage], add_messages]
    history: Annotated[list[MemoryItem], operator.add]
    user_input: str
    user_id: str
    session_id: str
    memory_context: str
    session_summary: str
    love_snapshot: int
    user_emo: Any
    memory_write_ids: list[str]


def history_to_messages(history: list[MemoryItem]) -> list[BaseMessage]:
    """Build LangChain messages from the compatibility history view."""

    return [item.message for item in history]
