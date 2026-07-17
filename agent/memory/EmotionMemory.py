"""情感陪伴 Agent 的运行时状态定义。

定义 EmotionState TypedDict，作为 LangGraph 各节点共享的状态容器；
并提供 history_to_messages 兼容函数，把历史 MemoryItem 视图还原为
LangChain 消息列表。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from agent.memory.MemoryItem import MemoryItem


class EmotionState(TypedDict, total=False):
    """ChatAgent LangGraph 各节点共享的运行时状态。

    字段：
        messages: 当前会话消息列表（使用 add_messages reducer，支持增量合并）
        history: 兼容历史视图的 MemoryItem 列表（使用 operator.add 合并）
        user_input: 本轮用户输入文本
        user_id: 用户唯一标识（用于长期记忆归属）
        session_id: 会话唯一标识（用于短期状态）
        memory_context: 检索到的长期记忆上下文字符串
        session_summary: 本次会话的裁剪摘要
        love_snapshot: 当前好感度快照（0-100）
        user_emo: 用户当前情感状态
        memory_write_ids: 本轮写入的长期记忆 ID 列表
    """

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
    """把兼容历史视图的 MemoryItem 列表还原为 LangChain 消息列表。

    用于在需要把 history 喂给 LLM 时进行转换。
    """
    return [item.message for item in history]
