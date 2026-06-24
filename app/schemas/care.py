from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class CareEventCreate(BaseModel):
    user_id: UUID
    care_type: str
    title: str
    content: str
    trigger_time: datetime
    repeat_type: str = "once"
