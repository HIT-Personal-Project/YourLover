from enum import Enum




class EmotionEnum(Enum):
    """人物情感枚举, 用于表示人物当前的情感状态"""
    Happy = "Happy"
    Sad = "Sad"
    Angry = "Angry"
    Shy = "Shy"


class ActionEnum(Enum):
    """人物动作枚举, 用于表示人物当前的动作状态"""
    Idle = "Idle"
    Thinking = "Thinking"
    Listening = "Listening"
    Speaking = "Speaking"
    Happy = "Happy"
    Sad = "Sad"
    Shy = "Shy"
    ToolUsing = "ToolUsing"
    Sleep = "Sleep"
