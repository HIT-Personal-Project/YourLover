'''
Descripttion: 工具模块初始化文件，自动发现并注册所有工具
version: 1.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:29:16
LastEditors: HongJin
LastEditTime: 2026-06-25 14:30:47
'''
from .BaseTool import (
    BaseTool,
    ToolRegistry,
    ToolConfig,
    register_tool,
    discover_tools,
    tool,
)

_discovered_tools = discover_tools()

__all__ = [
    "BaseTool",
    "ToolRegistry",
    "ToolConfig",
    "register_tool",
    "discover_tools",
    "tool",
]
