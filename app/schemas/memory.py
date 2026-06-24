from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Dict

class MemoryCreate(BaseModel):
    user_id: UUID
    content: str
    memory_type: str
    metadata: Optional[Dict] = None

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict] = None
