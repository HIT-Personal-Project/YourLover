"""
AvatarController 协议
定义 LoverWindow 与 Avatar 控制器之间的交互契约。

设计说明：
- 本模块使用 typing.Protocol，不强制 AvatarController 继承特定基类。
- avatar 模块中的 AvatarController（如 Live2DController）只需实现以下方法即可被 WindowManager 接管。
- 所有交互仍通过 EventBus 触发，WindowManager 仅作为"适配层"将事件转发给控制器。

位置说明：
- 本协议文件属于 avatar 模块，定义的是 Avatar 控制器的接口契约。
- windows 模块（如 WindowManager）通过导入本协议进行类型注解，不产生循环依赖。
- 依赖方向：windows → avatar.avatar_controller_protocol（协议），avatar.controller → avatar.avatar_controller_protocol（实现）。
"""

from typing import Protocol


class AvatarControllerProtocol(Protocol):
    """Avatar 控制器协议。

    实现类应提供：
    - on_click(x, y): 处理原始点击（可调用 Live2D HitTest 精确命中）。
    - on_hit_area(area_name): 处理 LoverWindow 检测到的点击区域。
    - on_shake(): 处理摇晃手势。
    - on_drag_start(direction): 拖拽开始时触发，带初始方向（可播放被抓住的动画）。
    - on_drag_direction(direction): 拖拽过程中方向变化时触发。
    - on_drag_end(): 拖拽结束时触发（可播放放下的动画）。
    - play_motion(motion_name): 播放指定动作。
    - change_expression(expression_name): 切换表情。
    - set_state(state_name): 设置 Avatar 状态。
    - on_drag(x, y): 每帧鼠标跟随（视线/头部跟随）。
    - on_update(): 每帧模型更新。
    - get_render_widget(): 返回用于渲染的 QWidget。
    """

    def on_click(self, x: int, y: int) -> None:
        """当用户在 Avatar 渲染区域点击时调用（原始坐标）。

        说明：
        - 适用于 Live2D 自带 HitTest 的精确命中。
        - LoverWindow 会在未命中 QRect HitArea 时也发射此事件。

        Args:
            x: 相对于 Avatar 渲染控件的 x 坐标。
            y: 相对于 Avatar 渲染控件的 y 坐标。
        """
        ...

    def on_hit_area(self, area_name: str) -> None:
        """当用户点击到 LoverWindow 注册的 HitArea 时调用。

        Args:
            area_name: 区域名称，如 "head", "face", "body"。
        """
        ...

    def on_shake(self) -> None:
        """当检测到摇晃手势时调用。"""
        ...

    def on_drag_start(self, direction: str) -> None:
        """拖拽开始时调用（用户按住角色并发生定向移动后触发）。

        说明：
        - 可播放"被抓住"的动画/表情（如惊讶表情 + Tap 动作）。
        - 由 LoverWindow 在检测到定向移动后通过 EventBus 触发（非按下即触发）。
        - 快速点击不会触发此方法。

        Args:
            direction: 拖拽初始方向，"left" / "right" / "up" / "down"。
        """
        ...

    def on_drag_direction(self, direction: str) -> None:
        """拖拽过程中根据移动方向调用。

        说明：
        - 每次鼠标移动且发生拖拽时触发，参数为当前帧的主方向。
        - 可用于让角色朝拖拽方向倾斜、视线跟随等。

        Args:
            direction: 方向字符串，"left" / "right" / "up" / "down"。
        """
        ...

    def on_drag_end(self) -> None:
        """拖拽结束时调用（用户松开鼠标结束拖动）。

        说明：
        - 可播放"被放下"的动画/表情（如恢复 happy 表情 + Idle 动作）。
        - 仅在真正发生过拖拽时触发，快速点击不会触发。
        """
        ...

    def play_motion(self, motion_name: str) -> None:
        """播放指定动作。

        Args:
            motion_name: 动作名称，如 "shake", "tap", "idle"。
        """
        ...

    def change_expression(self, expression_name: str) -> None:
        """切换表情。

        Args:
            expression_name: 表情名称，如 "happy", "sad", "surprised"。
        """
        ...
    
    def clear_expression(self) -> None:
        ...

    def set_state(self, state_name: str) -> None:
        """设置 Avatar 状态。

        Args:
            state_name: 状态名称，如 "Idle", "Thinking", "Speaking"。
        """
        ...

    def on_drag(self, x: int, y: int) -> None:
        """每帧传入鼠标在渲染控件上的本地坐标，用于角色视线/头部跟随。

        说明：
        - 由 Avatar 渲染控件的定时器每帧调用。
        - 实现类中应对应调用 Live2D 的 model.Drag(x, y)。

        Args:
            x: 相对于 Avatar 渲染控件的 x 坐标。
            y: 相对于 Avatar 渲染控件的 y 坐标。
        """
        ...

    def on_update(self) -> None:
        """每帧调用一次，驱动 Avatar 内部状态更新。

        说明：
        - 由 Avatar 渲染控件的定时器在每帧调用。
        - 实现类中应对应调用 Live2D 的 model.Update()。
        """
        ...

    def get_render_widget(self):
        """返回 Avatar 渲染控件（QWidget）。"""
        ...
