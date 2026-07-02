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
        memory_loaded: 是否已加载记忆（用于路由判断）
    """

    messages: Annotated[list, add_messages]
    history: Annotated[List[MemoryItem], operator.add]
    love: Annotated[int, operator.add]
    user_input: str
    memory_loaded: bool


def history_to_messages(history: List[MemoryItem]) -> List[BaseMessage]:
    """从history构造messages列表，用于LLM调用"""
    messages = []
    for item in history:
        if item.type == "Chat":
            if item.speaker == "User":
                messages.append(HumanMessage(content=item.text))
            elif item.speaker == "AI":
                messages.append(AIMessage(content=item.text))
            elif item.speaker == "System":
                messages.append(SystemMessage(content=item.text))
    return messages


def create_emotion_graph(llm: BaseChatModel, system_prompt: str = None) -> StateGraph:
    """
    创建情感陪伴Agent的LangGraph工作流

    Args:
        llm: 语言模型实例
        system_prompt: 系统提示词

    Returns:
        StateGraph: 配置好的工作流实例
    """
    if system_prompt is None:
        system_prompt = """你是一个温柔、善解人意的情感陪伴助手。请用温暖、关怀的语言回应用户。
        注意用户的情感状态，根据用户的情绪给予适当的安慰和鼓励。"""

    def chat_node(state: EmotionState) -> dict:
        """聊天节点：调用LLM生成回复，将完整对话写入history"""
        system_message = SystemMessage(content=system_prompt)

        history_messages = history_to_messages(state["history"])

        current_user_message = HumanMessage(content=state["user_input"])
        full_messages = [system_message] + history_messages + [current_user_message]

        response = llm.invoke(full_messages)

        user_memory = MemoryItem(
            type="Chat",
            speaker="User",
            text=state["user_input"],
            love=state["love"]+1,
            ai_emo=None,
            user_emo=None
        )

        ai_memory = MemoryItem(
            type="Chat",
            speaker="AI",
            text=response.content,
            love=state["love"]+1,
            ai_emo=None,
            user_emo=None
        )

        return {
            "messages": [response],
            "history": [user_memory, ai_memory],
            "love": 1
        }

    def process_input_node(state: EmotionState) -> dict:
        """处理输入节点：仅将用户输入转换为消息格式，不写入history"""
        user_message = HumanMessage(content=state["user_input"])

        return {
            "messages": [user_message]
        }

    def should_continue(state: EmotionState) -> str:
        """条件边：决定是否继续（当前简化为直接结束）"""
        return END

    graph = StateGraph(EmotionState)

    graph.add_node("process_input", process_input_node)
    graph.add_node("chat", chat_node)

    graph.add_edge(START, "process_input")
    graph.add_edge("process_input", "chat")
    graph.add_conditional_edges("chat", should_continue)

    checkpointer = InMemorySaver()

    return graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    """
    情感陪伴Agent示例

    这个示例展示了如何使用EmotionState和MemoryItem在LangGraph中构建情感陪伴Agent。
    """
    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(model="qwen3-vl:4b", temperature=0.8)
    except ImportError:
        print("未安装langchain_ollama，请安装后运行：pip install langchain-ollama")
        exit(1)

    graph = create_emotion_graph(llm)

    print("🎭 情感陪伴Agent已启动")
    print("------------------------")

    config = {"configurable": {"thread_id": "user_001"}}

    test_conversations = [
        "今天工作好累啊，感觉压力很大",
        "谢谢你的安慰，心情好多了",
        "你真好，我越来越喜欢你了"
    ]

    for user_input in test_conversations:
        print(f"\n👤 用户: {user_input}")

        state = graph.invoke(
            {"user_input": user_input},
            config=config
        )

        last_memory = state["history"][-1]
        print(f"🤖 AI: {last_memory.text}")
        print(f"💖 当前好感度: {state['love']}")
        print(f"📝 记忆总数: {len(state['history'])}")
