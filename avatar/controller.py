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