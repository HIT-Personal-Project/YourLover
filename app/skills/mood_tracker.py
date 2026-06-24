from app.skills.base_skill import BaseSkill
from typing import Dict

class MoodTrackerSkill(BaseSkill):
    name = "mood_tracker"
    trigger = ["记录心情", "今天心情", "心情怎么样", "心情记录"]
    priority = 5
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "今天心情怎么样呀？我来帮你记录~", "skill": self.name}
