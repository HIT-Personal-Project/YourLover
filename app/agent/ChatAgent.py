'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:23:13
LastEditors: HongJin
LastEditTime: 2026-06-25 14:38:34
'''
from Langchain_ollama import ChatOllama


class ChatAgent:
    def __init__(self, config):
        self.LLM = config['LLM']
        self.tools = config['tools']
        
        
    def chat(self, messages: list) -> Dict[str, Any]:
        """单次对话
        """
        response = self.LLM.chat_completion(
            messages=messages,
            model=self.LLM.model,
            temperature=self.LLM.temperature,
            max_tokens=self.LLM.max_tokens,
        )
        return response

    def _model_initial(self):
        """初始化大模型，包括加载记忆，情感等。
        """
        pass