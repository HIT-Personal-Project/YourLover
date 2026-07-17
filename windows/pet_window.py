"""
桌面宠物窗口模块
负责：
- 透明窗口渲染
- 悬浮窗口管理
- 拖拽交互
- 右键菜单
- Live2D模型显示
- 点击HitArea检测

不负责：
- 聊天功能（由ChatWindow负责）
- 设置功能（由SettingWindow负责）

事件流示例：
    Mouse点击 -> PetWindow -> Avatar -> HitArea -> EventBus -> Agent
"""