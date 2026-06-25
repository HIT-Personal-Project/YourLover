'''
Descripttion: Agent ReAct 链模拟测试
version: 1.0.0
Author: HongJin
Date: 2026-06-25
'''
import json
from tools.BaseTool import ToolRegistry, BaseTool, register_tool


@register_tool
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


def simulate_react_chain(user_input: str):
    """
    模拟 Agent 的 ReAct 决策链

    流程:
    1. LLM 根据用户输入决定调用哪个工具（这里简化为关键词匹配）
    2. 解析工具名和参数
    3. 执行工具
    4. 输出完整流程
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

    # 执行工具
    print(f"\n⚙️  执行工具: {tool_name}")
    print(f"   参数: {params}")
    try:
        result = ToolRegistry.execute_tool(tool_name, **params)
        print(f"   结果: {result}")
    except Exception as e:
        result = f"执行失败: {e}"
        print(f"   错误: {result}")

    print(f"\n📝 最终回答: 根据【{tool_name}】的执行结果，答案是: {result}")
    print("=" * 60)


if __name__ == "__main__":
    print("\n🧰 当前已注册的工具:")
    tools = ToolRegistry.list_tools()
    for t in tools:
        print(f"   - {t['name']}: {t['description'][:30]}...")

    print("\n" + "=" * 60)
    print("🔄 开始模拟 ReAct 链")
    print("=" * 60)

    # 测试用例
    test_cases = [
        "帮我计算一下 123 + 456 等于多少",
        "搜索一下今天北京的天气",
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n📌 测试用例 {i}/{len(test_cases)}")
        simulate_react_chain(case)

    print("\n✅ 测试完成")
