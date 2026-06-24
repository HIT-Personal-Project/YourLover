from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict

class ChatRequest(BaseModel):
    user_id: UUID
    message: str
    message_type: str = "text"
    voice_data: Optional[str] = None
    session_id: Optional[UUID] = None

class ChatResponse(BaseModel):
    response_id: str
    user_id: UUID
    session_id: str
    message: str
    message_type: str = "text"
    voice_data: Optional[str] = None
    emotion: Dict[str, float]
    timestamp: str
