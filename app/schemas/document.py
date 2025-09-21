from typing import List
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentOut(BaseModel):
    id: str
    filename: str
    language: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
        
class DocumentListOut(BaseModel):
    items: List[DocumentOut]

    class Config:
        from_attributes = True

