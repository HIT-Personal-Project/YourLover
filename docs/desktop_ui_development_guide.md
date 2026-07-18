# YourLover 桌面 UI 开发指南

本文档说明桌面端（悬浮宠物 + 聊天主页 + 设置面板）的整体架构、事件总线机制、各组件/窗口职责，以及如何在此基础上扩展新功能。

---

## 1. 整体架构概览

桌面 UI 采用**组件化 + 事件总线**架构，目标是把窗口、控件、业务逻辑彻底解耦：

- `windows/`：放置所有顶层窗口（悬浮窗、聊天窗、设置窗）。
- `widgets/`：放置可复用组件（聊天组件、右键菜单、设置项等）。
- `core/event_bus.py`：全局事件总线，所有跨模块通信都通过它。
- `demos/desktop_ui_demo.py`：可运行的演示入口，用假 Avatar 验证 UI 流程。

### 1.1 核心设计原则

1. **窗口之间不直接互相调用**。例如 `LoverWindow` 不会直接 `chat_window.show()`，而是发射 EventBus 信号。
2. **组件只负责自身 UI 与内部信号**。例如 `ChatInput` 只会在用户点击发送时发射 `send_clicked(text)`，不直接调用 Agent。
3. **WindowManager 是唯一的窗口协调者**。它订阅 EventBus，把事件分发给对应窗口。
4. **Avatar 相关逻辑通过 `AvatarControllerProtocol` 解耦**。`LoverWindow` 只负责容器和原始鼠标事件，具体 Live2D 渲染交给实现协议的控制器。

---

## 2. 事件总线（EventBus）机制

### 2.1 什么是 EventBus

`core/event_bus.py` 中定义了一个全局单例 `event_bus`，它继承自 `QObject`，内部使用 PySide6 的 `Signal` 定义所有跨模块事件。

任何模块都可以通过以下方式通信：

```python
from core.event_bus import event_bus

# 发送事件
event_bus.show_chat_window_requested.emit()

# 接收事件
event_bus.show_chat_window_requested.connect(on_show_chat)
```

### 2.2 信号传递流程

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

以**点击右键菜单的"退出"**为例：

```text
用户点击"退出"
    ↓
QAction.triggered
    ↓
MenuItem.on_triggered()
    ↓
event_bus.application_quit_requested.emit()
    ↓
WindowManager._setup_event_routing() 中已连接：
    event_bus.application_quit_requested.connect(self.quit)
    ↓
WindowManager.quit() → self._app.quit()
```

注意：**没有直接调用 `sys.exit()`**。`WindowManager.quit()` 调用的是 `QApplication.quit()`，这样 Qt 能正常清理资源、关闭窗口、释放对象。

### 2.3 典型事件流程示例

#### 示例 A：右键点击"主页"

```text
LoverWindow 右键菜单 → MenuItem(HOME).on_triggered()
    → event_bus.menu_home_requested.emit()
    → event_bus.show_chat_window_requested.emit()
        → WindowManager.show_chat() 显示 ChatWindow
```

#### 示例 B：用户发送消息

```text
ChatInput._on_send()
    → send_clicked.emit(text)
    → ChatWindow.connect_signals() 中：
        self._input.send_clicked.connect(event_bus.user_message_sent.emit)
    → event_bus.user_message_sent.emit(text)
        → ChatWindow.append_user_message(text) 显示到历史
        → desktop_ui_demo.on_user_message(text) 启动模拟 Agent 回复线程
```

#### 示例 C：Agent 流式回复

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

### 2.4 当前 EventBus 信号分类

| 分类 | 信号 | 说明 |
|------|------|------|
| Avatar 交互 | `avatar_clicked(x, y)` | Avatar 区域被点击 |
| | `avatar_hit_area_clicked(area_name)` | 命中 HitArea |
| | `avatar_dragged(dx, dy)` | 拖拽中 |
| | `avatar_drag_finished(x, y)` | 拖拽结束 |
| | `avatar_shaken()` | 检测到摇晃 |
| | `avatar_state_changed(state)` | Avatar 状态变化 |
| 菜单/导航 | `menu_home_requested()` | 请求主页 |
| | `menu_settings_requested()` | 请求设置 |
| | `menu_quit_requested()` | 请求退出 |
| | `menu_item_triggered(id, payload)` | 通用菜单项触发 |
| 聊天 | `user_message_sent(text)` | 用户发送消息 |
| | `agent_reply_received(event)` | Agent 完整回复 |
| | `agent_stream_chunk(chunk)` | 流式片段 |
| | `agent_thinking_started/finished()` | Agent 思考状态 |
| 设置 | `setting_changed(key, value)` | 单个设置项变化 |
| | `settings_batch_changed(values)` | 批量设置变化 |
| | `settings_save_requested()` | 请求保存设置 |
| 窗口管理 | `show_chat_window_requested()` | 显示聊天窗 |
| | `hide_chat_window_requested()` | 隐藏聊天窗 |
| | `show_setting_window_requested()` | 显示设置窗 |
| | `hide_setting_window_requested()` | 隐藏设置窗 |
| | `hide_all_secondary_windows_requested()` | 隐藏所有二级窗口 |
| | `application_quit_requested()` | 请求退出应用 |

---

## 3. 组件与窗口职责

### 3.1 windows/ 目录

#### `base_window.py`

所有窗口的抽象基类 `BaseWindow`（继承 `QMainWindow`）。

- 统一窗口生命周期：`show_window()`、`hide_window()`、`toggle()`。
- 子类必须实现 `setup_ui()` 和 `connect_signals()`。
- 默认 `closeEvent` 改为隐藏而非退出。

#### `lover_window.py`

**虚拟伴侣悬浮窗口** `LoverWindow`。

- 无边框、透明、置顶悬浮。
- 承载 Avatar 渲染控件（由外部注入）。
- 处理鼠标拖拽、摇晃检测。
- 右键弹出菜单（主页、设置、退出）。
- 管理 HitArea，把点击事件转发到 EventBus。
- 不负责具体 Live2D 渲染。

关键接口：

- `set_avatar_widget(widget)`：注入 Avatar 渲染控件。
- `register_hit_area(name, rect)`：注册可点击区域。
- `shake_avatar()`：触发摇晃动画（委托 AvatarController）。
- `on_avatar_clicked(pos)`：处理 Avatar 区域点击。

#### `chat_window.py`

**聊天主页窗口** `ChatWindow`（Claude Desk 风格）。

- **左右双栏布局**：左侧 `ChatSessionList`（会话列表），右侧 `ChatHeader` + `ChatHistory` + `ChatInput`。
- 把用户输入转发到 `user_message_sent`。
- 订阅 Agent 事件并更新历史记录。
- 顶部设置按钮打开设置面板。
- **管理会话**：新建、切换、删除会话；切换会话时恢复历史消息。
- 消息追加时自动保存到当前会话，并更新会话列表预览。

关键接口：

- `append_user_message(text)` / `append_agent_message(text)`：追加消息（同时保存到会话）。
- `update_last_agent_message(text)`：流式更新最后一条消息。
- `set_status(text, color)`：更新顶部状态。
- `create_new_session()`：新建会话。
- `switch_session(session_id)`：切换会话。
- `_on_session_clicked(session_id)`：会话被点击时恢复消息历史。
- `_on_session_deleted(session_id)`：删除会话。
- `_save_message_to_session(role, content)`：内部方法，保存消息到当前会话。

#### `setting_window.py`

**设置面板窗口** `SettingWindow`。

- 无边框、可从右侧滑入滑出。
- 动态管理设置项。
- 保存时广播 `settings_batch_changed` 和 `settings_save_requested`。

关键接口：

- `add_setting_item(item)`：添加设置项。
- `get_all_values()`：获取所有设置值。
- `save_settings()`：保存并隐藏。
- `slide_in(anchor)` / `slide_out()`：滑入滑出动画。

#### `window_manager.py`

**窗口管理器**。

- 创建并持有 `LoverWindow`、`ChatWindow`、`SettingWindow`。
- 订阅 EventBus，把事件路由到对应窗口。
- 注入 AvatarController 及其渲染控件。
- 管理窗口联动（如打开设置时定位在聊天窗旁边）。

关键接口：

- `run()`：显示悬浮窗。
- `quit()`：退出应用。
- `set_avatar_controller(controller)`：注入 AvatarController。
- `show_chat()` / `show_settings()`：显示二级窗口。

#### `avatar_controller_protocol.py`

定义 `AvatarControllerProtocol`，规定 Avatar 控制器必须实现的方法：

- `on_click(x, y)`：原始点击坐标。
- `on_hit_area(area_name)`：命中区域。
- `on_shake()`：摇晃手势。
- `on_drag(x, y)`：每帧鼠标跟随。
- `on_update()`：每帧模型更新。
- `play_motion(name)` / `change_expression(name)` / `set_state(name)`。
- `get_render_widget()`：返回渲染控件。

### 3.2 widgets/ 目录

#### `base/base_widget.py`

所有可复用组件的抽象基类 `BaseWidget`（继承 `QWidget`）。

- 子类必须实现 `setup_ui()` 和 `connect_signals()`。
- 可选重写 `refresh(data)` 和 `apply_style()`。

#### `base/extensible_item.py`

**可扩展列表项接口** `ExtensibleItem`。

- 统一右键菜单项、设置项等动态增删项的行为。
- 要求实现 `payload`、`create_widget()`、`on_triggered()`、`on_removed()`。
- `ItemPayload` 封装 `item_id`、`title`、`icon`、`extra`。

#### `menu/menu_builder.py`

**右键菜单构建器** `MenuBuilder`。

- 链式 API：`add_home()`、`add_settings()`、`add_quit()`、`add_custom()`、`add_separator()`。
- 最终调用 `build(parent)` 生成 `ContextMenu`。

#### `menu/menu_item.py`

**单个右键菜单项** `MenuItem`，实现 `ExtensibleItem`。

- 根据 `MenuItemType` 决定触发行为：
  - `HOME` → 发送 `menu_home_requested` + `show_chat_window_requested`。
  - `SETTINGS` → 发送 `menu_settings_requested` + `show_setting_window_requested`。
  - `QUIT` → 发送 `menu_quit_requested` + `application_quit_requested`。
  - `CUSTOM` → 只发送 `menu_item_triggered`，可额外传 `callback`。
- `create_widget()` 创建 `QAction`。

#### `menu/context_menu.py`

**右键菜单容器** `ContextMenu`。

- 管理一组 `MenuItem`。
- 提供 `add_item()`、`remove_item()`、`clear()`、`show_at(pos)`。
- 发射本地信号 `item_triggered(id, payload)`（可选使用）。

#### `chat/chat_header.py`

聊天窗口顶部栏。

- 显示头像、标题、状态。
- 提供设置按钮，点击发射 `settings_clicked`。
- 卡通游戏风：粉色头像底（圆形）、粉色边框、樱花 🌸 emoji 头像。

#### `chat/chat_session_list.py`

**左侧历史会话列表组件** `ChatSessionList`（含 `SessionItem` 和 `SessionData`）。

职责：
- 在聊天窗口左侧展示所有历史会话。
- 顶部"✨"按钮新建会话。
- 支持动态增删会话、切换选中、删除会话。
- 选中态使用粉色高亮 + 边框。
- hover 时显示删除按钮（红色圆形）。

关键接口：
- `add_session(data)`：添加会话。
- `remove_session(session_id)`：删除会话。
- `update_session(data)`：更新会话标题与预览。
- `select_session(session_id)`：选中会话。
- `clear()`：清空会话。
- `current_session_id()`：当前会话 ID。

信号：
- `session_clicked(session_id)`：会话被点击。
- `session_deleted(session_id)`：会话被请求删除。
- `new_session_requested()`：请求新建会话。

数据模型 `SessionData`：
- `session_id`：唯一标识。
- `title`：会话标题。
- `preview`：最后消息预览。
- `updated_at`：更新时间。
- `avatar`：会话头像 emoji。

`SessionItem`：
- 单个会话列表项（QFrame）。
- 显示头像、标题、预览。
- 点击发射 `clicked`，删除按钮发射 `delete_clicked`。
- 鼠标进入时显示删除按钮，离开时隐藏。

#### `chat/chat_history.py`

聊天历史记录面板。

- 维护 `ChatBubble` 列表。
- 支持追加消息、更新最后一条消息（流式）、清空历史。
- 自动滚动到底部。
- 卡通风：粉色细滚动条、暖白背景 `#fffafc`。

#### `chat/chat_bubble.py`

单条聊天气泡。

- **修复了一左一右问题**：通过 stretch 控制对齐，用户气泡靠右、Agent 气泡靠左。
- 卡通游戏风：
  - 用户消息：粉色 `#ec4899` 实底白字，圆角 18px，右下角小圆角（气泡尾巴效果）。
  - Agent 消息：白色卡片 + 粉色边框 `#fce7f3`，圆角 18px，左下角小圆角。
  - 系统消息：淡黄提示，居中。
- 暴露 `refresh(data)` 和 `set_content(text)`。

#### `chat/chat_input.py`

聊天输入区域。

- 多行文本输入 + 发送按钮。
- 支持 `Ctrl+Enter` 快捷键发送。
- 卡通风：粉色边框、聚焦时粉色加粗边框、发送按钮粉色三态色（hover/pressed/disabled）。
- 点击发送时发射 `send_clicked(text)`。

#### `settings/setting_panel.py`

设置项列表面板。

- 以滚动列表展示所有 `SettingItem`。
- 动态增删、批量取值/设值。
- 转发 `setting_changed` 为本地 `item_value_changed` 信号。

#### `settings/setting_item.py`

设置项抽象基类与具体实现：

- `SettingItem`：基类，封装 `key`、`label`、`value`。
  - 值变化时发送 `event_bus.setting_changed.emit(key, value)`。
  - 子类只需实现 `create_editor()` 和 `_update_editor()`。
- `ToggleSettingItem`：开关（布尔）。
- `TextSettingItem`：文本输入。
- `SliderSettingItem`：整数滑块/数值框。
- `OptionSettingItem`：下拉选项。

### 3.3 core/ 目录

#### `event_bus.py`

全局事件总线，定义所有 Signal。

#### `agent_event.py`

`AgentEvent` 数据类，统一 Agent 相关事件的载荷格式。

---

## 4. 如何扩展新功能

### 4.1 新增一个窗口

步骤：

1. 在 `windows/` 下新建文件，例如 `windows/about_window.py`。
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

### 4.2 新增一个可复用组件

步骤：

1. 在 `widgets/` 下合适子目录新建文件，例如 `widgets/common/status_badge.py`。
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

### 4.3 新增一个右键菜单项

以新增"关于"菜单项为例，说明可扩展机制。

#### 方案 A：使用预定义类型（推荐，通用可复用）

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

#### 方案 B：使用自定义项 + callback（适合一次性、局部逻辑）

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

### 4.4 新增一个设置项

步骤：

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

### 4.5 新增一个 EventBus 信号

步骤：

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

## 5. 以"退出"为例说明完整扩展流程

下面回顾之前为"退出"菜单项新增 sys 退出的完整步骤，帮助理解可扩展机制。

### 5.1 原来的问题

原来的代码用 `add_custom("menu_quit", "退出")`，类型是 `CUSTOM`。点击时只发送 `menu_item_triggered("menu_quit", {...})`，没有任何模块监听这个事件，所以点退出没有反应。

### 5.2 改造为预定义类型 QUIT

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

这里同时发射了两个信号：

- `menu_quit_requested()`：留给业务层做额外处理（如记录日志、保存状态）。
- `application_quit_requested()`：触发真正的退出流程。

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

### 5.3 为什么不直接 `sys.exit()`

- `sys.exit()` 会立即终止进程，Qt 窗口、OpenGL 上下文、音频设备等可能来不及释放。
- `QApplication.quit()` 会进入正常的事件循环退出流程，触发所有对象的析构，更安全。
- 如果一定要在退出前执行额外逻辑（如保存配置），可以连接 `application_quit_requested` 信号做预处理，最后再调用 `app.quit()`。

---

## 6. 开发约定

1. **中文注释**：所有组件、窗口、暴露接口、关键逻辑必须写中文注释，特别是组件功能和暴露接口。
2. **解耦**：窗口之间不直接调用，必须通过 EventBus。
3. **预留接口**：未实现的功能用 `# TODO:` 标记，并暴露清晰的接口供后续填充。
4. **目录规范**：
   - 窗口代码放 `windows/`。
   - 可复用组件放 `widgets/`。
   - 通用组件接口放 `widgets/base/`。
5. **Avatar 解耦**：`LoverWindow` 不直接依赖 Live2D，所有 Avatar 交互通过 `AvatarControllerProtocol`。

---

## 7. 快速参考：常用文件对应关系

| 需求 | 需要修改的文件 |
|------|---------------|
| 新增窗口 | `windows/xxx_window.py`、`windows/window_manager.py`、`core/event_bus.py` |
| 新增组件 | `widgets/xxx/xxx.py`、在窗口 `setup_ui()` 中使用 |
| 新增右键菜单项 | `widgets/menu/menu_item.py`、`widgets/menu/menu_builder.py`、`windows/lover_window.py`、`core/event_bus.py` |
| 新增设置项类型 | `widgets/settings/setting_item.py` |
| 新增设置项实例 | `windows/setting_window.py` |
| 新增全局事件 | `core/event_bus.py` |
| 调整 Avatar 交互 | `windows/avatar_controller_protocol.py`、具体 `AvatarController` 实现 |
| 运行演示 | `demos/desktop_ui_demo.py` |
