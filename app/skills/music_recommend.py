from app.skills.base_skill import BaseSkill
from typing import Dict

class MusicRecommendSkill(BaseSkill):
    name = "music_recommend"
    trigger = ["推荐音乐", "想听音乐", "歌单", "音乐"]
    priority = 8
    
    def can_handle(self, context: Dict) -> bool:
        text = context.get("text", "").lower()
        return any(keyword in text for keyword in self.trigger)
    
    def execute(self, context: Dict) -> Dict:
        return {"response": "想听什么类型的音乐呀？我来帮你推荐~", "skill": self.name}
