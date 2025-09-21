from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload, subqueryload
from app.db.session import get_db
from app.db.models.training import TrainingCourse, TrainingSection, Lesson

router = APIRouter(tags=["Pages"], include_in_schema=False)
templates = Jinja2Templates(directory="app/template")

@router.get("/training", response_class=HTMLResponse)
async def get_training_list(request: Request, db: Session = Depends(get_db)):
    courses = db.query(TrainingCourse).all()
    return templates.TemplateResponse(name="training.html", context={"request": request, "courses": courses, "page": "training"})

@router.get("/training/course/{course_id}", response_class=HTMLResponse)
async def get_course_page(request: Request, course_id: str, db: Session = Depends(get_db)):
    course = db.query(TrainingCourse).options(
        joinedload(TrainingCourse.sections).joinedload(TrainingSection.lessons)
    ).filter(TrainingCourse.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return templates.TemplateResponse(name="course.html", context={"request": request, "course": course, "page": "training"})

@router.get("/training/lesson/{lesson_id}", response_class=HTMLResponse)
async def get_lesson_page(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).options(joinedload(Lesson.section)).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return templates.TemplateResponse(name="lesson.html", context={"request": request, "lesson": lesson, "page": "training"})

@router.get("/admin/training/lesson/{lesson_id}", response_class=HTMLResponse)
async def get_admin_lesson_edit_page(request: Request, lesson_id: str, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).options(joinedload(Lesson.section)).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return templates.TemplateResponse(name="admin_lesson.html", context={"request": request, "lesson": lesson, "page": "admin_training"})

@router.get("/admin/training/section/{section_id}/new-lesson", response_class=HTMLResponse)
async def get_admin_lesson_create_page(request: Request, section_id: str, db: Session = Depends(get_db)):
    section = db.query(TrainingSection).filter(TrainingSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return templates.TemplateResponse(name="admin_lesson_create.html", context={"request": request, "section": section, "page": "admin_training"})

@router.get("/admin/training", response_class=HTMLResponse)
async def get_admin_training_page(request: Request, course_id: str = None, db: Session = Depends(get_db)):
    courses_query = db.query(TrainingCourse).options(
        subqueryload(TrainingCourse.sections).subqueryload(TrainingSection.lessons)
    )
    courses = courses_query.all()
    selected_course = courses_query.filter(TrainingCourse.id == course_id).first() if course_id else None
    
    return templates.TemplateResponse(
        name="admin_training.html", 
        context={
            "request": request, 
            "courses": courses, 
            "selected_course": selected_course,
            "page": "admin_training"
        }
    )

@router.get("/admin/qa", response_class=HTMLResponse)
async def get_admin_qa_page(request: Request):
    return templates.TemplateResponse(name="admin_qa.html", context={"request": request, "page": "admin_qa"})

@router.get("/admin/documents", response_class=HTMLResponse)
async def get_admin_documents_page(request: Request):
    return templates.TemplateResponse(name="admin_documents.html", context={"request": request, "page": "admin_documents"})


@router.get("/", response_class=RedirectResponse, status_code=302)
async def root():
    return "/training"

