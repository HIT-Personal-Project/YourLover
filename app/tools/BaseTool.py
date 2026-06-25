'''
Descripttion: 工具基类与注册中心模块，提供工具定义、注册和调用的基础设施
version: 2.0.0
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
import importlib
import os
import inspect
import pkgutil
import sys


class ToolConfig(BaseModel):
    """
    工具配置数据模型，用于定义工具的元信息

    Attributes:
        name: 工具名称，唯一标识
        description: 工具描述，用于AI理解工具用途
        parameters: 工具参数定义，键为参数名，值为参数类型或配置
        return_type: 返回值类型，可选
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    return_type: Optional[Type] = None


class BaseTool(ABC):
    """
    工具抽象基类，所有自定义工具都应继承此类

    使用方式:
        @register_tool
        class MyTool(BaseTool):
            name = "my_tool"
            description = "这是我的工具"
            param_descriptions = {
                "param1": "第一个参数的含义",
                "param2": "第二个参数的含义",
            }
            examples = [
                {
                    "user_input": "用户输入示例",
                    "model_params": {"param1": "value", "param2": 2},
                    "return_value": "调用结果示例",
                }
            ]

            def _tool_call(self, param1: str, param2: int) -> str:
                # 实现工具逻辑
                return result

    Attributes:
        name: 工具名称，子类必须重写
        description: 工具描述，子类可重写
        param_descriptions: 参数含义说明字典，键为参数名，值为参数描述
        examples: 工具使用示例列表，每条示例包含 user_input（用户输入）、model_params（模型应传入的参数 dict）、return_value（返回值）
    """
    name: str = ""
    description: str = ""
    param_descriptions: Dict[str, str] = {}
    examples: List[Dict[str, Any]] = []

    @abstractmethod
    def _tool_call(self, **kwargs) -> Any:
        """
        工具核心执行方法，子类必须实现此方法

        Args:
            **kwargs: 工具执行所需的参数

        Returns:
            Any: 工具执行结果
        """
        pass

    def tool_call(self, **kwargs) -> Any:
        """
        工具调用入口方法，封装对 _tool_call 的调用

        Args:
            **kwargs: 工具执行所需的参数

        Returns:
            Any: 工具执行结果
        """
        return self._tool_call(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """
        将工具信息转换为 LLM 友好的 JSON 格式

        Returns:
            Dict[str, Any]: 包含 name、description、params、examples 的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "params": self._get_parameters(),
            "examples": self.examples,
        }

    def _get_parameters(self) -> Dict[str, Dict[str, Any]]:
        """
        从 _tool_call 方法的签名中提取参数定义，返回 LLM 友好的字典结构

        每个参数包含:
            - type: 参数类型名称（字符串，如 "str"、"int"）
            - description: 参数含义（来自 param_descriptions）
            - required: 是否必填
            - default: 默认值（如果非必填）

        Returns:
            Dict[str, Dict[str, Any]]: 参数名到参数定义的映射
        """
        sig = inspect.signature(self._tool_call)
        hints = get_type_hints(self._tool_call)
        hints.pop("return", None)

        params: Dict[str, Dict[str, Any]] = {}
        for param_name, param in sig.parameters.items():
            if param_name == "kwargs" or param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            param_type = hints.get(param_name, Any)
            type_name = getattr(param_type, "__name__", str(param_type))

            default = None
            required = True
            if param.default is not inspect.Parameter.empty:
                default = param.default
                required = False

            params[param_name] = {
                "type": type_name,
                "description": self.param_descriptions.get(param_name, ""),
                "required": required,
                "default": default,
            }

        return params


class ToolRegistry:
    """
    工具注册中心，负责工具的注册、查找和执行

    使用方式:
        # 注册工具（通过 @register_tool 装饰器自动完成）
        @register_tool
        class MyTool(BaseTool):
            ...

        # 获取工具
        tool = ToolRegistry.get_tool("my_tool")

        # 执行工具
        result = ToolRegistry.execute_tool("my_tool", param1="value")

        # 列出所有工具（供LLM决策使用）
        tools = ToolRegistry.list_tools()

    Attributes:
        _tools: 工具存储字典，键为工具名称，值为工具实例
    """
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """
        注册工具到注册中心

        Args:
            tool: BaseTool 子类的实例
        """
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """
        根据名称获取工具实例

        Args:
            name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例，如果不存在返回 None
        """
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """
        获取所有已注册工具的信息列表，用于LLM进行ReAct决策

        Returns:
            List[Dict[str, Any]]: 工具信息字典列表，包含 name、description、parameters
        """
        return [tool.to_dict() for tool in cls._tools.values()]

    @classmethod
    def execute_tool(cls, name: str, **kwargs) -> Any:
        """
        根据名称执行工具

        Args:
            name: 工具名称
            **kwargs: 工具执行所需的参数

        Returns:
            Any: 工具执行结果

        Raises:
            ValueError: 工具不存在时抛出
        """
        tool = cls.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return tool.tool_call(**kwargs)

    @classmethod
    def clear(cls) -> None:
        """
        清空所有已注册的工具
        """
        cls._tools.clear()

    @classmethod
    def count(cls) -> int:
        """
        获取已注册工具的数量

        Returns:
            int: 工具数量
        """
        return len(cls._tools)


def register_tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """
    工具类装饰器，自动将工具类注册到 ToolRegistry

    使用方式:
        @register_tool
        class MyTool(BaseTool):
            name = "my_tool"
            description = "这是我的工具"

            def _tool_call(self, **kwargs):
                # 实现工具逻辑
                pass

    Args:
        cls: BaseTool 子类

    Returns:
        Type[BaseTool]: 原类（装饰器不改变类本身）

    Raises:
        ValueError: 如果工具名称为空
    """
    if not cls.name:
        raise ValueError(f"Tool class '{cls.__name__}' must have a non-empty name attribute")

    ToolRegistry.register(cls())
    return cls


def discover_tools(package_name: str = None) -> List[str]:
    """
    自动发现并注册指定包下的所有工具类

    扫描指定包中的所有子模块，导入模块并注册所有继承自 BaseTool 的非抽象类

    使用方式:
        # 在 tools/__init__.py 中调用，自动使用当前包名
        discovered = discover_tools()
        # 或显式指定包名
        discovered = discover_tools("tools")

    Args:
        package_name: 要扫描的包名，默认从调用方所在的包自动推断

    Returns:
        List[str]: 已注册的工具名称列表
    """
    registered_tools = []

    if package_name is None:
        frame = inspect.currentframe().f_back
        globals_dict = frame.f_globals
        package_name = globals_dict.get("__package__") or globals_dict.get("__name__", "")

    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        print(f"Failed to import package '{package_name}': {e}")
        return registered_tools

    for _, modname, _ in pkgutil.iter_modules(package.__path__):
        if modname == "BaseTool":
            continue
        full_module_name = f"{package_name}.{modname}"
        try:
            module = importlib.import_module(full_module_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, BaseTool)
                    and obj is not BaseTool
                    and not inspect.isabstract(obj)
                    and obj.__module__ == full_module_name
                ):
                    if obj.name and obj.name not in ToolRegistry._tools:
                        ToolRegistry.register(obj())
                        registered_tools.append(obj.name)
        except Exception as e:
            print(f"Failed to import module '{modname}': {e}")

    return registered_tools


def tool(name: str, description: str = ""):
    """
    工具函数装饰器，用于将普通函数快速转换为 BaseTool 子类并自动注册

    使用方式:
        @tool(name="my_tool", description="这是我的工具")
        def my_tool_func(param1: str, param2: int) -> str:
            # 实现工具逻辑
            return result

    Args:
        name: 工具名称
        description: 工具描述，可选

    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        hints = get_type_hints(func)
        return_type = hints.pop("return", None)

        class WrappedTool(BaseTool):
            name = name
            description = description

            def _tool_call(self, **kwargs):
                return func(**kwargs)

        WrappedTool._tool_call.__annotations__ = hints
        ToolRegistry.register(WrappedTool())

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
