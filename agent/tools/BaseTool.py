'''
Descripttion: 工具基类与自动封装模块，提供工具定义和 langchain @tool 自动封装的基础设施
version: 3.0.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25 11:29:16
LastEditors: HongJin
LastEditTime: 2026-06-27 14:30:00
'''
from abc import ABC, abstractmethod
from typing import Any, Dict, Annotated, get_type_hints
import inspect
import importlib
import pkgutil

from langchain_core.tools import tool as lc_tool  # langchain 自带的 @tool 装饰器


class BaseTool(ABC):
    """
    工具抽象基类，所有自定义工具都应继承此类

    子类必须定义:
        - name: 工具名称（唯一标识）
        - description: 工具描述（供 LLM 理解用途）
        - param_descriptions: 参数含义说明字典（键为参数名，值为参数描述）
        - _tool_call(): 工具核心执行方法

    使用方式:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "这是我的工具"
            param_descriptions = {
                "param1": "第一个参数的含义",
                "param2": "第二个参数的含义",
            }

            def _tool_call(self, param1: str, param2: int = 0) -> str:
                # 实现工具逻辑
                return result

    注意: 子类不再需要 @register_tool 装饰器，BaseTool.py 会自动扫描并封装
    """
    name: str = ""
    description: str = ""
    param_descriptions: Dict[str, str] = {}

    @abstractmethod
    def _tool_call(self, **kwargs) -> Any:
        """
        工具核心执行方法，子类必须实现

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


def _build_param_annotations(
    tool_instance: BaseTool,
) -> Dict[str, Any]:
    """
    根据 _tool_call 的函数签名和 param_descriptions，构建 langchain @tool 需要的参数注解

    对于每个参数，生成 Annotated[type, "参数描述"] 格式的注解，
    这样 langchain @tool 能自动提取参数描述供 LLM 使用。

    Args:
        tool_instance: BaseTool 子类实例

    Returns:
        Dict[str, Any]: 参数名 -> Annotated[type, description] 的映射字典
    """
    # 获取 _tool_call 的类型提示（排除 return）
    hints = get_type_hints(tool_instance._tool_call)
    hints.pop("return", None)

    # 获取 _tool_call 的函数签名
    sig = inspect.signature(tool_instance._tool_call)

    annotations: Dict[str, Any] = {}
    for param_name, param in sig.parameters.items():
        # 跳过 **kwargs 等可变参数
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        # 获取参数类型，默认为 str
        param_type = hints.get(param_name, str)

        # 获取参数描述，来自 param_descriptions 字典
        param_desc = tool_instance.param_descriptions.get(param_name, "")

        # 构建 Annotated[type, "描述"] 注解
        # langchain @tool 会从 Annotated 的第二个元素提取参数描述
        annotations[param_name] = Annotated[param_type, param_desc]

    return annotations


def _wrap_tool_instance(tool_instance: BaseTool):
    """
    将一个 BaseTool 子类实例封装为 langchain @tool 函数

    核心流程:
    1. 从 _tool_call 的签名中提取参数信息
    2. 用 Annotated[type, "描述"] 构建参数注解
    3. 动态创建一个带正确签名的函数
    4. 用 langchain @tool(name=..., description=...) 装饰该函数
    5. 返回可直接供 LLM bind_tools 使用的 langchain Tool 对象

    Args:
        tool_instance: BaseTool 子类实例

    Returns:
        langchain_core.tools.StructuredTool: 封装后的 langchain 工具对象
    """
    # 获取参数注解（Annotated 格式）
    param_annotations = _build_param_annotations(tool_instance)

    # 获取函数签名，用于确定哪些参数有默认值
    sig = inspect.signature(tool_instance._tool_call)

    # 构建函数参数字符串，例如: "query: Annotated[str, '搜索关键词'], max_results: Annotated[int, '结果数量'] = 5"
    param_lines = []
    for param_name, param in sig.parameters.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue

        # 参数类型注解
        annotation_str = param_annotations[param_name]

        # 处理默认值
        if param.default is not inspect.Parameter.empty:
            param_lines.append(f"{param_name}: {annotation_str} = {repr(param.default)}")
        else:
            param_lines.append(f"{param_name}: {annotation_str}")

    params_str = ", ".join(param_lines)

    # 动态创建函数的代码
    # 函数名 = 工具名（langchain @tool 会用函数名作为工具名）
    # 函数体: 调用 tool_instance.tool_call，用 locals() 捕获所有参数并传入
    #   locals() 在函数内部返回的是该函数的局部变量（即参数），不包含 exec 命名空间中的变量
    # docstring: 重复工具的 description，langchain @tool 也会从 docstring 提取描述
    func_code = (
        f"def {tool_instance.name}({params_str}):\n"
        f'    """{tool_instance.description}"""\n'
        f"    return _tool_instance_.tool_call(**locals())"
    )

    # 构建函数的命名空间
    # _tool_instance_: 闭包中引用的 tool 实例
    # typing: Annotated 转字符串后包含 "typing.Annotated"，需要 typing 模块在命名空间中
    import typing as _typing_mod
    namespace = {
        "_tool_instance_": tool_instance,
        "Annotated": Annotated,
        "typing": _typing_mod,
    }

    # 执行动态代码，在 namespace 中生成函数
    exec(func_code, namespace)

    # 取出生成的函数对象
    raw_func = namespace[tool_instance.name]

    # 使用 langchain 的 @tool(description="...") 装饰器封装
    # langchain 会自动从 Annotated 提取参数描述，从函数名提取工具名
    wrapped = lc_tool(description=tool_instance.description)(raw_func)

    return wrapped


def discover_and_wrap_tools(package_name: str = None) -> Dict[str, Any]:
    """
    自动发现当前包下所有 BaseTool 子类，并将其封装为 langchain @tool 函数

    工作流程:
    1. 扫描指定包中的所有子模块
    2. 找到所有继承自 BaseTool 的非抽象类
    3. 实例化每个工具类
    4. 调用 _wrap_tool_instance() 将其封装为 langchain Tool
    5. 存入 tool_map 字典（键为工具名称，值为 langchain Tool 对象）

    使用方式:
        # 在 tools/__init__.py 中调用
        tool_map = discover_and_wrap_tools()

        # 然后可以直接 bind 给 LLM
        llm_with_tools = llm.bind_tools(list(tool_map.values()))

    Args:
        package_name: 要扫描的包名，默认从调用方所在包自动推断

    Returns:
        Dict[str, langchain_core.tools.StructuredTool]: 工具名称 -> langchain Tool 对象的映射
    """
    tool_map: Dict[str, Any] = {}

    # 自动推断包名
    if package_name is None:
        frame = inspect.currentframe().f_back
        globals_dict = frame.f_globals
        package_name = globals_dict.get("__package__") or globals_dict.get("__name__", "")

    # 导入包
    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        print(f"[ToolDiscovery] 导入包 '{package_name}' 失败: {e}")
        return tool_map

    # 遍历包中的所有子模块
    for _, modname, _ in pkgutil.iter_modules(package.__path__):
        # 跳过 BaseTool 自身所在的模块，避免重复扫描
        if modname == "BaseTool":
            continue

        full_module_name = f"{package_name}.{modname}"

        try:
            module = importlib.import_module(full_module_name)
        except Exception as e:
            print(f"[ToolDiscovery] 导入模块 '{modname}' 失败: {e}")
            continue

        # 在模块中查找所有 BaseTool 子类
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseTool)
                and obj is not BaseTool           # 排除 BaseTool 自身
                and not inspect.isabstract(obj)    # 排除抽象类
                and obj.__module__ == full_module_name  # 只取当前模块定义的类，排除 import 进来的
            ):
                # 检查工具名称是否有效
                if not obj.name:
                    print(f"[ToolDiscovery] 跳过类 '{obj.__name__}': name 属性为空")
                    continue

                # 检查是否重复注册
                if obj.name in tool_map:
                    print(f"[ToolDiscovery] 跳过类 '{obj.__name__}': 工具名 '{obj.name}' 已存在")
                    continue

                # 实例化工具类
                tool_instance = obj()

                # 封装为 langchain @tool 并加入 tool_map
                try:
                    lc_tool_obj = _wrap_tool_instance(tool_instance)
                    tool_map[obj.name] = lc_tool_obj
                    print(f"[ToolDiscovery] 已注册工具: {obj.name}")
                except Exception as e:
                    print(f"[ToolDiscovery] 封装工具 '{obj.name}' 失败: {e}")

    return tool_map
