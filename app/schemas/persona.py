from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional

class Personality(BaseModel):
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float

class SpeakingStyle(BaseModel):
    catchphrases: List[str]
    tone: str
    sentence_endings: List[str]

class PersonaCreate(BaseModel):
    user_id: UUID
    name: str
    age: Optional[int] = None
    identity: Optional[str] = None
    backstory: Optional[str] = None
    personality: Optional[Personality] = None
    speaking_style: Optional[SpeakingStyle] = None
    interests: Optional[List[str]] = None
    evolution_rate: float = 0.1

class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    identity: Optional[str] = None
    backstory: Optional[str] = None
    personality: Optional[Personality] = None
    speaking_style: Optional[SpeakingStyle] = None
    interests: Optional[List[str]] = None
