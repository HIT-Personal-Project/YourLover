from app.skills.base_skill import BaseSkill
from typing import Dict

class StudyAssistantSkill(BaseSkill):
    name = "study_assistant"
    trigger = ["学习", "作业", "考试", "复习", "功课", "论文"]
    priority = 3
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "学习加油哦！需要我帮你整理知识点吗？", "skill": self.name}
