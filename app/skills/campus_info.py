from app.skills.base_skill import BaseSkill
from typing import Dict

class CampusInfoSkill(BaseSkill):
    name = "campus_info"
    trigger = ["课表", "食堂", "图书馆", "教学楼", "宿舍", "校园"]
    priority = 4
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "需要查校园信息吗？我可以帮你查课表、食堂菜单等", "skill": self.name}
