from langchain.chat_models import QianwenChat
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import settings

class LLMService:
    def __init__(self):
        self.llm = QianwenChat(
            model_name=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY
        )
    
    def generate_response(self, prompt: str, persona: dict = None) -> str:
        """生成LLM响应"""
        messages = []
        if persona:
            system_prompt = f"你是{persona.get('name', '小哈')}，{persona.get('identity', '')}。性格特点：{persona.get('personality', {})}"
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))
        return self.llm(messages).content
