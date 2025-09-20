# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

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
    # Pasirinktinai: keisti kelią į OpenAPI JSON / Swagger / ReDoc
    openapi_url="/openapi.json",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
