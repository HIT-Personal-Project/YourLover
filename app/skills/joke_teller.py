from app.skills.base_skill import BaseSkill
from typing import Dict

class JokeTellerSkill(BaseSkill):
    name = "joke_teller"
    trigger = ["笑话", "开心一下", "搞笑", "幽默"]
    priority = 7
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "好的！我来讲个冷笑话：程序员的头发为什么越来越少？因为他们一直在debug！", "skill": self.name}
