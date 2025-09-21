from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from app.db.models.chat import ResponseSourceLayer

class MessageResponseMeta(BaseModel):
    response_time_ms: int
    source_layer: ResponseSourceLayer
    source_qa_id: Optional[str] = None
    source_document_chunks: Optional[List[str]] = None

    class Config:
        from_attributes = True

class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime
    response_details: Optional[MessageResponseMeta] = None

    class Config:
        from_attributes = True

class ChatSessionOut(BaseModel):
    id: str
    created_at: datetime
    messages: List[ChatMessageOut]

    class Config:
        from_attributes = True

class SendMessageIn(BaseModel):
    message: str = Field(..., min_length=1)
    language: Optional[str] = "lt"
    context: Optional[str] = None

class CreateSessionResponse(BaseModel):
    session_id: str