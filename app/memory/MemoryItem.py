'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 12:13:25
LastEditors: HongJin
LastEditTime: 2026-06-25 13:31:02
'''


#代表一条记忆的内容，每条记忆储存当前对话的元数据
from datetime import datetime


class MemoryItem():
    
    # MEMORY_ID = None # 记忆的唯一标识符 (也许需要)
    TYPE: str = None # 判断记忆类型是不是对话记忆，如果是思考或者工具调用的记忆需要特殊处理。 (Chat, Think, ToolCall)
    SPEAKER: str = None # System, AI 或者 User
    TEXT: str = None # 主观文本内容，仅包含对话文本。
    LOVE: int = 0 # 好感度，默认0
    EMO = None  # 情感当前对话的情感状态当前对话的情感状态， 可以存储情感词汇比如["快乐", "悲伤"]等，也可以存储情感得分比如{"快乐": 0.8, "悲伤": 0.2}。根据后续开发决策。
    SPEAK_TIME =  None  # 对话发生时的时间戳，默认当前时间
    
    #直接传参
    def __init__(self, TYPE: str, SPEAKER: str, TEXT: str, LOVE: int = 0, EMO = None, SPEAK_TIME: float = None):
        super(MemoryItem, self).__init__()
        self.TYPE = TYPE
        self.SPEAKER = SPEAKER
        self.TEXT = TEXT
        self.LOVE = LOVE
        self.EMO = EMO
        self.SPEAK_TIME = datetime.now().timestamp() if SPEAK_TIME is None else SPEAK_TIME
    
    def __init__(self, Parameters: dict):
        super(MemoryItem, self).__init__(**Parameters)
        
        # 从参数字典中获取属性值
        self.TYPE = Parameters.get("TYPE", None)
        self.LOVE = Parameters.get("LOVE", 0)
        self.SPEAKER = Parameters.get("SPEAKER", None)
        self.TEXT = Parameters.get("TEXT", None)
        self.EMO = Parameters.get("EMO", None)
        self.SPEAK_TIME = Parameters.get("SPEAK_TIME", None)
    
    
    #获取记忆内容添加到上下文中，根据记忆类型进行不同处理
    def get_memory(self):
        if self.TYPE == "Chat":
            #一般情况    
            pass
            
        elif self.TYPE == "Think":
            #思考类型
            pass
        
        elif self.TYPE == "ToolCall":
            #工具调用类型
            pass
        
    def __str__(self):
        return f"MemoryItem({self.TYPE}, {self.SPEAKER}, {self.TEXT}, {self.EMO}, {self.SPEAK_TIME})"
    
    
    