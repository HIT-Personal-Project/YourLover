from app.skills.base_skill import BaseSkill
from typing import Dict

class DailyGreetingSkill(BaseSkill):
    name = "daily_greeting"
    trigger = ["早安", "晚安", "早上好", "晚上好", "早安呀", "晚安啦"]
    priority = 1
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "早安呀~今天也要元气满满哦！", "skill": self.name}
