from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class LessonCreate(BaseModel):
    section_id: str
    title: str
    content: str
    starting_code: Optional[str] = None
    order: int = 0
    validation_criteria: Optional[Dict[str, Any]] = None

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    starting_code: Optional[str] = None
    validation_criteria: Optional[Dict[str, Any]] = None

class LessonOut(BaseModel):
    id: str
    title: str
    order: int
    content: str
    starting_code: Optional[str] = None
    validation_criteria: Optional[Dict[str, Any]] = None
    class Config:
        from_attributes = True

class SectionCreate(BaseModel):
    course_id: str
    title: str
    order: int = 0

class SectionOut(BaseModel):
    id: str
    title: str
    order: int
    lessons: List[LessonOut]
    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    compiler: str = "python"

class CourseOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    compiler: str
    sections: List[SectionOut]
    class Config:
        from_attributes = True

