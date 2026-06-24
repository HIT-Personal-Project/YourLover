from abc import ABC, abstractmethod
from typing import List, Dict

class BaseSkill(ABC):
    name: str                     # 技能名称
    trigger: List[str]            # 触发关键词/意图
    priority: int                 # 优先级（数值越小优先级越高）
    
    @abstractmethod
    def can_handle(self, context: Dict) -> bool:
        """判断是否能处理当前上下文"""
        pass
    
    @abstractmethod
    def execute(self, context: Dict) -> Dict:
        """执行技能逻辑"""
        pass
