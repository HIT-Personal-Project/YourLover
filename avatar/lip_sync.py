"""
Avatar口型同步模块
负责：
- 实现语音驱动的口型同步
- 分析音频数据
- 生成口型参数
- 同步音频播放和口型动画

事件流：
    Agent -> TTS -> AudioPlayer -> Avatar.start_speaking() -> lip_sync -> 播放结束 -> Avatar.stop_speaking()
"""