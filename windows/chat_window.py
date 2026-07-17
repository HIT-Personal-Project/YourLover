"""
聊天窗口模块 （项目主页）
负责：
- 聊天消息显示
- Markdown渲染
- 历史记录管理
- 输入框交互
- 语音按钮
- Tool调用状态显示

窗口生命周期：
- 关闭时执行hide()，而非destroy()
- 保持窗口状态，下次打开时恢复

事件流示例：
    User -> ChatWindow -> AgentClient -> Server -> Streaming -> EventBus -> ChatWindow更新
"""