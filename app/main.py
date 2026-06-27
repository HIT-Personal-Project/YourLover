# ========================================================================
# 方式1: 直接调用 discover_and_wrap_tools() 获取 tool_map
#   注意: 直接运行脚本时 __name__ 为 __main__，无法自动推断包名，需显式传入
# ========================================================================
from tools import tool_map

# ========================================================================
# 方式2: 从 tools 包的 __init__.py 导入（推荐，包加载时已自动扫描）
#   from tools import tool_map
#   此方式无需显式传包名，因为 __init__.py 中调用时能正确推断
# ========================================================================

# --- 查看 tool_map 中的工具 ---
print("\n🧰 当前已注册的工具:")
for name, lc_tool_obj in tool_map.items():
    print(f"   - {name}: {lc_tool_obj.description[:30]}...")

print(tool_map)

# --- 将工具 bind 给 LLM ---
# llm_with_tools = llm.bind_tools(list(tool_map.values()))
# response = llm_with_tools.invoke("帮我读一下 config.yaml")

# --- 单独调用某个工具 ---
# result = tool_map["file_manager"].invoke({"action": "read", "file_path": "config.yaml"})
# print(result)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

llm = ChatOllama(model="qwen3-vl:4b")

# bind 工具到 LLM
llm_with_tools = llm.bind_tools(list(tool_map.values()))

print("\n" + "=" * 60)
print("🔄 开始模拟 ReAct 链")
print("=" * 60)

# 测试用例
test_cases = [
    "帮我计算一下 123 + 456 等于多少",
    "帮我计算'3+5+8+10/2'等于多少",
]

# 最大 ReAct 轮数，防止死循环
MAX_ITERATIONS = 5

for case in test_cases:
    print(f"\n{'='*60}")
    print(f"👤 用户: {case}")
    print(f"{'='*60}")

    # 消息历史，初始只有用户输入
    messages = [HumanMessage(content=case)]

    for i in range(MAX_ITERATIONS):
        # 调用 LLM（流式输出）
        print(f"\n--- 第 {i+1} 轮 ---")
        print("🤖: ", end="", flush=True)

        # 流式调用 LLM
        collected_chunks = []
        for chunk in llm_with_tools.stream(messages):
            collected_chunks.append(chunk)
            # 如果有文本内容，流式打印
            if chunk.content:
                print(chunk.content, end="", flush=True)

        # 合并流式 chunk 为完整 response
        # 第一个 chunk 包含完整信息，后续 chunk 是增量
        full_response = collected_chunks[0]
        for chunk in collected_chunks[1:]:
            full_response = full_response + chunk

        print()  # 换行

        # 将 AI 回复加入消息历史
        messages.append(full_response)

        # 检查是否有工具调用
        if not full_response.tool_calls:
            # 没有工具调用，说明模型已经给出最终回答
            print("✅ 模型给出最终回答，ReAct 结束")
            break

        # 执行所有工具调用，将结果返回给模型
        for tc in full_response.tool_calls:
            print("---------go to use tool---------")
            tool_name = tc["name"]
            tool_args = tc["args"]
            print(f"\n⚙️  调用工具: {tool_name}")
            print(f"   参数: {tool_args}")

            # 执行工具
            tool_result = tool_map[tool_name].invoke(tool_args)
            print(f"   结果: {tool_result}")

            # 将工具执行结果作为 ToolMessage 加入消息历史，供模型下一轮思考
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))
    else:
        print("\n⚠️ 已达到最大轮数限制，强制结束")