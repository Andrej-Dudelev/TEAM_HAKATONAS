from typing import List, Optional
from pydantic import BaseModel, Field

class QuestionVariation(BaseModel):
    """Vieno klausimo variacija (alternatyvus formuluotės variantas)."""
    id: str
    qa_pair_id: str
    language: str
    variation_text: str

class QAPair(BaseModel):
    """Pagrindinis Q&A įrašas su pradiniu klausimu (-ais) ir variacijomis."""
    qa_id: str
    question_en: Optional[str] = None
    question_ka: Optional[str] = None
    variations: List[QuestionVariation] = Field(default_factory=list)

__all__ = ["QAPair", "QuestionVariation"]
