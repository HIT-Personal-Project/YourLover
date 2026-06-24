from sqlalchemy import Column, String, Text, JSON, DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    memory_type = Column(String(20), nullable=False)  # working/short/long/episodic
    content = Column(Text, nullable=False)
    embedding = Column(LargeBinary)
    metadata = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    accessed_at = Column(DateTime, nullable=False, default=datetime.now)
