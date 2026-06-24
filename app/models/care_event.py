from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class CareEvent(Base):
    __tablename__ = "care_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    care_type = Column(String(20), nullable=False)  # timed/event/emotion/campus
    title = Column(String(100))
    content = Column(Text)
    trigger_time = Column(DateTime, nullable=False)
    repeat_type = Column(String(20), default="once")
    metadata = Column(JSON)
    status = Column(String(20), default="pending")  # pending/executed/cancelled
    created_at = Column(DateTime, nullable=False, default=datetime.now)
