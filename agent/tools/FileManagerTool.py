'''
Descripttion: 文件管理工具，用于读取和写入文件
version: 1.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 14:30:47
LastEditors: HongJin
LastEditTime: 2026-06-25 14:30:47
'''
from agent.tools.BaseTool import BaseTool
import os


class FileManagerTool(BaseTool):
    """
    文件管理工具，用于读取和写入文件

    使用方式:
        # 自动注册，无需手动调用
        result = ToolRegistry.execute_tool("file_manager", action="read", file_path="/path/to/file.txt")

    Attributes:
        name: 工具名称，唯一标识
        description: 工具描述，供LLM理解工具用途
        examples: 工具使用示例，每条包含 user_input（用户输入）、model_params（模型传入的参数）、return_value（返回值）
    """
    name = "file_manager"
    description = "用于读取和写入文件。当你需要读取文件内容或保存数据到文件时使用此工具。支持的操作类型：'read'（读取文件）、'write'（写入文件）。"
    param_descriptions = {
        "action": "操作类型，必填，可选值: 'read'（读取文件）或 'write'（写入文件）",
        "file_path": "文件路径，必填，相对路径或绝对路径均可",
        "content": "写入的文件内容，仅当 action='write' 时需要",
    }
    examples = [
        {
            "user_input": "帮我读一下 config.yaml 这个文件的内容",
            "model_params": {"action": "read", "file_path": "config.yaml"},
            "return_value": "app_name: 校园情感陪伴助手\nversion: 1.0.0\n...",
        },
        {
            "user_input": "把这段对话记录保存到 log.txt 中",
            "model_params": {"action": "write", "file_path": "log.txt", "content": "对话记录内容..."},
            "return_value": "文件 'log.txt' 写入成功",
        },
    ]

    def _tool_call(self, action: str, file_path: str, content: str = "") -> str:
        """
        执行文件操作

        Args:
            action: 操作类型，可选值: "read"（读取文件）, "write"（写入文件）
            file_path: 文件路径
            content: 写入内容（仅 action 为 "write" 时需要）

        Returns:
            str: 操作结果
        """
        if action == "read":
            if not os.path.exists(file_path):
                return f"错误: 文件 '{file_path}' 不存在"
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif action == "write":
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"文件 '{file_path}' 写入成功"
        else:
            return f"错误: 不支持的操作类型 '{action}'，仅支持 'read' 和 'write'"
