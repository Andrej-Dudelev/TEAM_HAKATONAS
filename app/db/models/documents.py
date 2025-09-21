import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    language = Column(String(2), nullable=False)
    status = Column(String, default="indexed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())