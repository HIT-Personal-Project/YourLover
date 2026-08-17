
from core.config import Settings
from agent.agent.ChatAgent import ChatAgent
from core.config import settings

from agent.models.OllamaModels import get_ollama_llm
import requests

from enum import Enum,auto
from agent.memory.MemoryItem import MemoryItem

from typing import overload



# from avatar.avatar_state import EmotionEnum


class AgentController:
    """
    负责管理整个ChatAgent的生命周期，包括连接、断开、调用等操作 
    以及与交互界面的通信。
    """
    def __init__(self,settings:Settings,configurable:dict) -> None:

        self.is_connected = False
        self.settings = settings
        self.configurable=configurable


    def chat(self,user_input:str,configurable:dict=None):
        """
        调用ChatAgent进行聊天
        """
        if configurable is not None:
            self.configurable = configurable

        if not self.is_connected:
            return AgentMessage("还没有连接上大模型，不能进行聊天~","Sad")
        state = self.agent.invoke(
            {
                "user_input": user_input,
                "user_id": self.configurable["user_id"],
                "session_id": self.configurable["session_id"],
            }
        )
        return AgentMessage(state["history"][-1])

    
    def chat_test(self,user_input:str,configurable:dict=None):
        """
        测试用，不调用ChatAgent，直接返回用户输入
        """
        return AgentMessage(user_input,"Happy") 

    
    def APIConnect(self,LLM_type:str,LLM_name:str,url=None,api_key=None):
        """
        连接ChatAgent
        """
        status, msg = self._agent_init(LLM_type,LLM_name,url,api_key)
        if status == ConnectState.OK:
            self.is_connected = True
            return AgentMessage(f"{LLM_name} 连接成功了！现在可以开始聊天了！","Happy")
        else:
            return AgentMessage(msg,"Sad")
            
    
    def _agent_init(self,LLM_type:str,LLM_name:str,url=None,api_key=None):
        """
        尝试初始化ChatAgent的API，判断其是否能够连接
        """
        if LLM_type == "ollama":
            try:
                resp = requests.get("http://localhost:11434/api/tags", timeout=5)
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"Ollama 服务正常，已下载模型: {models}")
            except requests.ConnectionError as e:
                print(f"Ollama 服务异常: {e}")
                return  ConnectState.FAILED, f"Ollama 服务异常: {e} 请检查Ollama服务是否启动。"

            if LLM_name not in models:            
                return  ConnectState.FAILED, f"Ollama 模型 {LLM_name} 不存在"
            
            else:
                self.agent = ChatAgent(
                    get_ollama_llm(model_name=self.settings.CHAT_MODEL_NAME),
                    self.settings,
                    {"configurable":self.configurable},
                )
                return ConnectState.OK, "连接成功"
        else:
            return ConnectState.FAILED, f"暂时不能连接{LLM_type}~"


class ConnectState(Enum):
    OK = auto()
    FAILED = auto()


class AgentMessage:
    """解析 MemoryItem 或直接文本，传给交互界面。

    设计说明：
    - Python 不支持方法重载，两个 __init__ 会导致后者被当作 @overload 桩函数，
      调用时直接抛 NotImplementedError。
    - 改用单一 __init__ + 类型判断，兼容两种构造方式：
      1. AgentMessage(memoryItem): 从 MemoryItem 提取完整元数据。
      2. AgentMessage(msg, emotion): 直接指定文本和情感（用于错误提示等）。
    """

    def __init__(self, source: "MemoryItem | str", emotion: str | None = None) -> None:
        """构造 AgentMessage。

        Args:
            source: MemoryItem 实例（提取完整元数据）或纯文本字符串。
            emotion: 当 source 为字符串时指定情感（如 "Happy"/"Sad"）；
                     source 为 MemoryItem 时忽略此参数。
        """
        if isinstance(source, MemoryItem):
            # 从 MemoryItem 提取完整元数据
            self.type = source.type
            self.speaker = source.speaker
            self.love = source.love
            self.ai_emo = source.ai_emo
            # self.user_emo = source.user_emo
            self.message = source.message
            self.msg = source.message  # 兼容属性访问
        else:
            # 直接指定文本和情感（用于错误提示、状态通知等）
            self.msg = str(source)
            self.message = str(source)  # 兼容属性访问
            self.ai_emo = emotion
            self.type = "Chat"
            self.speaker = "AI"
            self.love = 0
