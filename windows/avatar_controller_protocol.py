"""
AvatarController 协议
定义 LoverWindow 与 Avatar 控制器之间的交互契约。

设计说明：
- 本模块使用 typing.Protocol，不强制 AvatarController 继承特定基类。
- avatar 模块中的 AvatarController 只需实现以下方法即可被 WindowManager 接管。
- 所有交互仍通过 EventBus 触发，WindowManager 仅作为“适配层”将事件转发给控制器。
"""

from typing import Protocol


class AvatarControllerProtocol(Protocol):
    """Avatar 控制器协议。

    实现类应提供：
    - on_click(x, y): 处理原始点击（可调用 Live2D HitTest 精确命中）。
    - on_hit_area(area_name): 处理 LoverWindow 检测到的点击区域。
    - on_shake(): 处理摇晃手势。
    - play_motion(motion_name): 播放指定动作。
    - change_expression(expression_name): 切换表情。
    - set_state(state_name): 设置 Avatar 状态。
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
