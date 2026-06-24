from app.skills.base_skill import BaseSkill
from typing import Dict

class EmotionalSupportSkill(BaseSkill):
    name = "emotional_support"
    trigger = ["难过", "伤心", "心情不好", "不开心", "郁闷", "烦躁"]
    priority = 2
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "抱抱你~有什么不开心的可以和我说哦，我一直在", "skill": self.name}
