from agent.ChatAgent import ChatAgent
from config import settings, Settings

from memory.EmotionMemory import EmotionState, history_to_messages
from memory.MemoryItem import MemoryItem

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

    session = {
        "configurable": {"thread_id": "czw197"}
    }

    agent = ChatAgent(llm, settings, session)

    agent.save_graph_figure("ChatAgent.png")

    print("🎭 情感陪伴Agent已启动")
    print("------------------------")

    test_conversations = [
        "今天工作好累啊，感觉压力很大",
        "谢谢你的安慰，心情好多了",
        "你真好，我越来越喜欢你了"
    ]

    for user_input in test_conversations:
        print(f"\n👤 用户: {user_input}")

        state = agent.invoke(
            {"user_input": user_input},
            session=session
        )

        last_memory = state["history"][-1]
        print(f"🤖 AI: {last_memory.text}")
        print(f"💖 当前好感度: {state['love']}")
        print(f"📝 记忆总数: {len(state['history'])}")

    print("------------------------")
    print("🎭 情感陪伴Agent已关闭")


    print(history_to_messages(state["history"]))

    print("------------------------")

    print(state["messages"])
    