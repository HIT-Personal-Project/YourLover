from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, RemoveMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langgraph.prebuilt import ToolNode, tools_condition

from typing import Literal
import os
import tempfile
from PIL import Image as PILImage
from IPython.display import Image, display

@tool(description="用于请求人工辅助")
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    info = input("请输入·人工服务")
    return info

tools = [human_assistance]

tool_node= ToolNode(tools)

llm = ChatOllama(model="qwen2.5:3b")

llm_with_tools = llm.bind_tools(tools)

config= {
    "configurable": {
        "thread_id": "XIV0018579"
    }
}

workflow = StateGraph(MessagesState)


def chat(state: MessagesState) -> dict:
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    assert len(response.tool_calls) <= 1
    return {"messages": [response]}



workflow.add_node("chatbot", chat)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "chatbot")
workflow.add_conditional_edges("chatbot", tools_condition)
workflow.add_edge("tools", "chatbot")

app = workflow.compile(checkpointer=MemorySaver())

png_bytes = app.get_graph().draw_mermaid_png()
try:
    get_ipython()
    display(Image(png_bytes))
except NameError:
    try:
        img = PILImage.open(png_bytes)
        img.show()
    except Exception:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(png_bytes.getvalue())
            temp_path = f.name
        os.startfile(temp_path)

def stream_graph_updates(user_input: str):
    for event in app.stream({"messages": [HumanMessage(user_input)]}, config=config,stream_mode="values"):
        event["messages"][-1].pretty_print()



while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break


