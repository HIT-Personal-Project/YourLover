"""
使用langchain提供的agent接口，不建议这样做

"""

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver

llm = ChatOllama(model="qwen2.5:3b")

memory_saver = MemorySaver()

config = {
    "configurable": {
        "thread_id": "XIV0018579"
    }
}


@tool
def HIT_score(name: str, age: str) -> str:
    """计算HIT值，根据姓名和年龄计算HIT值"""
    HIT_cal = int(age) * 0.04 * len(name)
    return f"{name}的HIT值是{HIT_cal}"

agent = create_agent(
    model=llm,
    tools=[HIT_score],
    checkpointer=None,
    system_prompt="你是一个用户助手，按照用户的要求回答问题，并思考是否需要调用工具。"
)

result = agent.invoke(
    {"messages": [HumanMessage(content="我叫孙笑川，我今年40岁了，请问我的HIT值是多少？")]}
   )

print(result["messages"][-1].content)


graph_png = agent.get_graph().draw_mermaid_png()
with open("fast_hello_graph.png", "wb") as f:
    f.write(graph_png)