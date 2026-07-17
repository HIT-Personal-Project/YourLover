'''
Descripttion: 工具模块初始化文件，自动发现所有工具并封装为 langchain @tool
version: 2.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:29:16
LastEditors: HongJin
LastEditTime: 2026-06-27 14:30:00
'''
from agent.tools.BaseTool import (
    BaseTool,
    discover_and_wrap_tools,
)

# 自动发现当前包下所有 BaseTool 子类，并封装为 langchain @tool 函数
# tool_map: Dict[str, langchain_core.tools.StructuredTool] — 键为工具名，值为 langchain Tool 对象
# 可通过 llm.bind_tools(list(tool_map.values())) 直接绑定给 LLM
tool_map = discover_and_wrap_tools()

__all__ = [
    "BaseTool",
    "discover_and_wrap_tools",
    "tool_map",
]
