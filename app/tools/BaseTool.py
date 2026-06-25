'''
Descripttion: 
version: 
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:29:16
LastEditors: HongJin
LastEditTime: 2026-06-25 14:30:47
'''
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, get_type_hints
from pydantic import BaseModel, create_model
from functools import wraps


class ToolConfig(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: Optional[Type] = None


class BaseTool(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def _run(self, **kwargs) -> Any:
        pass

    def run(self, **kwargs) -> Any:
        return self._run(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters(),
        }

    def _get_parameters(self) -> Dict[str, Any]:
        hints = get_type_hints(self._run)
        hints.pop("return", None)
        return hints


class ToolRegistry:
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in cls._tools.values()]

    @classmethod
    def execute_tool(cls, name: str, **kwargs) -> Any:
        tool = cls.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return tool.run(**kwargs)


def tool(name: str, description: str = ""):
    def decorator(func):
        hints = get_type_hints(func)
        return_type = hints.pop("return", None)

        class WrappedTool(BaseTool):
            name = name
            description = description

            def _run(self, **kwargs):
                return func(**kwargs)

        WrappedTool._run.__annotations__ = hints
        ToolRegistry.register(WrappedTool())

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator