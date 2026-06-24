from app.skills.base_skill import BaseSkill
from typing import Dict

class DreamInterpreterSkill(BaseSkill):
    name = "dream_interpreter"
    trigger = ["解梦", "梦见", "做梦", "梦境"]
    priority = 6
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "梦见什么啦？说来听听，我帮你分析分析~", "skill": self.name}
