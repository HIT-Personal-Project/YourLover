"""
简单尝试做了好感度系统的聊天机器人，默认每次对话后好感度+1

"""



from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, RemoveMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages

from typing import Literal, Annotated
from typing_extensions import TypedDict
from IPython.display import Image, display
import operator


class LoveState(TypedDict):
    messages: Annotated[list, add_messages]
    love: Annotated[int, operator.add]
    name: str
    birthday: str

llm = ChatOllama(model="qwen2.5:3b")

config = {
    "configurable": {
        "thread_id": "XIV0018579"
    }
}

def chat(state: LoveState) -> dict:
    messages = state["messages"]
    love_value = state.get("love", 0)
    love_msg = SystemMessage(content=f"你是一个情感聊天伴侣机器人，请模仿可爱活泼的小女生进行对话，并根据输入提供的好感度决定语气和内容。当前用户对你的好感度（爱意值）为：{love_value}（0-100分）。请根据这个数值决定你的语气和内容：值越高，语气越亲密、可爱、热情；值越低，语气越礼貌、冷淡。")
    response = llm.invoke([love_msg] + messages)
    return {"messages": [response], "love": 1}


workflow = StateGraph(LoveState)
workflow.add_node("chatbot", chat)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)
app = workflow.compile(checkpointer=MemorySaver())




first_call = True

def stream_graph_updates(user_input: str) ->dict:
    global first_call
    input_dict = {"messages": [HumanMessage(user_input)]}
    if first_call:
        input_dict["love"] = 77
        first_call = False
    for event in app.stream(input_dict, config=config, stream_mode="values"):
        event["messages"][-1].pretty_print()
        if "love" in event:
            print(f"❤️ 当前爱意值: {event['love']}")
    

        


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


# # 获取历史状态
# for state in app.get_state_history(config=config):
#     print(state["messages"])
