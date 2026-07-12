'''
Descripttion: 网络搜索工具，用于执行网页搜索
version: 1.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 14:30:47
LastEditors: HongJin
LastEditTime: 2026-06-25 14:30:47
'''
from .BaseTool import BaseTool


class WebSearchTool(BaseTool):
    """
    网络搜索工具，用于搜索互联网上的信息

    使用方式:
        # 自动注册，无需手动调用
        result = ToolRegistry.execute_tool("web_search", query="人工智能最新进展")

    Attributes:
        name: 工具名称，唯一标识
        description: 工具描述，供LLM理解工具用途
        examples: 工具使用示例，每条包含 user_input（用户输入）、model_params（模型传入的参数）、return_value（返回值）
    """
    name = "web_search"
    description = "用于搜索互联网上的最新信息。当你需要查找当前事件、新闻、技术文档或任何需要实时数据的内容时使用此工具。"
    param_descriptions = {
        "query": "搜索关键词，必填，例如 '人工智能最新进展'",
        "max_results": "返回结果数量，可选，默认 5，范围 1-20",
    }
    examples = [
        {
            "user_input": "最近人工智能领域有什么重大突破？",
            "model_params": {"query": "人工智能最新突破", "max_results": "5"},
            "return_value": "搜索结果 (关键词: 人工智能最新突破):\n1. [标题1](url1)\n   摘要1\n2. [标题2](url2)\n   摘要2",
        },
        {
            "user_input": "帮我查一下今天北京的天气",
            "model_params": {"query": "北京今天天气"},
            "return_value": "搜索结果 (关键词: 北京今天天气):\n1. [北京天气预报](url)\n   今天北京晴，25-32度...",
        },
    ]

    def _tool_call(self, query: str, max_results: int = 5) -> str:
        """
        执行网络搜索

        Args:
            query: 搜索关键词
            max_results: 返回结果数量，默认5条

        Returns:
            str: 搜索结果摘要
        """
        search_results = [
            {"title": "搜索结果1", "url": "https://example.com/1", "summary": f"关于 '{query}' 的搜索结果摘要1"},
            {"title": "搜索结果2", "url": "https://example.com/2", "summary": f"关于 '{query}' 的搜索结果摘要2"},
            {"title": "搜索结果3", "url": "https://example.com/3", "summary": f"关于 '{query}' 的搜索结果摘要3"},
        ]

        result_str = f"搜索结果 (关键词: {query}):\n"
        for i, result in enumerate(search_results[:max_results], 1):
            result_str += f"{i}. [{result['title']}]({result['url']})\n   {result['summary']}\n"

        return result_str
