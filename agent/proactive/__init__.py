"""主动对话引擎：模拟真人"一段时间没被理会会主动找你"的行为。

状态机（每个周期内）：
    IDLE --静默到期--> 问候(check-in) --再静默--> 问候... --达到无视上限--> 生气
    生气后进入 SILENT：不再主动发消息，直到用户主动发消息（哄她）才重置。

组件职责：
    - ProactiveEngine：QTimer 轮询静默时长 + 随机调度 + 生气惩罚；
      通过 Qt 信号把"该发主动消息了"交给上层（app.py 经 AgentWorker
      异步调用 LLM），不直接触碰 ChatAgent。
"""

from agent.proactive.engine import ProactiveEngine

__all__ = ["ProactiveEngine"]
