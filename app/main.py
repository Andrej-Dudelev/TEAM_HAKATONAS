# 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.database import create_tables
from app.api.routes import router as api_router
from app.api.page_routes import router as page_router
from app.api.achievements import router as achievement_router 
from app.services.scheduler import goal_scheduler
from app.models import User, Achievement
import os
import logging

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    logger.info("Starting application...")
    create_tables()
    
    try:
        goal_scheduler.start()
        logger.info("Goal scheduler started")
    except Exception as e:
        logger.error(f"Failed to start goal scheduler: {e}")
    
    yield
    
    logger.info("Shutting down application...")
    try:
        goal_scheduler.stop()
        logger.info("Goal scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping goal scheduler: {e}")

app = FastAPI(
    title="Mental Health FastAPI App",
    description="A mental health application with user authentication, achievements, and automatic goal assignment",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = "app/static"
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    logger.warning(f"Static directory '{STATIC_DIR}' not found. Static files will not be served.")

app.include_router(api_router, prefix="/api/v1")
app.include_router(achievement_router, prefix="/api/v1", tags=["Achievements"]) 
app.include_router(page_router, tags=["Pages"])

@app.get("/api", tags=["Info"])
def api_info():
    """API information endpoint"""
    return {
        "message": "Welcome to Mental Health FastAPI App API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "User Authentication & Authorization",
            "Customer/Multi-tenant Support", 
            "Achievement System with Auto-assignment",
            "Daily/Weekly/Monthly Goals",
            "Admin Panel with User Management",
            "Background Scheduler for Goal Assignment"
        ],
        "endpoints": {
            "authentication": "/api/v1/auth/",
            "users": "/api/v1/users/",
            "admin": "/api/v1/admin/",
            "achievements": "/api/v1/achievements/",
            "progress": "/api/v1/progress/",
            "customers": "/api/v1/customers/"
        }
    }

@app.get("/health", tags=["Info"])
def health_check():
    """Application health check"""
    return {
        "status": "healthy", 
        "app": "Mental Health FastAPI",
        "scheduler_running": goal_scheduler.scheduler.running if goal_scheduler.scheduler else False
    }

@app.get("/scheduler/status", tags=["Admin"])
def scheduler_status():
    """Get scheduler status (for monitoring)"""
    if not goal_scheduler.scheduler:
        return {"status": "not_initialized"}
    
    jobs = []
    for job in goal_scheduler.scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running" if goal_scheduler.scheduler.running else "stopped",
        "jobs": jobs
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)