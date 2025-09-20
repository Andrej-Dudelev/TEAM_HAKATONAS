from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.pages import router as pages_router
from app.db import init_db, SessionLocal, QAPair
from app.services.semantic_search import SemanticSearchService, search_service as global_search_service
from app.api.chat_routes import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Application Startup ---")
    init_db()
    global global_search_service
    if global_search_service is None:
        print("Instantiating and syncing SemanticSearchService...")
        global_search_service = SemanticSearchService()
        db: Session = SessionLocal()
        try:
            all_qa_pairs = db.query(QAPair).all()
            if all_qa_pairs:
                global_search_service.sync_index_from_db(all_qa_pairs)
            else:
                print("No Q&A pairs in DB to sync with ChromaDB.")
        finally:
            db.close()
    print("--- Startup Complete ---")
    yield
    print("--- Application Shutdown ---")

app = FastAPI(
    title="Simple LLM API",
    description="""
API atsakyti į klausimus naudojant OpenAI modelius.
**Endpoint'ai:**
- `POST /api/ask` – grąžina LLM atsakymą (general arba RAG režimas).
- `GET /api/ask-stream` – SSE srautas (atsakymas dalimis).
- `GET /api/health` – sveikatos patikra.
""",
    version="1.0.0",
    contact={
        "name": "Aurimas",
        "email": "aurimas@example.com",
        "url": "https://example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


app.include_router(pages_router)
app.include_router(api_router, prefix="/api")
app.include_router(chat_router, prefix="/api/chat")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)