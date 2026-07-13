"""Local M7 smoke demo. Run with: python -m app.main"""

from langchain_ollama import ChatOllama

from agent.ChatAgent import ChatAgent
from config import settings

from models.OllamaModels import get_ollama_llm

def main() -> None:
    # llm = ChatOllama(model="qwen3:8b", temperature=0.3)
    llm = get_ollama_llm(model_name=settings.CHAT_MODEL_NAME)
    agent = ChatAgent(
        llm,
        settings,
        {"configurable": {"thread_id": "m7-session-1", "user_id": "m7-demo-user"}},
    )

    print(f"M7 ChatAgent 已启动（Ollama {settings.CHAT_MODEL_NAME}）")
    turns = [
        ("m7-session-1", "记住我喜欢回答短一点"),
        ("m7-session-2", "请简单说一句今天的鼓励"),
        ("m7-session-2", "帮我调用一下rag工具，查询一下校园情感陪伴助手有什么功能？"),
    ]

    agent.save_graph_figure("Agent_memory.png")
    for session_id, text in turns:
        state = agent.invoke(
            {"user_input": text, "user_id": "m7-demo-user", "session_id": session_id}
        )
        print(f"\n用户 [{session_id}]: {text}")
        print(f"助手: {state['messages'][-1].content}")
        print(f"好感度快照: {state['love_snapshot']}")
        print(f"召回上下文: {state['memory_context'] or '（无）'}")

    for history in state["history"]:
        print(history)

if __name__ == "__main__":
    main()
