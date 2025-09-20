import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class QAPair(Base):
    __tablename__ = "qa_pairs"
    qa_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_en = Column(Text, nullable=True)
    question_ka = Column(Text, nullable=True)
    answer_en = Column(Text, nullable=False)
    answer_ka = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    variations = relationship("QuestionVariation", back_populates="qa_pair", cascade="all, delete-orphan")

class QuestionVariation(Base):
    __tablename__ = "question_variations"
    id = Column(Integer, primary_key=True, index=True)
    qa_pair_id = Column(String, ForeignKey("qa_pairs.qa_id"), nullable=False)
    variation_text = Column(Text, nullable=False)
    language = Column(String(2), nullable=False)
    
    qa_pair = relationship("QAPair", back_populates="variations")