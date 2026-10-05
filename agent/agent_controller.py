
from dataclasses import dataclass
import threading

from core.config import Settings
from agent.agent.ChatAgent import ChatAgent
from core.config import settings

from agent.models.OllamaModels import get_ollama_llm
import requests

from enum import Enum,auto
from agent.memory.MemoryItem import MemoryItem

from typing import overload

from utils.message_filter import extract_emotion


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
        # 串行化 invoke：正常对话与主动消息可能来自不同 QThread，并发调用
        # 同一个 LangGraph thread_id 会让 MemorySaver checkpoint 竞争，
        # 导致 messages 状态损坏、后续所有回复变空。锁保证同一时刻
        # 只有一个 worker 进入 LangGraph。
        self._invoke_lock = threading.Lock()


    def chat(self,user_input:str,configurable:dict=None):
        """
        调用ChatAgent进行聊天
        """
        if configurable is not None:
            self.configurable = configurable

        if not self.is_connected:
            return AgentMessage("还没有连接上大模型，不能进行聊天~","Sad")
        with self._invoke_lock:
            state = self.agent.invoke(
                {
                    "user_input": user_input,
                    "user_id": self.configurable["user_id"],
                    "session_id": self.configurable["session_id"],
                    "proactive_context": "",  # 显式清空，防止上一轮残留隐藏指令
                }
            )
        message = AgentMessage(state["history"][-1])
        # 时序修正：MemoryItem 在 _chat 节点构造，携带的是轮初好感度快照；
        # judge_affinity 节点在其后才解析 {{+N}} 标记并累加，这里用轮末
        # state 值覆盖，保证界面拿到的是本轮累加后的最新好感度
        message.love = int(state.get("love_snapshot", message.love))
        return message


    def chat_proactive(self, instruction: str, configurable: dict = None):
        """主动消息轮：注入隐藏指令让 Agent 以小爱身份主动发消息。

        与 chat() 的区别：
            - user_input 为空串：不产生用户 HumanMessage，指令走
              proactive_context 通道拼进 system prompt（用户与 UI 不可见）；
            - Agent 的回复（主动消息本体）照常进入消息列表、history 与
              SQLite，聊天窗口正常显示；
            - 主动轮不判定好感度增量（被无视的惩罚由 ProactiveEngine 直扣）。
        """
        if configurable is not None:
            self.configurable = configurable

        if not self.is_connected:
            return AgentMessage("（主动消息跳过：还没有连接上大模型）", "Sad")
        with self._invoke_lock:
            state = self.agent.invoke(
                {
                    "user_input": "",
                    "user_id": self.configurable["user_id"],
                    "session_id": self.configurable["session_id"],
                    "proactive_context": instruction,
                }
            )
        message = AgentMessage(state["history"][-1])
        # 主动轮好感度不变，但引擎可能刚扣过分：用轮末快照刷新界面显示
        message.love = int(state.get("love_snapshot", message.love))
        return message

    
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

@dataclass
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
            self.user_emo = source.user_emo
            self.message = source.message.content
            # self.msg = source.message.content  # 兼容属性访问

            self.message, self.ai_emo =  extract_emotion(self.message)
            self.ai_emo = self.ai_emo[0] if self.ai_emo else "Happy"
            print(self.message)
        else:
            # 直接指定文本和情感（用于错误提示、状态通知等）
            # self.msg = str(source)
            self.message = str(source)  # 兼容属性访问
            self.ai_emo = emotion
            self.type = "Chat"
            self.speaker = "AI"
            self.love = None  # 非聊天消息无真实好感度，界面不应刷新（app.py 会跳过）
