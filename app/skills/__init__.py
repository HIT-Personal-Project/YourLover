from app.skills.base_skill import BaseSkill
from app.skills.daily_greeting import DailyGreetingSkill
from app.skills.emotional_support import EmotionalSupportSkill
from app.skills.study_assistant import StudyAssistantSkill
from app.skills.campus_info import CampusInfoSkill
from app.skills.mood_tracker import MoodTrackerSkill
from app.skills.dream_interpreter import DreamInterpreterSkill
from app.skills.joke_teller import JokeTellerSkill
from app.skills.music_recommend import MusicRecommendSkill

skills = [
    DailyGreetingSkill(),
    EmotionalSupportSkill(),
    StudyAssistantSkill(),
    CampusInfoSkill(),
    MoodTrackerSkill(),
    DreamInterpreterSkill(),
    JokeTellerSkill(),
    MusicRecommendSkill(),
]
