from tools import tool_map
from config import Config
# from models.OllamaModels import get_ollama_llm, get_ollama_embeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt import ToolNode

from typing import Literal


""""
ChatAgent 示例

"""
class ChatAgent:
    def __init__(self,config,session,llm):
        """
        初始化 ChatAgent 实例
        
        Args:
            config: 配置文件实例
            session: 会话实例
            llm: 语言模型实例
        
        Returns:
            None
        """
        self.config = config
        self.session = session
        self.llm = llm
        self.tools = tool_map
        self.tool_names = list(tool_map.keys())


    def __build_wrokflow(self) -> StateGraph[MessagesState]:
        """
        构建 ChatAgent 的工作流
        
        Returns:
            StateGraph[MessagesState]: 工作流实例
        """
        graph = StateGraph(MessagesState)
        graph.add_node('llm', self.chat)

        return graph


    def chat(self, state: MessagesState) -> dict:
        """
        与 ChatAgent 进行对话

        Args:
            state: 状态对象

        Returns:
            dict: 代理回复状态对象
        """
        response = self.llm.invoke(state['messages'])

        return {'messages': [response]}

    