"""
Avatar控制器模块（AvatarController）
整个Live2D系统的唯一入口

负责：
- 管理Live2D模型的生命周期
- 提供统一的Avatar API接口
- 维护Avatar状态机（状态：Idle, Thinking, Listening, Speaking, Happy, Sad, ToolUsing, Sleep）

核心方法：
    avatar.play_motion(motion_name)
    avatar.change_expression(expression_name)
    avatar.look_at(x, y)
    avatar.start_speaking()
    avatar.stop_speaking()
    avatar.load_model(model_path)
    avatar.set_state(state_name)

重要：
- Agent永远不要直接调用live2d.playMotion()
- 必须通过AvatarController统一管理
- 所有动作播放通过状态机控制，避免到处调用play_motion()

状态流示例：
    Agent开始回复 -> avatar.set_state("Thinking")
    Agent回复完成 -> avatar.set_state("Speaking")
    TTS结束 -> avatar.set_state("Idle")
"""

from PySide6.QtWidgets import (
    QWidget,
)


import live2d.v3 as live2d

from core.config import settings, Settings  
from avatar.avatar_controller_protocol import AvatarControllerProtocol
from avatar.live2d import Live2D

from avatar.avatar_state import EmotionEnum


class Live2DController (AvatarControllerProtocol):
    """基于 live2d-py 的 AvatarController。

    实现 AvatarControllerProtocol，内部持有 Live2D。
    所有交互最终委托给 model。

    说明：
    - 本类通过结构化类型（Protocol 的鸭子类型机制）自动满足 AvatarControllerProtocol。
    - 不需要显式继承 Protocol，只要方法签名匹配即可。
    - WindowManager 通过 AvatarControllerProtocol 类型注解引用本类，实现解耦。
    """

    def __init__(self,settings: Settings) -> None:
        """初始化 Controller。

        Args:
            model_path: model3.json 路径。
        """
        # 注意：创建 widget 时不会立即加载模型，模型加载在 initializeGL 中
        self._render_widget = Live2D(settings)

    @property
    def model(self) -> live2d.LAppModel | None:
        """返回 Live2D 模型实例（可能为 None，在 initializeGL 完成前）。"""
        return self._render_widget.model

    def get_render_widget(self) -> QWidget:
        """返回 Avatar 渲染控件。"""
        return self._render_widget


    def on_click(self, x: int, y: int) -> None:
        """处理原始点击坐标（可调用 Live2D HitTest）。"""
        print(f"[Live2DAvatarController] 原始点击: ({x}, {y})")
        # TODO: 这里可以调用 self.model.HitTest("head", x, y) 检测命中部位

    def on_hit_area(self, area_name: str) -> None:
        """处理不同部位点击。"""
        print(f"[Live2DAvatarController] 点击部位: {area_name}")
        # if area_name == "head":
        self.play_motion("Tap")
            # self.change_expression("happy")
        # elif area_name == "body":
        #     self.play_motion("Tap@Body")

    def on_shake(self) -> None:
        """处理摇晃。"""
        print("[Live2DAvatarController] 检测到摇晃")
        self.play_motion("Shake",live2d.MotionPriority.FORCE)

    def on_drag_start(self, direction: str) -> None:
        """拖拽开始：播放被抓住的动画 + 惊讶表情。

        Args:
            direction: 拖拽初始方向 "left"/"right"/"up"/"down"。
        """
        print(f"[Live2DAvatarController] 拖拽开始(方向:{direction}) → 被抓住动画")
        self.play_motion("Move")


    def on_drag_end(self) -> None:
        """拖拽结束：播放放下的动画 + 恢复 happy 表情。"""
        print("[Live2DAvatarController] 拖拽结束 → 恢复待机")
        self.play_motion("Idle")

    def on_drag(self, x: int, y: int) -> None:
        """每帧鼠标跟随（视线/头部跟随）。

        Args:
            x: 相对于渲染控件的 x 坐标。
            y: 相对于渲染控件的 y 坐标。
        """
        if self.model:
            self.model.Drag(x, y)

    def on_update(self) -> None:
        """每帧模型更新。"""
        if self.model:
            self.model.Update()


    def play_motion(self, motion_name: str, priority= None) -> None:
        """播放指定动作组中的随机动作。"""
        if self.model:
            if priority == None:
                priority = live2d.MotionPriority.NORMAL
            try:
                self.model.StartRandomMotion(
                    motion_name, priority
                )
            except Exception as e:
                print(f"[Live2DAvatarController] 动作播放失败 {motion_name}: {e}")


    ############ 说话功能 ###########
    def speak(self, motion = None)->None:
        try:
            if motion:
                # print(motion)
                if motion == "Shy":
                    self.model.StartMotion("Speak",0)

                elif motion == "Sad":
                    print("run sad emotion")
                    self.model.StartMotion("Speak",1)

                elif motion == "Happy":
                    self.model.StartMotion("Speak",2)
            else:
                # self.play_motion("Speak",live2d.MotionPriority.FORCE)
                pass
        except Exception as e:
            print(f"[Live2DAvatarController] 说话动画播放失败 {motion}: {e}")
    def change_expression(self, expression_name: str) -> None:
        """切换表情。"""
        expression_name = expression_name
        if self.model:
            try:
                self.model.SetExpression(expression_name)
            except Exception as e:
                print(f"[Live2DAvatarController] 表情切换失败 {expression_name}: {e}")

    def clear_expression(self) -> None:
        self._render_widget.clear_expression()

    def set_state(self, state_name: str) -> None:
        """设置 Avatar 状态（预留接口）。"""
        # TODO: 接入状态机
        print(f"[Live2DAvatarController] 设置状态: {state_name}")
        self._render_widget.state = state_name
        if state_name == "Happy":
            self.clear_expression()
        self.change_expression(state_name)

    