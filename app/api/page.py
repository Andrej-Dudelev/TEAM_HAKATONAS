# užregistroujame router ir šablonus šioje vietoje kad būtų galima importuoti iš app.main
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def root_page(request: Request):
    """Return login page as root page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Return login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/create", response_class=HTMLResponse)
def create_page(request: Request):
    """Return create account page"""
    return templates.TemplateResponse("create.html", {"request": request})

@router.get("/achievements", response_class=HTMLResponse)
def achievements_page(request: Request):
    """Return achievements page"""
    return templates.TemplateResponse("achievements.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    """Return dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    """Return history page"""
    return templates.TemplateResponse("history.html", {"request": request})

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """Return admin panel page"""
    return templates.TemplateResponse("admin.html", {"request": request})