import re
from collections import namedtuple

MessageAndEmotion = namedtuple("MessageAndEmotion",["message","emotion"])

def extract_emotion(text):
    """
    从字符串中提取所有 <<...>> 内的内容，并移除这些标记。
    返回 (清理后的消息, 特殊字符列表)
    """
    # 查找所有 {{...}} 中的内容（非贪婪匹配）
    emotion = re.findall(r'<<(.*?)>>', text)
    # 移除所有 {{...}} 及其内容，得到纯消息文本
    message = re.sub(r'<<.*?>>', '', text)
    # 清理多余空格（可选）
    message = message.strip()

    return MessageAndEmotion(message=message, emotion= emotion)

