'''
Descripttion: 对话 Agent 模块，负责与 LLM 交互并执行 ReAct 工具调用
version: 2.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:23:13
LastEditors: HongJin
LastEditTime: 2026-06-25 14:38:34
'''
import json
import re
from typing import Any, Dict, List, Optional
from Langchain_ollama import ChatOllama
from tools.BaseTool import ToolRegistry, BaseTool


REACT_SYSTEM_PROMPT = """你是一个具备工具调用能力的智能助手。你可以调用以下工具来回答用户的问题：

{tools_description}

请严格按照以下 JSON 格式之一进行回复：

1. 需要调用工具时：
{{"action": "tool_name", "params": {{"param1": "value1", "param2": "value2"}}, "thought": "你的思考过程"}}

2. 直接回答用户时（无需工具）：
{{"action": "final_answer", "answer": "你的最终回答"}}

注意：
- params 的键名必须与工具定义中的参数名完全一致
- 参数值都是字符串或数字，不要传对象
- 如果一次工具调用无法完成任务，可以基于上一次的观察结果继续调用
"""


class ChatAgent:
    """
    对话 Agent，实现 ReAct 循环：
    1. 把工具列表注入 system prompt
    2. 让 LLM 决策（调用工具或最终回答）
    3. 解析 LLM 输出，调用工具
    4. 把工具结果反馈给 LLM
    5. 重复直到 LLM 给出 final_answer 或达到最大迭代次数

    使用方式:
        agent = ChatAgent(config)
        answer = agent.chat("帮我查一下北京天气")

        # 手动执行工具
        result = agent.execute_tool("web_search", query="...")
    """
    def __init__(self, config):
        self.LLM = config['LLM']
        self.tools = ToolRegistry.list_tools()
        self.max_iterations = config.get("max_iterations", 5)

    def _build_tools_description(self) -> str:
        """
        将工具列表格式化为 LLM 可读的文本描述

        Returns:
            str: 工具描述文本
        """
        descriptions = []
        for tool in self.tools:
            tool_json = json.dumps(tool, ensure_ascii=False, indent=2, default=str)
            descriptions.append(f"```json\n{tool_json}\n```")
        return "\n\n".join(descriptions)

    def _parse_llm_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 输出中解析出 JSON 决策

        支持从 markdown 代码块中提取 JSON，例如：
            ```json
            {"action": "web_search", ...}
            ```

        Args:
            content: LLM 输出的文本

        Returns:
            Optional[Dict[str, Any]]: 解析出的 JSON 字典，解析失败返回 None
        """
        content = content.strip()

        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return None

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def chat(self, user_input: str, history: List[Dict[str, str]] = None) -> str:
        """
        ReAct 决策循环：与 LLM 多轮交互直到得到最终答案

        Args:
            user_input: 用户输入
            history: 历史对话（可选），格式为 [{"role": "user|assistant", "content": "..."}]

        Returns:
            str: 最终回答
        """
        if history is None:
            history = []

        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT.format(
                tools_description=self._build_tools_description()
            )},
            *history,
            {"role": "user", "content": user_input},
        ]

        for _ in range(self.max_iterations):
            response = self.LLM.chat_completion(
                messages=messages,
                model=self.LLM.model,
                temperature=self.LLM.temperature,
                max_tokens=self.LLM.max_tokens,
            )
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            decision = self._parse_llm_response(content)

            if decision is None:
                return content

            action = decision.get("action")

            if action == "final_answer":
                return decision.get("answer", content)

            tool_name = action
            params = decision.get("params", {})

            try:
                result = ToolRegistry.execute_tool(tool_name, **params)
                observation = f"工具 {tool_name} 执行结果：\n{result}"
            except Exception as e:
                observation = f"工具 {tool_name} 执行失败：{e}"

            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": observation})

        return "达到最大迭代次数，任务未完成"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有可用工具列表

        Returns:
            List[Dict[str, Any]]: 工具信息字典列表
        """
        return ToolRegistry.list_tools()

    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        执行指定工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具执行所需的参数

        Returns:
            Any: 工具执行结果
        """
        return ToolRegistry.execute_tool(tool_name, **kwargs)

    def refresh_tools(self) -> None:
        """
        刷新工具列表
        """
        self.tools = ToolRegistry.list_tools()

    def _model_initial(self):
        """
        初始化大模型，包括加载记忆，情感等
        """
        pass


if __name__ == "__main__":
    print(ToolRegistry.list_tools())
