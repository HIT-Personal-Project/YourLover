'''
Descripttion: 情感陪伴Agent核心类，基于LangGraph构建工作流
version: 1.0
Author: HongJin
email: 756547077@qq.com
Date: 2026-06-25
LastEditors: HongJin
LastEditTime: 2026-07-02

工作流说明:
┌─────────────────────────────────────────────────────────────────────┐
│                        ChatAgent 状态流转图                         │
├─────────────────────────────────────────────────────────────────────┤
│                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  节点职责:                                                          │
│    load_memory: 首次会话时初始化记忆（好感度、历史记录等）           │
│    user_input: 处理用户输入，转换为消息格式                         │
│    llm: 调用大模型生成回复，将完整对话写入history                    │
├─────────────────────────────────────────────────────────────────────┤
│  状态字段:                                                          │
│    messages:   LangChain消息列表，用于LLM调用                       │
│    history:    MemoryItem列表，带元数据的完整记忆                   │
│    love:       好感度(0-100)，每次对话+1                           │
│    user_input: 当前用户输入                                         │
│    memory_loaded: 是否已加载记忆（路由判断用）                      │
└─────────────────────────────────────────────────────────────────────┘
'''

from tools import tool_map
from config import Settings, settings

# from models.OllamaModels import get_ollama_llm, get_ollama_embeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from langgraph.graph import StateGraph, END, START, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from memory.EmotionMemory import EmotionState, history_to_messages
from memory.MemoryItem import MemoryItem

from typing import Literal


class ChatAgent:
    """
    情感陪伴Agent核心类，负责处理用户对话、管理记忆和调用大模型

    核心能力:
    - 基于LangGraph的状态机工作流
    - 支持记忆持久化（通过MemorySaver）
    - 好感度系统（love值管理）
    - 完整的对话历史记录
    """

    def __init__(self, llm, config: Settings, session):
        """
        初始化 ChatAgent 实例

        Args:
            llm: 语言模型实例，需支持invoke方法
            config: 配置文件实例，包含系统提示词等配置
            session: 会话配置，格式: {"configurable": {"thread_id": "xxx"}}

        Returns:
            None
        """
        self.config = config
        self.session = session
        self.llm = llm
        self.tools = tool_map

        # 系统提示词，从配置中读取
        self.system_prompt = config.TEST_SYSTEM_PROMPT

        # 当前可用工具名称列表
        self.tool_names = list(tool_map.keys())

        # 将工具绑定到LLM，使其具备工具调用能力
        self.llm_with_tools = self.llm.bind_tools(list(self.tools.values()))

        self.memory_loaded = False

        # 构建LangGraph工作流
        self.__build_workflow()

    def invoke(self, user_input: dict, session: dict = None) -> dict:
        """
        执行 ChatAgent 的工作流，处理用户输入并返回回复

        Args:
            user_input: 用户输入字典，格式: {"user_input": "用户消息内容"}
            session: 会话配置（可选），默认使用初始化时的session

        Returns:
            EmotionState: 执行后的完整状态对象，包含messages、history、love等字段
        """
        # 默认使用初始化时的会话配置
        if session is None:
            session = self.session

        return self.workflow.invoke(user_input, config=session)

    def save_graph_figure(self, filename: str) -> None:
        """
        保存 ChatAgent 的工作流图（Mermaid格式转PNG）

        Args:
            filename: 输出图片文件名，如 "ChatAgent.png"

        Returns:
            None
        """
        graph_png = self.workflow.get_graph().draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(graph_png)

    # ---------- 工作流构建 ----------

    def __build_workflow(self) -> None:
        """
        构建LangGraph状态机工作流

        工作流结构:
        1. START → 条件路由 → load_memory（首次）或 user_input（非首次）
        2. load_memory → user_input
        3. user_input → emotion_analysis
        4. emotion_analysis → llm
        5. llm → should_call_tool → tools（有工具调用）或 END（无工具调用）
        6. tools → llm（工具执行后回到LLM继续处理）

        使用MemorySaver作为检查点，实现会话状态持久化
        """
        # 创建状态图，使用EmotionState作为状态定义
        graph = StateGraph(EmotionState)

        # 添加工作流节点
        graph.add_node('load_memory', self._load_memory)   # 记忆加载节点
        graph.add_node('emotion_analysis', self._emotion_analysis)  # 情感分析节点
        graph.add_node('user_input', self._user_input)       # 用户输入处理节点
        graph.add_node('tools', self._tool_call)            # 工具调用节点
        graph.add_node('llm', self._chat)                    # LLM调用节点

        # 条件边：根据memory_loaded状态决定首次加载还是直接处理输入
        graph.add_conditional_edges(
            START,
            self._should_load_memory,  # 路由判断函数
            {
                "load_memory": "load_memory",  # memory_loaded=False时进入
                "user_input": "user_input"     # memory_loaded=True时进入
            }
        )

        # 条件边：根据LLM回复是否包含工具调用决定下一步
        graph.add_conditional_edges(
            "llm",
            self._should_call_tool,  # 路由判断函数
            {
                "tools": "tools",    # 有tool_calls时进入工具执行节点
                END: END             # 无tool_calls时结束对话
            }
        )

        # 状态流转边
        graph.add_edge("user_input", "emotion_analysis")  # 输入处理后进行情感分析
        graph.add_edge("load_memory", "user_input")       # 记忆加载后处理输入
        graph.add_edge("emotion_analysis", "llm")         # 情感分析后调用LLM
        graph.add_edge("tools", "llm")                    # 工具执行后回到LLM

        # 编译工作流，启用检查点持久化
        self.workflow = graph.compile(checkpointer=MemorySaver())

    # ---------- 路由函数 ----------

    def _should_load_memory(self, state: EmotionState) -> Literal["load_memory", "user_input"]:
        """
        条件路由函数：决定首次会话还是后续会话

        判断逻辑:
        - 如果 memory_loaded 为 False 或不存在 → 进入 load_memory
        - 如果 memory_loaded 为 True → 进入 user_input（跳过加载）

        Args:
            state: 当前EmotionState状态对象

        Returns:
            Literal["load_memory", "user_input"]: 下一个节点名称
        """
        if self.memory_loaded is True:
            return "user_input"
        else:
            return "load_memory"

    def _should_call_tool(self, state: EmotionState) -> Literal["tools", END]:
        """
        条件路由函数：判断是否需要调用工具

        判断逻辑:
        - 如果最后一条消息是AIMessage且包含tool_calls → 进入 tools 节点执行工具调用
        - 否则 → 进入 END 结束对话

        Args:
            state: 当前EmotionState状态对象

        Returns:
            Literal["tools", END]: 下一个节点名称或END
        """
        messages = state["messages"]
        if not messages:
            return END

        last_message = messages[-1]
        
        # 检查是否有工具调用
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        else:
            return END

    # ---------- 工作流节点 ----------

    def _load_memory(self, state: EmotionState) -> dict:
        """
        记忆加载节点：初始化会话状态（首次会话时调用）

        目前为模拟实现，后续将接入长期记忆存储（如数据库）
        默认初始化好感度为77，记忆列表为空

        Args:
            state: 当前EmotionState状态对象

        Returns:
            dict: 初始化后的状态更新，包含love、history、memory_loaded字段
        """

        self.memory_loaded = True
        
        return {
            "love": 77,                # 初始好感度设置为77
            "history": [],             # 初始记忆列表为空
            "messages": []            # 初始消息列表为空
        }

    def _user_input(self, state: EmotionState) -> dict:
        """
        用户输入处理节点：将用户输入转换为LangChain消息格式

        注意：此节点仅做输入预处理，不写入history。
        完整的对话记忆会在llm节点中与AI回复一起写入。

        Args:
            state: 当前EmotionState状态对象，包含user_input字段

        Returns:
            dict: 状态更新，仅包含messages字段
        """
        # 将用户输入转换为LangChain HumanMessage格式
        user_message = HumanMessage(content=state["user_input"])

                # 创建用户输入的记忆项
        user_memory = MemoryItem(
            type="Chat",
            speaker="User",
            message=user_message,
            love=state["love"],
            ai_emo=None,
            user_emo=None
        )

        return {
            "messages": [user_message],
            "history": [user_memory]
        }
    
    def _emotion_analysis(self, state: EmotionState) -> dict:
        """
        情感分析节点：根据用户输入，分析用户的情感状态

        Args:
            state: 当前EmotionState状态对象，包含user_input和messages字段

        Returns:
            dict: 状态更新，包含user_emo字段
        """
        # 这里可以添加情感分析逻辑，例如使用情感分析模型
        # 例如：ai_emo = self.emotion_analyzer.analyze(state["messages"][-1].content)
        # user_emo = self.emotion_analyzer.analyze(state["user_input"])

        # 待实现

        emotion_analysis_result = AIMessage(
            content="用户情感分析结果：用户当前情感为：中性"
        )

        emotion_analysis_memory = MemoryItem(
            type="EmotionAnalysis",
            speaker="AI",
            message=emotion_analysis_result,
            love=state["love"],
            ai_emo=None,
            user_emo=None
        )


        return {
            "history": [emotion_analysis_memory],
            "messages": [emotion_analysis_result],
            "user_emo": None
        }

    def _chat(self, state: EmotionState) -> dict:
        """
        LLM调用节点：调用大模型生成回复（支持工具调用）

        处理流程:
        1. 获取当前messages列表
        2. 如果是首次调用，在messages前面注入system_prompt（包含好感度）
        3. 使用绑定了工具的LLM调用
        4. 如果有tool_calls，只更新messages（不写history）
        5. 如果没有tool_calls（最终回复），创建MemoryItem写入history并更新好感度

        Args:
            state: 当前EmotionState状态对象

        Returns:
            dict: 状态更新，包含messages、history、love字段
        """
        # 获取当前消息列表
        current_messages = state["messages"] or []

        # 构造系统提示词，动态注入当前好感度
        system_message = SystemMessage(
            content=self.system_prompt + 
            f"\n请根据你当前模拟的好感度（爱意值）为：{state['love']}（0-100分），对用户进行回复。"
        )

        # 构建LLM输入：system_message + 当前messages
        full_messages = [system_message] + current_messages

        # 使用绑定了工具的LLM调用
        response = self.llm_with_tools.invoke(full_messages)

        ai_memory = MemoryItem(
            type="Chat",
            speaker="AI",
            message=response,
            love=state["love"] + 1,
            ai_emo=None,
            user_emo=None
        )
        return {
            "messages": [response],
            "history": [ai_memory],
            "love": 1
        }

    def _tool_call(self, state: EmotionState) -> dict:
        """
        工具调用节点：执行LLM返回的工具调用，并将结果封装为ToolMessage

        处理流程:
        1. 从messages中获取最后一条AIMessage
        2. 提取tool_calls列表
        3. 遍历tool_calls，使用tool_map执行每个工具
        4. 为每个工具调用创建ToolMessage
        5. 返回EmotionState格式的状态更新

        Args:
            state: 当前EmotionState状态对象

        Returns:
            dict: 状态更新，包含messages字段（ToolMessage列表）
        """
        # 获取最后一条消息（应该是包含tool_calls的AIMessage）
        messages = state["messages"]
        if not messages:
            return {"messages": [], "history": [], "love": 0}

        last_message = messages[-1]
        
        # 检查是否有工具调用
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return {"messages": [], "history": [], "love": 0}

        # 执行所有工具调用并创建ToolMessage
        tool_messages = []

        tool_call_memories = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get('name')
            tool_args = tool_call.get('args', {})
            tool_call_id = tool_call.get('id', '')

            # 检查工具是否存在
            if tool_name not in self.tools:
                result = f"工具 '{tool_name}' 不存在"
            else:
                # 执行工具调用
                try:
                    result = self.tools[tool_name].invoke(tool_args)
                except Exception as e:
                    result = f"工具执行失败: {str(e)}"

            # 创建ToolMessage
            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id,
            )
            tool_messages.append(tool_message)

            tool_call_memory = MemoryItem(
                type="ToolCall",
                speaker="AI",
                message=tool_message,
                love=state["love"],
                ai_emo=None,
                user_emo=None
            )
            tool_call_memories.append(tool_call_memory)

        return {
            "messages": tool_messages,
            "history": tool_call_memories,
            "love": 0
        }
