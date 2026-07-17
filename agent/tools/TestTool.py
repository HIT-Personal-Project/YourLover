'''
Descripttion: Agent ReAct 链模拟测试
version: 2.0.0
Author: HongJin
Date: 2026-06-25
'''
import json
from agent.tools.BaseTool import BaseTool, discover_and_wrap_tools

## 测试工具
class CalculatorTool(BaseTool):
    """
    计算器工具，用于执行数学运算
    """
    name = "calculator"
    description = "用于执行数学计算。当你需要计算表达式、统计数据或进行数值分析时使用此工具。"
    param_descriptions = {
        "expression": "数学表达式，必填，例如 '2 + 3 * 4' 或 '10 / 2 + 5'",
    }
    examples = [
        {
            "user_input": "帮我计算一下 123 加 456 等于多少",
            "model_params": {"expression": "123 + 456"},
            "return_value": "579",
        },
        {
            "user_input": "5 的平方是多少？",
            "model_params": {"expression": "5 ** 2"},
            "return_value": "25",
        },
    ]

    def _tool_call(self, expression: str) -> str:
        """
        执行数学表达式

        Args:
            expression: 数学表达式字符串

        Returns:
            str: 计算结果
        """
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return str(result)
        except Exception as e:
            return f"计算错误: {e}"


def simulate_react_chain(user_input: str, tool_map: dict):
    """
    模拟 Agent 的 ReAct 决策链

    流程:
    1. LLM 根据用户输入决定调用哪个工具（这里简化为关键词匹配）
    2. 解析工具名和参数
    3. 通过 langchain Tool 的 invoke 方法执行工具
    4. 输出完整流程

    Args:
        user_input: 用户输入
        tool_map: 工具名称 -> langchain Tool 对象的映射字典
    """
    print("=" * 60)
    print(f"用户输入: {user_input}")
    print("=" * 60)

    # 模拟 LLM 决策（关键词匹配）
    if "天气" in user_input or "搜索" in user_input:
        tool_name = "web_search"
        params = {"query": user_input.replace("搜索", "").replace("天气", "").strip()}
    elif "计算" in user_input or any(op in user_input for op in ["+", "-", "*", "/", "**"]):
        tool_name = "calculator"
        import re
        expr_match = re.search(r'[\d\+\-\*\/\.\s\*\*]+', user_input)
        params = {"expression": expr_match.group().strip()} if expr_match else {"expression": "0"}
    elif "读" in user_input or "文件" in user_input:
        tool_name = "file_manager"
        params = {"action": "read", "file_path": "config.yaml"}
    else:
        print("\n🤔 LLM 决定: 无需工具，直接回答\n")
        print(f"📝 最终回答: 我需要更多信息来回答您的问题。")
        return

    # 决策结果
    print(f"\n🤔 LLM 决策:")
    print(f"   思考: 用户需要【{tool_name}】来处理这个请求")
    print(f"   参数: {json.dumps(params, ensure_ascii=False)}")

    # 执行工具（通过 langchain Tool 的 invoke 方法）
    print(f"\n⚙️  执行工具: {tool_name}")
    print(f"   参数: {params}")
    try:
        lc_tool_obj = tool_map[tool_name]
        result = lc_tool_obj.invoke(params)
        print(f"   结果: {result}")
    except Exception as e:
        result = f"执行失败: {e}"
        print(f"   错误: {result}")

    print(f"\n📝 最终回答: 根据【{tool_name}】的执行结果，答案是: {result}")
    print("=" * 60)


if __name__ == "__main__":
    # ========================================================================
    # 方式1: 直接调用 discover_and_wrap_tools() 获取 tool_map
    #   注意: 直接运行脚本时 __name__ 为 __main__，无法自动推断包名，需显式传入
    # ========================================================================
    from agent.tools import tool_map

    # ========================================================================
    # 方式2: 从 tools 包的 __init__.py 导入（推荐，包加载时已自动扫描）
    #   from tools import tool_map
    #   此方式无需显式传包名，因为 __init__.py 中调用时能正确推断
    # ========================================================================

    # --- 查看 tool_map 中的工具 ---
    print("\n🧰 当前已注册的工具:")
    for name, lc_tool_obj in tool_map.items():
        print(f"   - {name}: {lc_tool_obj.description[:30]}...")

    # --- 将工具 bind 给 LLM ---
    # llm_with_tools = llm.bind_tools(list(tool_map.values()))
    # response = llm_with_tools.invoke("帮我读一下 config.yaml")

    # --- 单独调用某个工具 ---
    # result = tool_map["file_manager"].invoke({"action": "read", "file_path": "config.yaml"})
    # print(result)

    from langchain_ollama import ChatOllama

    llm = ChatOllama(model="qwen3-vl:4b")

    llm.bind_tools(tool_map)

    print("\n" + "=" * 60)
    print("🔄 开始模拟 ReAct 链")
    print("=" * 60)

    # 测试用例
    test_cases = [
        "帮我计算一下 123 + 456 等于多少",
        "搜索一下今天北京的天气",
    ]

    for case in test_cases:
        response = llm.invoke(case)
        print(response)
        if response.tool_calls:
            for tc in response.tool_calls:
                print(f"工具: {tc['name']}")
                print(f"参数: {tc['args']}")

                print(tool_map[tc['name']].invoke(tc['args']))
