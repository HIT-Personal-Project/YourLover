import edge_tts
import asyncio
from typing import Optional

class VoiceService:
    @staticmethod
    async def text_to_speech(text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> bytes:
        """文本转语音"""
        communicate = edge_tts.Communicate(text, voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes
    
    @staticmethod
    def speech_to_text(audio_data: bytes) -> str:
        """语音转文本"""
        pass
