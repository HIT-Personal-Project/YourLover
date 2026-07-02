from typing import Annotated, List, TypedDict, Callable, Any

import operator

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.language_models import BaseChatModel

from memory.MemoryItem import MemoryItem


class EmotionState(TypedDict):
    """
    情感状态, LangGraph状态对象
    history列表每条装的是MemoryItem对象，需要使用请调用管理器或者使用MemoryItem内部的方法

    Attributes:
        messages: 消息列表，包含用户和助手的消息（用于LLM调用）
        history: 记忆列表，包含用户和助手的对话记录（带元数据的完整记忆）
        love: 好感度，用于存储用户对助手的好感度，默认值为0
        user_input: 当前用户输入（用于临时存储）
    """

    messages: Annotated[list, add_messages]
    history: Annotated[List[MemoryItem], operator.add]
    love: Annotated[int, operator.add]
    user_input: str


def history_to_messages(history: List[MemoryItem]) -> List[BaseMessage]:
    """从history构造messages列表，用于LLM调用"""
    messages = []
    
    for item in history:
        messages.append(item.message)
    
    return messages

