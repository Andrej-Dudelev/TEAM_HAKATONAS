from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class VariationIn(BaseModel):
    variation_text: str = Field(..., min_length=1)
    language: Optional[str] = "lt"

class QACreate(BaseModel):
    question: Optional[str] = None
    answer: str
    variations: List[VariationIn] = Field(default_factory=list)
    index: bool = True

class QAUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    variations: Optional[List[VariationIn]] = None
    reindex: bool = True

class QAOut(BaseModel):
    qa_id: str
    question: Optional[str] = None
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True

class QAListOut(BaseModel):
    total: int
    items: List[QAOut]

