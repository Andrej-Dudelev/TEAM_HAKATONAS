from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

from app.api.admin_routes import router as admin_router
from app.api.chat_routes import router as chat_router
from app.api.pages import router as pages_router
from app.api.training_routes import router as training_router
from app.api.code_execution_routes import router as code_execution_router
from app.db import init_db, SessionLocal, QAPair
from app.services import semantic_search
from app.services.semantic_search import SemanticSearchService

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Application Startup ---")
    init_db()
    print("Instantiating and syncing SemanticSearchService...")
    semantic_search.search_service = SemanticSearchService()
    
    db: Session = SessionLocal()
    try:
        all_qa_pairs = db.query(QAPair).all()
        if all_qa_pairs:
            semantic_search.search_service.sync_index_from_db(all_qa_pairs)
        else:
            print("No Q&A pairs in DB to sync with ChromaDB.")
    finally:
        db.close()

    print("--- Startup Complete ---")
    yield
    print("--- Application Shutdown ---")

app = FastAPI(
    title="Learning Platform API",
    description="API for an interactive learning platform.",
    version="2.0.0",
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages_router)
app.include_router(chat_router, prefix="/api/chat")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(training_router, prefix="/api/training")
app.include_router(code_execution_router, prefix="/api/code")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)