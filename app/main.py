"""Local M7 smoke demo. Run with: python -m app.main"""

from langchain_ollama import ChatOllama

from app.agent.ChatAgent import ChatAgent
from app.config import settings


def main() -> None:
    llm = ChatOllama(model="qwen3:8b", temperature=0.3)
    agent = ChatAgent(
        llm,
        settings,
        {"configurable": {"thread_id": "m7-session-1", "user_id": "m7-demo-user"}},
    )

    print("M7 ChatAgent 已启动（Ollama qwen3:8b）")
    turns = [
        ("m7-session-1", "记住我喜欢回答短一点"),
        ("m7-session-2", "请简单说一句今天的鼓励"),
    ]
    for session_id, text in turns:
        state = agent.invoke(
            {"user_input": text, "user_id": "m7-demo-user", "session_id": session_id}
        )
        print(f"\n用户 [{session_id}]: {text}")
        print(f"助手: {state['messages'][-1].content}")
        print(f"好感度快照: {state['love_snapshot']}")
        print(f"召回上下文: {state['memory_context'] or '（无）'}")


if __name__ == "__main__":
    main()
