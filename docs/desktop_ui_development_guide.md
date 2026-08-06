# 🎨 YourLover 桌面 UI 开发指南

> 📌 **本文档说明桌面端（悬浮宠物 + 聊天主页 + 设置面板）的整体架构、事件总线机制、各组件/窗口职责，以及如何在此基础上扩展新功能。**

---

## 📋 目录

1. [🏗️ 整体架构概览](#1-整体架构概览)
2. [⚡ 事件总线（EventBus）机制](#2-事件总线eventbus机制)
3. [🧩 组件与窗口职责](#3-组件与窗口职责)
4. [🔧 如何扩展新功能](#4-如何扩展新功能)
5. [🚪 以"退出"为例说明完整扩展流程](#5-以退出为例说明完整扩展流程)
6. [📜 开发约定](#6-开发约定)
7. [🗂️ 快速参考：常用文件对应关系](#7-快速参考常用文件对应关系)

---

## 1. 🏗️ 整体架构概览

桌面 UI 采用 **组件化 + 事件总线** 架构，目标是把窗口、控件、业务逻辑彻底解耦：

| 📁 目录 | 🎯 职责 |
| :--- | :--- |
| `windows/` | 放置所有顶层窗口（悬浮窗、聊天窗、设置窗） |
| `widgets/` | 放置可复用组件（聊天组件、右键菜单、设置项等） |
| `core/event_bus.py` | 全局事件总线，所有跨模块通信都通过它 |
| `demos/desktop_ui_demo.py` | 可运行的演示入口，用假 Avatar 验证 UI 流程 |

### 1.1 🌟 核心设计原则

> 💡 **原则一：窗口之间不直接互相调用**
> 例如 `LoverWindow` 不会直接 `chat_window.show()`，而是发射 EventBus 信号。

> 💡 **原则二：组件只负责自身 UI 与内部信号**
> 例如 `ChatInput` 只会在用户点击发送时发射 `send_clicked(text)`，不直接调用 Agent。

> 💡 **原则三：WindowManager 是唯一的窗口协调者**
> 它订阅 EventBus，把事件分发给对应窗口。

> 💡 **原则四：Avatar 相关逻辑通过 `AvatarControllerProtocol` 解耦**
> `LoverWindow` 只负责容器和原始鼠标事件，具体 Live2D 渲染交给实现协议的控制器。

---

## 2. ⚡ 事件总线（EventBus）机制

### 2.1 📡 什么是 EventBus

`core/event_bus.py` 中定义了一个全局单例 `event_bus`，它继承自 `QObject`，内部使用 PySide6 的 `Signal` 定义所有跨模块事件。

任何模块都可以通过以下方式通信：

```python
from core.event_bus import event_bus

# 发送事件
event_bus.show_chat_window_requested.emit()

# 接收事件
event_bus.show_chat_window_requested.connect(on_show_chat)
```

### 2.2 🔄 信号传递流程

一个典型的事件链路如下：

```text
用户操作（点击/输入/拖拽）
    ↓
具体组件（MenuItem / ChatInput / LoverWindow）
    ↓
EventBus 信号发射
    ↓
WindowManager 或其他监听者接收并执行动作
```

> 🔍 **以点击右键菜单的"退出"为例：**
>
> ```text
> 用户点击"退出"
>     ↓
> QAction.triggered
>     ↓
> MenuItem.on_triggered()
>     ↓
> event_bus.application_quit_requested.emit()
>     ↓
> WindowManager._setup_event_routing() 中已连接：
>     event_bus.application_quit_requested.connect(self.quit)
>     ↓
> WindowManager.quit() → self._app.quit()
> ```

> ⚠️ **注意：没有直接调用 `sys.exit()`**。`WindowManager.quit()` 调用的是 `QApplication.quit()`，这样 Qt 能正常清理资源、关闭窗口、释放对象。

### 2.3 🎯 典型事件流程示例

#### 🏠 示例 A：右键点击"主页"

```text
LoverWindow 右键菜单 → MenuItem(HOME).on_triggered()
    → event_bus.menu_home_requested.emit()
    → event_bus.show_chat_window_requested.emit()
        → WindowManager.show_chat() 显示 ChatWindow
```

#### 💬 示例 B：用户发送消息

```text
ChatInput._on_send()
    → send_clicked.emit(text)
    → ChatWindow.connect_signals() 中：
        self._input.send_clicked.connect(event_bus.user_message_sent.emit)
    → event_bus.user_message_sent.emit(text)
        → ChatWindow.append_user_message(text) 显示到历史
        → desktop_ui_demo.on_user_message(text) 启动模拟 Agent 回复线程
```

#### 🤖 示例 C：Agent 流式回复

```text
FakeAgentWorker.run()
    → event_bus.agent_thinking_started.emit()
    → event_bus.agent_stream_chunk.emit(chunk)
    → event_bus.agent_reply_received.emit(event)
        → ChatWindow._on_agent_thinking_started()
        → ChatWindow._on_agent_stream_chunk()
        → ChatWindow._on_agent_reply_received()
        → WindowManager._on_agent_reply()（窗口管理层补充逻辑：震动宠物）
```

#### 💭 示例 D：迷你聊天（快速对话）

> 迷你聊天通过 `main.py` 中的 `AgentWorker` 调用 `AgentController`，与大聊天窗口共用同一个 Agent，但使用**独立的 session_id** 实现会话隔离。

```text
用户点击💬按钮
    → MiniChatOverlay.expand() 展开输入框
    → 用户输入文本 + Enter / 点击➤
    → event_bus.mini_chat_input_sent.emit(text)
        → main.py: on_mini_chat_message(text)
            → 创建 AgentWorker(mini_chat=True, configurable={session_id:"mini-chat"})
            → AgentWorker.run():
                → event_bus.mini_chat_thinking_started.emit()
                    → MiniChatOverlay.show_thinking()
                    → SpeechBubble.show_thinking() 头顶显示"💭 思考中..."
                    → WindowManager._on_mini_chat_thinking() → AvatarController 播放思考表情
                → AgentController.chat_test(text, configurable)
                → event_bus.mini_chat_reply_received 不在此发射（仅大聊天发射 agent_thinking_finished）
                → reply_ready.emit(AgentMessage)
                    → main.py: _on_mini_chat_reply(agent_message)
                        → event_bus.mini_chat_reply_received.emit(reply_text)
                            → MiniChatOverlay.show_reply(reply)
                            → SpeechBubble.show_message(reply) 头顶显示回复
                            → WindowManager._on_mini_chat_reply() → AvatarController 播放说话动作
                            → 8秒后自动隐藏
```

> 🔔 **系统提示自动触发**：AgentController 启动时 `APIConnect()` 返回 `AgentMessage("连接成功了！", "Happy")`，`main.py` 将其保存到 `_startup_message`，在 `manager.run()` 后延迟 800ms 通过 `mini_chat_reply_received` 自动显示在角色头顶气泡。

**迷你聊天与大聊天窗口的区别：**

| 特性 | 🏠 大聊天窗口 | 💭 迷你聊天 |
| :--- | :--- | :--- |
| **触发方式** | 右键"主页"打开 | 角色右下角 💬 按钮触发 |
| **消息记录** | 记录在 `ChatWindow` 历史中 | 在角色头顶气泡显示 |
| **信号** | `user_message_sent` / `agent_reply_received` | `mini_chat_input_sent` / `mini_chat_reply_received` |
| **会话隔离** | 每个会话有独立 `session_id` | 固定 `session_id="mini-chat"` |
| **信号隔离** | `agent_thinking_finished` 仅在大聊天模式发射 | 迷你聊天模式不会污染 ChatWindow 状态 |

### 2.4 📊 当前 EventBus 信号分类

| 🏷️ 分类 | 📡 信号 | 📝 说明 |
| :--- | :--- | :--- |
| **Avatar 交互** | `avatar_clicked(x, y)` | Avatar 区域被点击 |
| | `avatar_hit_area_clicked(area_name)` | 命中 HitArea |
| | `avatar_drag_started(direction)` | 拖拽开始，带初始方向 `"left"/"right"/"up"/"down"` |
| | `avatar_dragged(dx, dy)` | 拖拽中 |
| | `avatar_drag_direction(direction)` | 拖拽过程中方向变化 |
| | `avatar_drag_finished(x, y)` | 拖拽结束 |
| | `avatar_shaken()` | 检测到摇晃 |
| | `avatar_state_changed(state)` | Avatar 状态变化 |
| **菜单/导航** | `menu_home_requested()` | 请求主页 |
| | `menu_settings_requested()` | 请求设置 |
| | `menu_quit_requested()` | 请求退出 |
| | `menu_item_triggered(id, payload)` | 通用菜单项触发 |
| **聊天** | `user_message_sent(text)` | 用户发送消息 |
| | `chat_session_changed(session_id)` | 聊天窗口切换/新建会话，通知 AgentController 更新 session_id |
| | `agent_reply_received(event)` | Agent 完整回复 |
| | `agent_stream_chunk(chunk)` | 流式片段 |
| | `agent_thinking_started/finished()` | Agent 思考状态（仅大聊天模式发射） |
| **迷你聊天** | `mini_chat_input_sent(text)` | 用户在迷你输入框发送消息 |
| | `mini_chat_thinking_started()` | 迷你聊天开始思考 |
| | `mini_chat_reply_received(text)` | 迷你聊天收到回复（角色头顶气泡显示） |
| **设置** | `setting_changed(key, value)` | 单个设置项变化 |
| | `settings_batch_changed(values)` | 批量设置变化 |
| | `settings_save_requested()` | 请求保存设置 |
| **窗口管理** | `show_chat_window_requested()` | 显示聊天窗 |
| | `hide_chat_window_requested()` | 隐藏聊天窗 |
| | `show_setting_window_requested()` | 显示设置窗 |
| | `hide_setting_window_requested()` | 隐藏设置窗 |
| | `hide_all_secondary_windows_requested()` | 隐藏所有二级窗口 |
| | `application_quit_requested()` | 请求退出应用 |

---

## 3. 🧩 组件与窗口职责

### 3.1 📁 `windows/` 目录

#### 🪟 `base_window.py`

所有窗口的抽象基类 `BaseWindow`（继承 `QMainWindow`）。

- 统一窗口生命周期：`show_window()`、`hide_window()`、`toggle()`。
- 子类必须实现 `setup_ui()` 和 `connect_signals()`。
- 默认 `closeEvent` 改为隐藏而非退出。

---

#### 🐾 `lover_window.py`

> **虚拟伴侣悬浮窗口** `LoverWindow`

- 无边框、透明、置顶悬浮。
- 承载 Avatar 渲染控件（由外部注入）。
- 处理鼠标拖拽、摇晃检测。
- 右键弹出菜单（主页、设置、退出）。
- 管理 HitArea，把点击事件转发到 EventBus。
- 不负责具体 Live2D 渲染。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `set_avatar_widget(widget)` | 注入 Avatar 渲染控件 |
| `register_hit_area(name, rect)` | 注册可点击区域 |
| `shake_avatar()` | 触发摇晃动画（委托 AvatarController） |
| `on_avatar_clicked(pos)` | 处理 Avatar 区域点击 |
| `position_changed(pos)` | 窗口移动时发射，供 MiniChatOverlay 等跟随窗口监听 |

---

#### 💬 `chat_window.py`

> **聊天主页窗口** `ChatWindow**（Claude Desk 风格）

- **左右双栏布局**：左侧 `ChatSessionList`（会话列表），右侧 `ChatHeader` + `ChatHistory` + `ChatInput`。
- 把用户输入转发到 `user_message_sent`。
- 订阅 Agent 事件并更新历史记录。
- 顶部设置按钮打开设置面板。
- **管理会话**：新建、切换、删除会话；切换会话时恢复历史消息。
- **会话隔离**：新建/切换会话时发射 `chat_session_changed(session_id)`，通知 `AgentController` 更新 `session_id`，确保每个会话的 Agent 记忆独立。
- 消息追加时自动保存到当前会话，并更新会话列表预览。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `append_user_message(text)` / `append_agent_message(text)` | 追加消息（同时保存到会话） |
| `update_last_agent_message(text)` | 流式更新最后一条消息 |
| `set_status(text, color)` | 更新顶部状态 |
| `create_new_session()` | 新建会话，发射 `chat_session_changed(session_id)` |
| `switch_session(session_id)` | 切换会话，发射 `chat_session_changed(session_id)` |
| `_on_session_clicked(session_id)` | 会话被点击时发射 `chat_session_changed` + 恢复消息历史 |
| `_on_session_deleted(session_id)` | 删除会话 |
| `_save_message_to_session(role, content)` | 内部方法，保存消息到当前会话 |

---

#### ⚙️ `setting_window.py`

> **设置面板窗口** `SettingWindow`

- 无边框、可从右侧滑入滑出。
- 动态管理设置项。
- 保存时广播 `settings_batch_changed` 和 `settings_save_requested`。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `add_setting_item(item)` | 添加设置项 |
| `get_all_values()` | 获取所有设置值 |
| `save_settings()` | 保存并隐藏 |
| `slide_in(anchor)` / `slide_out()` | 滑入滑出动画 |

---

#### 🎛️ `window_manager.py`

> **窗口管理器**

- 创建并持有 `LoverWindow`、`ChatWindow`、`SettingWindow`、`MiniChatOverlay`。
- 订阅 EventBus，把事件路由到对应窗口。
- 注入 AvatarController 及其渲染控件。
- 管理窗口联动（如打开设置时定位在聊天窗旁边）。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `run()` | 显示悬浮窗 + 迷你聊天浮层 |
| `quit()` | 退出应用 |
| `set_avatar_controller(controller)` | 注入 AvatarController |
| `show_chat()` / `show_settings()` | 显示二级窗口 |
| `mini_chat_overlay` | 返回迷你聊天浮层实例 |

---

#### 💭 `mini_chat_overlay.py`

> **迷你聊天浮层** `MiniChatOverlay`（快速对话入口）

- 无边框、透明、置顶浮动窗口，始终在角色右下角显示一个 💬 按钮。
- 点击 💬 展开输入框 + 发送按钮 + 关闭按钮。
- 用户输入消息发送后，通过 `mini_chat_input_sent` 事件广播。
- 监听 `mini_chat_thinking_started` / `mini_chat_reply_received`，在角色上方显示 `SpeechBubble` 对话气泡。
- 跟踪 `LoverWindow.position_changed` 信号，角色拖动时自动跟随。
- **z-order 修复**：拖拽后 LoverWindow 会被 Qt raise 到最上层，`_on_target_moved` 中调用 `self.raise_()` 确保浮层不被遮挡。

> 📝 **设计说明：**
> - 迷你聊天不需要打开大聊天窗口（`ChatWindow`），是独立的轻量对话入口。
> - 收起状态：仅显示圆形 💬 按钮（56×56），位于角色右下角部分重叠。
> - 展开状态：输入框 + 发送 + 关闭（320×52），位于角色右下方右对齐。
> - 发送时禁用输入，思考时角色头顶气泡显示"💭 思考中..."动画。
> - 回复显示后 8 秒自动隐藏气泡。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `set_target_window(window)` | 设置跟踪的目标窗口（LoverWindow），连接 `position_changed` 信号 |
| `expand()` / `collapse()` | 展开 / 收起输入框 |
| `show_reply(text)` | 显示回复气泡，恢复输入 |
| `show_thinking()` | 显示思考气泡，禁用输入 |
| `hide_bubble()` | 隐藏气泡 |

---

#### 🎭 `avatar/avatar_controller_protocol.py`

> ⚠️ 本文件属于 `avatar/` 模块，不在 `windows/` 下。

定义 `AvatarControllerProtocol`，规定 Avatar 控制器必须实现的方法：

| 方法 | 说明 |
| :--- | :--- |
| `on_click(x, y)` | 原始点击坐标 |
| `on_hit_area(area_name)` | 命中区域 |
| `on_shake()` | 摇晃手势 |
| `on_drag_start(direction)` | 拖拽开始，带初始方向 `"left"/"right"/"up"/"down"` |
| `on_drag_direction(direction)` | 拖拽过程中方向变化 |
| `on_drag_end()` | 拖拽结束 |
| `on_drag(x, y)` | 每帧鼠标跟随 |
| `on_update()` | 每帧模型更新 |
| `play_motion(name)` / `change_expression(name)` / `set_state(name)` | 动作/表情/状态控制 |
| `get_render_widget()` | 返回渲染控件 |

> 📌 **位置说明**：协议定义的是 Avatar 控制器的接口契约，逻辑上属于 avatar 模块。
> **依赖方向**：`windows` → `avatar.avatar_controller_protocol`（协议），`avatar.controller` → `avatar.avatar_controller_protocol`（实现），无循环依赖。

---

### 3.2 📁 `widgets/` 目录

#### 🧱 `base/base_widget.py`

所有可复用组件的抽象基类 `BaseWidget`（继承 `QWidget`）。

- 子类必须实现 `setup_ui()` 和 `connect_signals()`。
- 可选重写 `refresh(data)` 和 `apply_style()`。

---

#### 🔌 `base/extensible_item.py`

> **可扩展列表项接口** `ExtensibleItem`

- 统一右键菜单项、设置项等动态增删项的行为。
- 要求实现 `payload`、`create_widget()`、`on_triggered()`、`on_removed()`。
- `ItemPayload` 封装 `item_id`、`title`、`icon`、`extra`。

---

#### 🍔 `menu/menu_builder.py`

> **右键菜单构建器** `MenuBuilder`

- 链式 API：`add_home()`、`add_settings()`、`add_quit()`、`add_custom()`、`add_separator()`。
- 最终调用 `build(parent)` 生成 `ContextMenu`。

---

#### 📋 `menu/menu_item.py`

> **单个右键菜单项** `MenuItem`，实现 `ExtensibleItem`

- 根据 `MenuItemType` 决定触发行为：
  - `HOME` → 发送 `menu_home_requested` + `show_chat_window_requested`
  - `SETTINGS` → 发送 `menu_settings_requested` + `show_setting_window_requested`
  - `QUIT` → 发送 `menu_quit_requested` + `application_quit_requested`
  - `CUSTOM` → 只发送 `menu_item_triggered`，可额外传 `callback`
- `create_widget()` 创建 `QAction`

---

#### 📑 `menu/context_menu.py`

> **右键菜单容器** `ContextMenu`

- 管理一组 `MenuItem`。
- 提供 `add_item()`、`remove_item()`、`clear()`、`show_at(pos)`。
- 发射本地信号 `item_triggered(id, payload)`（可选使用）。

---

#### 🎩 `chat/chat_header.py`

聊天窗口顶部栏。

- 显示头像、标题、状态。
- 提供设置按钮，点击发射 `settings_clicked`。
- 卡通游戏风：粉色头像底（圆形）、粉色边框、樱花 🌸 emoji 头像。

---

#### 📚 `chat/chat_session_list.py`

> **左侧历史会话列表组件** `ChatSessionList`（含 `SessionItem` 和 `SessionData`）

**职责：**

- 在聊天窗口左侧展示所有历史会话。
- 顶部"✨"按钮新建会话。
- 支持动态增删会话、切换选中、删除会话。
- 选中态使用粉色高亮 + 边框。
- hover 时显示删除按钮（红色圆形）。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `add_session(data)` | 添加会话 |
| `remove_session(session_id)` | 删除会话 |
| `update_session(data)` | 更新会话标题与预览 |
| `select_session(session_id)` | 选中会话 |
| `clear()` | 清空会话 |
| `current_session_id()` | 当前会话 ID |

**📡 信号：**

| 信号 | 说明 |
| :--- | :--- |
| `session_clicked(session_id)` | 会话被点击 |
| `session_deleted(session_id)` | 会话被请求删除 |
| `new_session_requested()` | 请求新建会话 |

**📦 数据模型 `SessionData`：**

| 字段 | 说明 |
| :--- | :--- |
| `session_id` | 唯一标识 |
| `title` | 会话标题 |
| `preview` | 最后消息预览 |
| `updated_at` | 更新时间 |
| `avatar` | 会话头像 emoji |

**🖼️ `SessionItem`：**

- 单个会话列表项（QFrame）。
- 显示头像、标题、预览。
- 点击发射 `clicked`，删除按钮发射 `delete_clicked`。
- 鼠标进入时显示删除按钮，离开时隐藏。

---

#### 🕰️ `chat/chat_history.py`

聊天历史记录面板。

- 维护 `ChatBubble` 列表。
- 支持追加消息、更新最后一条消息（流式）、清空历史。
- 自动滚动到底部。
- 卡通风：粉色细滚动条、暖白背景 `#fffafc`。

---

#### 🗨️ `chat/chat_bubble.py`

单条聊天气泡。

- **修复了一左一右问题**：通过 stretch 控制对齐，用户气泡靠右、Agent 气泡靠左。
- 卡通游戏风：
  - 用户消息：粉色 `#ec4899` 实底白字，圆角 18px，右下角小圆角（气泡尾巴效果）。
  - Agent 消息：白色卡片 + 粉色边框 `#fce7f3`，圆角 18px，左下角小圆角。
  - 系统消息：淡黄提示，居中。
- 暴露 `refresh(data)` 和 `set_content(text)`。

---

#### ⌨️ `chat/chat_input.py`

聊天输入区域。

- 多行文本输入 + 发送按钮。
- 支持 `Ctrl+Enter` 快捷键发送。
- 卡通风：粉色边框、聚焦时粉色加粗边框、发送按钮粉色三态色（hover/pressed/disabled）。
- 点击发送时发射 `send_clicked(text)`。

---

#### 🎈 `mini_chat/speech_bubble.py`

> **角色头顶对话气泡** `SpeechBubble`

**职责：**

- 在角色上方显示对话内容或"思考中"状态。
- 卡通游戏风：圆角矩形 + 底部三角尾巴指向角色（paintEvent 自绘）。
- 白底粉色边框，自动根据文本长度调整宽高。
- 支持"思考中"省略号动画（每 400ms 循环 `.`/`..`/`...`）。
- 支持自动隐藏（默认 8 秒）。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `show_message(text)` | 显示对话内容，并启动自动隐藏定时器 |
| `show_thinking()` | 显示"💭 思考中..."动画状态 |
| `hide_bubble()` | 立即隐藏气泡 |
| `set_auto_hide(seconds)` | 设置自动隐藏秒数，0 表示不自动隐藏 |

> 🎨 **绘制说明**：
> - `paintEvent` 使用 `QPainterPath` 绘制圆角矩形 + 底部三角尾巴。
> - 主体区域高度 = 窗口高度 - 尾巴高度。
> - 尾巴位于底部中央，指向下方的角色。

---

#### 🔧 `settings/setting_panel.py`

设置项列表面板。

- 以滚动列表展示所有 `SettingItem`。
- 动态增删、批量取值/设值。
- 转发 `setting_changed` 为本地 `item_value_changed` 信号。

---

#### 🎚️ `settings/setting_item.py`

设置项抽象基类与具体实现：

- **`SettingItem`**：基类，封装 `key`、`label`、`value`
  - 值变化时发送 `event_bus.setting_changed.emit(key, value)`
  - 子类只需实现 `create_editor()` 和 `_update_editor()`
- **`ToggleSettingItem`**：开关（布尔）
- **`TextSettingItem`**：文本输入
- **`SliderSettingItem`**：整数滑块/数值框
- **`OptionSettingItem`**：下拉选项

---

### 3.3 📁 `core/` 目录

#### 📡 `event_bus.py`

全局事件总线，定义所有 Signal。

---

#### 📨 `agent_event.py`

`AgentEvent` 数据类，统一 Agent 相关事件的载荷格式。

---

### 3.4 🚀 `main.py`（应用主入口）

> `main.py` 是桌面助手的**真正入口**（`demos/desktop_ui_demo.py` 仅为 UI 原型演示）

**职责：**

- 初始化 `QApplication` 与 `WindowManager`。
- 注入 `Live2DController` 作为 AvatarController。
- 初始化 `AgentController` 并连接 LLM（Ollama）。
- 监听用户消息，通过 `AgentWorker` 线程调用 `AgentController.chat()` / `chat_test()`。
- **管理会话**：监听 `chat_session_changed`，更新 AgentController 的 `session_id`。
- **迷你聊天**：监听 `mini_chat_input_sent`，通过 `AgentWorker(mini_chat=True)` 调用 Agent，回复通过 `mini_chat_reply_received` 显示在角色头顶气泡。
- **系统提示**：AgentController 启动时 `APIConnect()` 返回的消息（如"连接成功了！"）延迟 800ms 自动显示在迷你聊天气泡。

---

#### 🧵 `AgentWorker`（QThread）

`main.py` 中定义的工作线程，封装 `AgentController.chat()` 的同步调用。

> 📝 **设计说明：**
> - `AgentController.chat()` 内部调用 LangGraph invoke，是同步阻塞的，不能在主线程调用。
> - 通过 `QThread` 在后台执行，完成后通过 `reply_ready` 信号把 `AgentMessage` 发回主线程。
> - `mini_chat` 参数控制思考信号路由：
>   - `mini_chat=True` → 发射 `mini_chat_thinking_started`（角色头顶气泡）
>   - `mini_chat=False` → 发射 `agent_thinking_started`（大聊天窗口）
> - `agent_thinking_finished` **仅在大聊天模式**发射，避免迷你聊天污染 ChatWindow 状态。
> - `configurable` 参数允许为不同会话指定不同的 `session_id`。

**🔑 关键接口：**

| 接口 | 说明 |
| :--- | :--- |
| `__init__(agent_controller, user_text, mini_chat=False, configurable=None)` | 初始化工作线程 |
| `run()` | 执行 `chat_test()` 调用，发射思考信号与 `reply_ready` |
| `reply_ready(AgentMessage)` | chat() 完成后发射，携带回复结果 |

---

#### 🗂️ 会话管理架构

```text
┌─────────────────────────────────────────────────────────────┐
│                    AgentController                          │
│  configurable = {"user_id": "default-user",                │
│                  "session_id": "a1b2c3d4"}  ← 当前会话      │
└─────────────────────────────────────────────────────────────┘
        ▲                          ▲
        │ chat(text, configurable) │ chat(text, configurable=
        │                          │   {session_id:"mini-chat"})
        │                          │
┌───────┴──────────┐    ┌─────────┴──────────┐
│  AgentWorker     │    │  AgentWorker        │
│  (大聊天模式)     │    │  (mini_chat=True)   │
│  session_id 由   │    │  session_id 固定为   │
│  ChatWindow 管理  │    │  "mini-chat"        │
└──────────────────┘    └────────────────────┘
        ▲                          ▲
        │ user_message_sent        │ mini_chat_input_sent
        │                          │
┌───────┴──────────┐    ┌─────────┴──────────┐
│  ChatWindow       │    │  MiniChatOverlay   │
│  新建/切换会话时   │    │  (角色右下角💬按钮)  │
│  emit             │    │                    │
│  chat_session_    │    │                    │
│  changed(s_id)    │    │                    │
└──────────────────┘    └────────────────────┘
```

> 📌 **会话隔离规则：**
> 1. **大聊天窗口**：每个会话有独立的 UUID `session_id`，新建/切换时通过 `chat_session_changed` 信号通知 `main.py` 更新 `AgentController.configurable["session_id"]`。
> 2. **迷你聊天**：使用固定 `session_id="mini-chat"`，在 `AgentWorker.__init__` 中传入 `configurable={"session_id": "mini-chat"}`，不修改全局 `AgentController.configurable`。
> 3. **系统提示**：`init_agent_controller()` 中 `APIConnect()` 返回的消息保存到 `_startup_message`，`manager.run()` 后通过 `QTimer.singleShot(800, ...)` 延迟发射 `mini_chat_reply_received`。

---

**`main.py` 中的关键函数：**

| 函数 | 职责 |
| :--- | :--- |
| `on_user_message(text)` | 大聊天消息处理：创建 `AgentWorker`，回复走 `agent_reply_received` |
| `on_mini_chat_message(text)` | 迷你聊天消息处理：创建 `AgentWorker(mini_chat=True, configurable={session_id:"mini-chat"})`，回复走 `mini_chat_reply_received` |
| `_on_agent_reply(agent_message)` | 大聊天回复：包装为 `AgentEvent`，发射 `agent_reply_received` + 状态栏更新 |
| `_on_mini_chat_reply(agent_message)` | 迷你聊天回复：提取文本，发射 `mini_chat_reply_received` |
| `on_chat_session_changed(session_id)` | 会话切换：更新 `AgentController.configurable["session_id"]` |
| `init_agent_controller()` | 初始化 AgentController + 连接 LLM，保存系统提示到 `_startup_message` |
| `main()` | 入口：创建 WindowManager + AvatarController + AgentController，连接事件，延迟显示系统提示 |

---

## 4. 🔧 如何扩展新功能

### 4.1 🪟 新增一个窗口

**步骤：**

1. 在 `windows/` 下新建文件，例如 `windows/about_window.py`
2. 继承 `BaseWindow`：

```python
from windows.base_window import BaseWindow

class AboutWindow(BaseWindow):
    def setup_ui(self) -> None:
        # 创建窗口内部 UI
        pass

    def connect_signals(self) -> None:
        # 连接内部信号与 EventBus
        pass
```

3. 在 `WindowManager.__init__()` 中创建实例：

```python
self._about_window = AboutWindow()
```

4. 在 `WindowManager._setup_event_routing()` 中订阅事件：

```python
event_bus.show_about_window_requested.connect(self._about_window.show_window)
```

5. 在 `core/event_bus.py` 中添加信号：

```python
show_about_window_requested = Signal()
```

6. 在需要触发的地方发射信号：

```python
event_bus.show_about_window_requested.emit()
```

---

### 4.2 🧩 新增一个可复用组件

**步骤：**

1. 在 `widgets/` 下合适子目录新建文件，例如 `widgets/common/status_badge.py`
2. 继承 `BaseWidget`：

```python
from widgets.base.base_widget import BaseWidget

class StatusBadge(BaseWidget):
    def setup_ui(self) -> None:
        self._label = QLabel(self)
        # ...

    def connect_signals(self) -> None:
        pass

    def set_status(self, text: str, color: str) -> None:
        self._label.setText(text)
        self._label.setStyleSheet(f"color: {color};")
```

3. 在窗口的 `setup_ui()` 中实例化并加入布局。

---

### 4.3 🍔 新增一个右键菜单项

> 以新增"关于"菜单项为例，说明可扩展机制。

#### ✅ 方案 A：使用预定义类型（推荐，通用可复用）

1. 在 `widgets/menu/menu_item.py` 的 `MenuItemType` 中新增类型：

```python
class MenuItemType(Enum):
    HOME = auto()
    SETTINGS = auto()
    ABOUT = auto()      # 新增
    QUIT = auto()
    SEPARATOR = auto()
    CUSTOM = auto()
```

2. 在 `MenuItem.on_triggered()` 中处理新类型：

```python
elif self.item_type == MenuItemType.ABOUT:
    event_bus.menu_about_requested.emit()
    event_bus.show_about_window_requested.emit()
```

3. 在 `widgets/menu/menu_builder.py` 中新增构建方法：

```python
def add_about(
    self,
    title: str = "关于",
    icon: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> "MenuBuilder":
    self._configs.append(
        (
            MenuItemType.ABOUT,
            {"title": title, "icon": icon, "callback": callback},
        )
    )
    return self
```

并在 `build()` 的 `if/elif` 链中增加 `MenuItemType.ABOUT` 分支。

4. 在 `core/event_bus.py` 中新增信号：

```python
menu_about_requested = Signal()
show_about_window_requested = Signal()
```

5. 在 `WindowManager._setup_event_routing()` 中连接：

```python
event_bus.show_about_window_requested.connect(self._show_about)
```

并实现 `_show_about()` 方法。

6. 在 `LoverWindow.setup_ui()` 中使用：

```python
self._context_menu = (
    MenuBuilder()
    .add_home("主页")
    .add_settings("设置")
    .add_about("关于")
    .add_separator()
    .add_quit("退出")
    .build(parent=self)
)
```

---

#### 🔧 方案 B：使用自定义项 + callback（适合一次性、局部逻辑）

如果某个菜单项只有当前窗口用，不需要全局事件：

```python
def on_about_clicked() -> None:
    print("关于被点击")
    # 或者：event_bus.show_about_window_requested.emit()

self._context_menu = (
    MenuBuilder()
    .add_home("主页")
    .add_settings("设置")
    .add_separator()
    .add_custom("menu_about", "关于", callback=on_about_clicked)
    .add_quit("退出")
    .build(parent=self)
)
```

`MenuItem` 会执行 `callback()`，同时发送 `menu_item_triggered("menu_about", {...})`。

---

### 4.4 ⚙️ 新增一个设置项

**步骤：**

1. 如果现有类型（开关/文本/滑块/下拉）不满足，在 `widgets/settings/setting_item.py` 中继承 `SettingItem`：

```python
class ColorSettingItem(SettingItem):
    """颜色选择设置项（示例）。"""

    def create_editor(self, parent: QWidget) -> QWidget:
        self._button = QPushButton("选择颜色", parent)
        self._button.clicked.connect(self._on_pick_color)
        return self._button

    def _update_editor(self, value: Any) -> None:
        self._button.setStyleSheet(f"background-color: {value};")

    def _on_pick_color(self) -> None:
        # 弹出颜色选择对话框，然后调用 self.on_value_changed(color)
        pass
```

2. 在 `SettingWindow.add_default_settings()` 或运行时添加：

```python
self.add_setting_item(
    ColorSettingItem(
        key="theme_color",
        label="主题颜色",
        default_value="#7c3aed",
    )
)
```

3. 监听 `event_bus.setting_changed` 即可响应变化：

```python
event_bus.setting_changed.connect(self._on_setting_changed)

def _on_setting_changed(self, key: str, value: Any) -> None:
    if key == "theme_color":
        self._apply_theme_color(value)
```

---

### 4.5 📡 新增一个 EventBus 信号

**步骤：**

1. 在 `core/event_bus.py` 的 `EventBus` 类中新增信号：

```python
# 用户请求切换模型
model_switch_requested = Signal(str)
```

2. 在发送方调用：

```python
event_bus.model_switch_requested.emit("rem")
```

3. 在接收方连接：

```python
event_bus.model_switch_requested.connect(self._on_model_switch)
```

---

### 4.6 🗣️ 新增一个聊天会话（session_id 隔离）

> 以新增一个"语音对话"会话为例，说明会话隔离机制。

#### 第一步：确定 session_id

每个会话需要唯一的 `session_id`。可以是 UUID 或固定名称：

```python
# 固定名称（类似迷你聊天的 "mini-chat"）
session_id = "voice-chat"

# 或动态 UUID（类似 ChatWindow 的新建会话）
import uuid
session_id = uuid.uuid4().hex[:8]
```

#### 第二步：在发送消息时传入 configurable

在 `main.py` 中创建 `AgentWorker` 时，传入 `configurable` 指定 `session_id`：

```python
worker = AgentWorker(
    _agent_controller,
    text,
    mini_chat=True,  # 或自定义模式
    configurable={
        "user_id": "default-user",
        "session_id": "voice-chat",
    },
)
```

这样 `AgentController.chat()` 会使用指定的 `session_id`，与其他会话的记忆隔离。

#### 第三步：（可选）如果会话由 UI 窗口管理

如果新会话由某个窗口（类似 ChatWindow）管理切换，需要：

1. 在 `core/event_bus.py` 中复用 `chat_session_changed` 信号或新增信号：

```python
voice_chat_session_changed = Signal(str)
```

2. 在窗口中切换会话时发射信号：

```python
event_bus.voice_chat_session_changed.emit(session_id)
```

3. 在 `main.py` 中监听并更新 `AgentController`：

```python
event_bus.voice_chat_session_changed.connect(on_voice_chat_session_changed)

def on_voice_chat_session_changed(session_id: str) -> None:
    if _agent_controller is not None:
        _agent_controller.configurable["session_id"] = session_id
```

---

## 5. 🚪 以"退出"为例说明完整扩展流程

> 下面回顾之前为"退出"菜单项新增 sys 退出的完整步骤，帮助理解可扩展机制。

### 5.1 ❌ 原来的问题

原来的代码用 `add_custom("menu_quit", "退出")`，类型是 `CUSTOM`。点击时只发送 `menu_item_triggered("menu_quit", {...})`，没有任何模块监听这个事件，所以点退出没有反应。

---

### 5.2 ✅ 改造为预定义类型 QUIT

#### 第一步：扩展枚举

在 `widgets/menu/menu_item.py` 的 `MenuItemType` 中增加：

```python
QUIT = auto()       # 退出应用
```

#### 第二步：定义触发行为

在 `MenuItem.on_triggered()` 中增加：

```python
elif self.item_type == MenuItemType.QUIT:
    event_bus.menu_quit_requested.emit()
    event_bus.application_quit_requested.emit()
```

> 📌 这里同时发射了两个信号：
> - `menu_quit_requested()`：留给业务层做额外处理（如记录日志、保存状态）
> - `application_quit_requested()`：触发真正的退出流程

#### 第三步：增加构建器方法

在 `widgets/menu/menu_builder.py` 中增加：

```python
def add_quit(
    self,
    title: str = "退出",
    icon: Any | None = None,
    callback: Callable[[], None] | None = None,
) -> "MenuBuilder":
    self._configs.append(
        (
            MenuItemType.QUIT,
            {"title": title, "icon": icon, "callback": callback},
        )
    )
    return self
```

并在 `build()` 中增加 `elif item_type == MenuItemType.QUIT` 分支，生成 `item_id="menu_quit"` 的 `MenuItem`。

#### 第四步：使用新的构建方法

在 `windows/lover_window.py` 中：

```python
self._context_menu = (
    MenuBuilder()
    .add_home("主页")
    .add_settings("设置")
    .add_separator()
    .add_quit("退出")      # 原来是 .add_custom("menu_quit", "退出")
    .build(parent=self)
)
```

#### 第五步：确认退出执行

`WindowManager._setup_event_routing()` 中本来就有：

```python
event_bus.application_quit_requested.connect(self.quit)
```

而 `WindowManager.quit()`：

```python
def quit(self) -> None:
    """退出应用。"""
    self._app.quit()
```

所以点击"退出"后，最终调用 `QApplication.quit()`，完成应用退出。

---

### 5.3 🤔 为什么不直接 `sys.exit()`

> - `sys.exit()` 会立即终止进程，Qt 窗口、OpenGL 上下文、音频设备等可能来不及释放。
> - `QApplication.quit()` 会进入正常的事件循环退出流程，触发所有对象的析构，更安全。
> - 如果一定要在退出前执行额外逻辑（如保存配置），可以连接 `application_quit_requested` 信号做预处理，最后再调用 `app.quit()`。

---

## 6. 📜 开发约定

| # | 📋 约定内容 |
| :--- | :--- |
| 1 | **中文注释**：所有组件、窗口、暴露接口、关键逻辑必须写中文注释，特别是组件功能和暴露接口 |
| 2 | **解耦**：窗口之间不直接调用，必须通过 EventBus |
| 3 | **预留接口**：未实现的功能用 `# TODO:` 标记，并暴露清晰的接口供后续填充 |
| 4 | **目录规范**：窗口代码放 `windows/`，可复用组件放 `widgets/`，通用组件接口放 `widgets/base/` |
| 5 | **Avatar 解耦**：`LoverWindow` 不直接依赖 Live2D，所有 Avatar 交互通过 `AvatarControllerProtocol` |

---

## 7. 🗂️ 快速参考：常用文件对应关系

| 🎯 需求 | 📁 需要修改的文件 |
| :--- | :--- |
| 新增窗口 | `windows/xxx_window.py`、`windows/window_manager.py`、`core/event_bus.py` |
| 新增组件 | `widgets/xxx/xxx.py`、在窗口 `setup_ui()` 中使用 |
| 新增右键菜单项 | `widgets/menu/menu_item.py`、`widgets/menu/menu_builder.py`、`windows/lover_window.py`、`core/event_bus.py` |
| 新增设置项类型 | `widgets/settings/setting_item.py` |
| 新增设置项实例 | `windows/setting_window.py` |
| 新增全局事件 | `core/event_bus.py` |
| 调整 Avatar 交互 | `avatar/avatar_controller_protocol.py`、`avatar/controller.py`（具体 `AvatarController` 实现） |
| 迷你聊天（快速对话） | `windows/mini_chat_overlay.py`、`widgets/mini_chat/speech_bubble.py`、`core/event_bus.py`、`main.py` |
| 会话管理（session_id 隔离） | `windows/chat_window.py`（emit `chat_session_changed`）、`core/event_bus.py`（信号）、`main.py`（`on_chat_session_changed` 更新 AgentController） |
| AgentWorker 思考信号路由 | `main.py`（`AgentWorker.__init__` 的 `mini_chat` 参数 + `run()` 中条件发射） |
| 系统提示自动显示 | `main.py`（`init_agent_controller` 保存 `_startup_message` + `main()` 中 `QTimer.singleShot` 延迟发射） |
| 浮层 z-order 跟随 | `windows/mini_chat_overlay.py`（`_on_target_moved` 中 `self.raise_()`） |
| 运行真实应用 | `main.py` |
| 运行 UI 原型演示 | `demos/desktop_ui_demo.py` |

---
