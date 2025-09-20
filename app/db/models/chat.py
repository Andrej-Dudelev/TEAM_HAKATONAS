import uuid
import enum
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, ForeignKey, JSON, Enum as SQLAlchemyEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class ResponseSourceLayer(enum.Enum):
    QA = "QA"
    RAG = "RAG"
    GENERAL = "GENERAL"

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
    response_details = relationship("MessageResponse", uselist=False, back_populates="message", cascade="all, delete-orphan")

class MessageResponse(Base):
    __tablename__ = "message_responses"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False, unique=True)
    response_time_ms = Column(Integer, nullable=False)
    source_layer = Column(SQLAlchemyEnum(ResponseSourceLayer), nullable=False)
    
    source_qa_id = Column(String, ForeignKey("qa_pairs.qa_id"), nullable=True)
    source_document_chunks = Column(JSON, nullable=True)

    message = relationship("ChatMessage", back_populates="response_details")