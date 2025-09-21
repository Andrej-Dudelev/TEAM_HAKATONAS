from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.training import TrainingCourse, TrainingSection, Lesson
from app.schemas.training import CourseCreate, SectionCreate, LessonCreate, CourseOut

router = APIRouter(tags=["Training"])

@router.get("/courses", response_model=list[CourseOut])
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(TrainingCourse).all()
    return courses