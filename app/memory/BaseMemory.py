'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:31:02
LastEditors: HongJin
LastEditTime: 2026-06-25 11:50:42
'''


from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from app.models.base import Message, MemoryItem



#这是一个记忆基类，所有记忆相关请继承自这个类实现
class BaseMemory(ABC):
    @abstractmethod
    def add(self, content: str, user_id: str, **kwargs) -> str:
        pass

    @abstractmethod
    def get(self, user_id: str, **kwargs) -> List[MemoryItem]:
        pass

    @abstractmethod
    def update(self, memory_id: str, content: str, **kwargs) -> None:
        pass

    @abstractmethod
    def delete(self, memory_id: str, **kwargs) -> None:
        pass

    @abstractmethod
    def clear(self, user_id: str) -> None:
        pass


