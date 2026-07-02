'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 12:13:25
LastEditors: HongJin
LastEditTime: 2026-06-25 13:31:02
'''
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, TypedDict

from langchain_core.messages import BaseMessage

#代表一条记忆的内容，每条记忆储存当前对话的元数据
@dataclass
class MemoryItem:
    """
    每条记忆的内容，每条记忆储存当前对话的元数据
    """
    # MEMORY_ID = None # 记忆的唯一标识符 (也许需要)
    type: str
    """判断记忆类型是不是对话记忆，如果是思考或者工具调用的记忆需要特殊处理。 (Chat, Think, ToolCall)"""
    speaker: str
    """System, AI 或者 User"""
    message: BaseMessage
    """Langchain的消息对象。"""
    love: int = 0
    """好感度，默认0"""
    ai_emo: Optional[Dict[str, float]] = None
    """AI当前对话的情感状态，可以存储情感词汇比如["快乐", "悲伤"]等，也可以存储情感得分比如{"快乐": 0.8, "悲伤": 0.2}。根据后续开发决策。"""
    user_emo: Optional[Dict[str, float]] = None
    """用户当前对话的情感状态，可以存储情感词汇比如["快乐", "悲伤"]等，也可以存储情感得分比如{"快乐": 0.8, "悲伤": 0.2}。根据后续开发决策。"""
    speak_time: float = None
    """对话发生时的时间戳，默认当前时间"""
    importance:float = 0.5
    """记忆的重要程度，默认0.5"""

    def __post_init__(self):
        """初始化后处理，设置默认时间戳"""
        if self.speak_time is None:
            self.speak_time = datetime.now().timestamp()

    #获取记忆内容添加到上下文中，根据记忆类型进行不同处理
    def get_memory(self) -> str:
        """获取记忆内容用于上下文，根据记忆类型进行不同处理"""
        if self.type == "Chat":
            #一般情况    
            return f"{self.speaker}: {self.message.content}"
            
        elif self.type == "Think":
            #思考类型
            return f"[思考] {self.message.content}"
        
        elif self.type == "ToolCall":
            #工具调用类型
            return f"[工具调用] {self.message.content}"
        
        else:
            return f"{self.speaker}: {self.message.content}"

    def to_dict(self) -> dict:
        """转换为字典，用于序列化"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryItem':
        """从字典创建实例，用于反序列化"""
        return cls(**data)

    def __str__(self):
        return f"MemoryItem({self.type}, {self.speaker}, {self.message.content[:30]}...)"
