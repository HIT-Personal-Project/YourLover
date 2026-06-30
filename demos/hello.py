"""
hello world级别的demo
"""

from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END,StateGraph,MessagesState
from langgraph.prebuilt import ToolNode
from typing import Annotated

@tool(description="用于查询天气")
def search(query: Annotated[str, "查询的天气信息"])  -> str:
    if "上海" in query or "shanghai" in query.lower():
        return "上海现在是25摄氏度，天气晴朗"
    else:
        return "天气35摄氏度"


@tool(description="HIT计算器，用于计算HIT值")
def HIT_calculater(
        name:str,
        age:str
) -> str:
    """
    Args:
        name (str): 姓名
        age (str): 年龄
    Returns:
        str: 计算结果
    """
    return f"{name}的年龄是{age}"


tools = [search]

tool_node = ToolNode(tools)
model = ChatOllama(model="qwen3-vl:4b").bind_tools(tools)

#React判断是否继续调用工具 路由函数
def should_continue(state: MessagesState) -> Literal["tools", "memory",END]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    
    if len(messages) > 5:
        return "memory"
    
    return END


# 在节点中实现压缩逻辑
# 压缩消息，只保留最近 5 条消息 + 系统提示词
def compress_messages(state: MessagesState) -> dict:
    messages = state["messages"]
    
    # 例如：只保留最近 5 条消息 + 系统提示词
    if len(messages) > 6:
        # 移除索引 1 到 len-5 之间的消息（保留 system prompt 和最近 5 条）
        remove_msgs = [RemoveMessage(id=m.id) for m in messages[1:-5]]
        return {"messages": remove_msgs}
    
    return {}




# 调用模型
def call_model(state:MessagesState)->dict:
    messages = state['messages']
    response = model.invoke(messages)
    return {'messages':[response]}

# 工作流的两个节点
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("memory", compress_messages)

# 入口节点
workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue)

# 调用工具节点后一定会返回到agent节点
workflow.add_edge("tools", "agent")
workflow.add_edge("memory", END)

checkpointer = MemorySaver() #持久化状态



# 编译图
app = workflow.compile(checkpointer=checkpointer)

final_state = app.invoke({"messages":[HumanMessage(content="我将会逐条发送给你消息，请记住消息即可。")]}                         ,
                         config={"thread_id": "123"}
                         )

result = final_state['messages'][-1].content
print(result)



for i in range(6):
    final_staet = app.invoke({"messages":[HumanMessage(content=f"这是第{i}条消息，发送给你的内容是：IDS--{i}，请记住消息。")]}                        ,
                             config={"thread_id": "123"}
                             )
    result = final_staet['messages'][-1].content
    print(result)

final_state = app.invoke({"messages":[HumanMessage(content="请告诉我你所知道的所有历史消息")]}                         ,
                         config={"thread_id": "123"}
                         )

result = final_state['messages'][-1].content
print(result)


print("Agent所获取的历史消息如下：")

for message in final_state['messages']:
    print(f"{message.id}: {message.content}")


graph_png = app.get_graph().draw_mermaid_png()
with open("hello_graph.png", "wb") as f:
    f.write(graph_png)