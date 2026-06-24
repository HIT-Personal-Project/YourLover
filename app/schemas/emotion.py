from pydantic import BaseModel
from typing import Optional

class EmotionAnalysisRequest(BaseModel):
    text: Optional[str] = None
    audio_data: Optional[str] = None
