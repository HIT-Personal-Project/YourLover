from sqlalchemy import Column, String, Integer, Float, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Persona(Base):
    __tablename__ = "personas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(50), nullable=False)
    age = Column(Integer)
    identity = Column(String(100))
    backstory = Column(String(500))
    personality = Column(JSON)
    speaking_style = Column(JSON)
    interests = Column(JSON)
    evolution_rate = Column(Float, default=0.1)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
