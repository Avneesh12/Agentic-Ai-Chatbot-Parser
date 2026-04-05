from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.database import Base
from pydantic import BaseModel


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, nullable=True)   # optional
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(String, nullable=False)  # RAG / LLM
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatResponse(BaseModel):
    question: str
    answer: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True