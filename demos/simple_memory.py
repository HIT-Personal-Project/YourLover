from langgraph.checkpoint.memory import MemorySaver, InMemorySaver

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from langgraph.prebuilt import create_react_agent


llm = ChatOllama(model="qwen2.5:3b")

memory_saver = InMemorySaver()

config = {
    "configurable": {
        "thread_id": "XIV0018579"
    }
}

agent = create_react_agent(
    model=llm,
    tools=[],
    prompt="你是一个智能助手，你可以回答用户的问题。",
    checkpointer=memory_saver
)

print(agent.invoke({"messages": [HumanMessage("我将会逐步发送一系列information给你，请你记住消息。")]}, config=config)["messages"][-1].content)

for i in range(5):
    print(agent.invoke({"messages": [HumanMessage(f"来自第{i}条information，内容为：IDS----{i}")]}, config=config)["messages"][-1].content)

print(agent.invoke({"messages": [HumanMessage("请告诉我全部的历史信息。")]}, config=config)["messages"][-1].content)


