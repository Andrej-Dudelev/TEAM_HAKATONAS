# app/api/semantic_routes.py
from typing import List, Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, constr
from types import SimpleNamespace

# Servisas – spėjame, kad tavo klasę įsidėjai į app/services/semantic_search.py
# Jei failas vadinasi kitaip, atitinkamai pataisyk importą:
from app.services.semantic_search import SemanticSearchService, search_service  # type: ignore
from typing import List, Dict, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, constr

from app.core.config import settings
from app.services.open_ai import (
    get_general_knowledge_response,
    get_rag_response,
    stream_general_knowledge_response,
)

router = APIRouter(tags=["LLM"])

# ==== Schemos ====
class ChatRequest(BaseModel):
    message: constr(strip_whitespace=True, min_length=1) = Field(..., description="Vartotojo žinutė")

class RagRequest(BaseModel):
    message: constr(strip_whitespace=True, min_length=1) = Field(..., description="Vartotojo žinutė")
    context: List[constr(strip_whitespace=True, min_length=1)] = Field(
        default_factory=list, description="Konteksto ištraukos (neprivaloma)"
    )

class ChatResponse(BaseModel):
    answer: str = Field(..., description="LLM atsakymas")

class HealthResponse(BaseModel):
    status: str
    model: str

# ==== Helpers ====
def ensure_api_key():
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OpenAI API key is not configured.")

# ==== Endpoint'ai ====
@router.get("/health", response_model=HealthResponse)
async def health():
    status = "ok" if settings.OPENAI_API_KEY else "missing_api_key"
    return {"status": status, "model": settings.OPENAI_MODEL}

@router.post(
    "/ask",
    response_model=ChatResponse,
 
    description="Priima tik `{ message }` ir grąžina pilną atsakymą.",
)
async def ask(req: ChatRequest):
    ensure_api_key()
    answer = await get_general_knowledge_response(req.message)
    return {"answer": answer or ""}

@router.post(
    "/ask-rag",
    response_model=ChatResponse,
    
    description="Priima `{ message, context[] }` ir grąžina atsakymą panaudojant kontekstą.",
)
async def ask_rag(req: RagRequest):
    ensure_api_key()
    answer = await get_rag_response(req.message, req.context)
    return {"answer": answer or ""}

@router.get(
    "/ask-stream",
    summary="Streaming atsakymas (SSE)",
    description="`GET /ask-stream?message=...` – grąžina atsakymą dalimis (text/event-stream).",
)
async def ask_stream(message: str = Query(..., min_length=1, description="Vartotojo žinutė")):
    ensure_api_key()

    async def gen() -> AsyncGenerator[bytes, None]:
        async for piece in stream_general_knowledge_response(message, history=None):
            yield f"data: {piece}\n\n".encode("utf-8")
        yield b"event: done\ndata: end\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")








# ---------- DTO schemos (request/response) ----------

class VariationIn(BaseModel):
    id: str = Field(..., description="Unikalus variacijos ID (naudojamas vektorių kolekcijoje)")
    language: constr(strip_whitespace=True, min_length=1)
    variation_text: constr(strip_whitespace=True, min_length=1)

class QAPairIn(BaseModel):
    qa_id: constr(strip_whitespace=True, min_length=1)
    question_lt: Optional[constr(strip_whitespace=True, min_length=1)] = None

    variations: List[VariationIn] = Field(default_factory=list)

class VariationCreate(BaseModel):
    id: str
    qa_pair_id: constr(strip_whitespace=True, min_length=1)
    language: constr(strip_whitespace=True, min_length=1)
    variation_text: constr(strip_whitespace=True, min_length=1)

class MatchResponse(BaseModel):
    qa_id: str
    language: str
    distance: float

class DocumentIndexRequest(BaseModel):
    document_id: constr(strip_whitespace=True, min_length=1)
    language: constr(strip_whitespace=True, min_length=1)
    chunks: List[constr(strip_whitespace=True, min_length=1)]

class DocumentSearchResponse(BaseModel):
    chunks: List[str]

# ---------- helper: singleton servisui gauti ----------

def get_service() -> SemanticSearchService:
    # Jei globalus search_service None – inicializuojam čia
    global search_service  # atkeliauja iš semantic_search modulio
    if search_service is None:
        search_service = SemanticSearchService()
    return search_service

# ---------- Q&A indeksavimo/paieškos endpointai ----------

@router.post("/qa/sync")
def sync_index(pairs: List[QAPairIn]):
    svc = get_service()
    # Servisas tikisi objektų su atributais (qa_id, question_en, question_ka, variations[])
    # Sukuriam SimpleNamespace, kad atitiktų laukus
    to_sync = []
    for p in pairs:
        vars_ns = [SimpleNamespace(id=v.id, variation_text=v.variation_text, language=v.language)
                   for v in p.variations]
        qa_ns = SimpleNamespace(
            qa_id=p.qa_id,
            question_en=p.question_en,
            question_ka=p.question_ka,
            variations=vars_ns
        )
        to_sync.append(qa_ns)
    svc.sync_index_from_db(to_sync)  # tipų tikrinimas servise tik anotacijoms; runtime veiks
    return {"status": "ok", "count": len(pairs)}

@router.post("/qa", summary="Pridėti Q&A į indeksą")
def add_qa(qa: QAPairIn):
    svc = get_service()
    vars_ns = [SimpleNamespace(id=v.id, variation_text=v.variation_text, language=v.language)
               for v in qa.variations]
    qa_ns = SimpleNamespace(
        qa_id=qa.qa_id,
        question_en=qa.question_en,
  
        variations=vars_ns
    )
    svc.add_qa_pair(qa_ns)
    return {"status": "ok"}

@router.put("/qa/{qa_id}", summary="Atnaujinti Q&A (perindeksuoti)")
def update_qa(qa_id: str, qa: QAPairIn):
    if qa.qa_id != qa_id:
        raise HTTPException(status_code=400, detail="Body qa_id nesutampa su path qa_id.")
    svc = get_service()
    vars_ns = [SimpleNamespace(id=v.id, variation_text=v.variation_text, language=v.language)
               for v in qa.variations]
    qa_ns = SimpleNamespace(
        qa_id=qa.qa_id,
        question_en=qa.question_en,

        variations=vars_ns
    )
    svc.update_qa_pair(qa_ns)
    return {"status": "ok"}

@router.delete("/qa/{qa_id}", summary="Pašalinti Q&A iš indekso")
def delete_qa(qa_id: str):
    svc = get_service()
    svc.delete_qa_pair(qa_id)
    return {"status": "ok"}

@router.post("/qa/variation", summary="Pridėti klausimo variaciją")
def add_variation(variation: VariationCreate):
    svc = get_service()
    var_ns = SimpleNamespace(
        id=variation.id,
        qa_pair_id=variation.qa_pair_id,
        language=variation.language,
        variation_text=variation.variation_text
    )
    svc.add_question_variation(var_ns)
    return {"status": "ok"}

@router.get("/qa/match", response_model=Optional[MatchResponse], summary="Rasti geriausią atitikmenį")
def find_match(query: str = Query(..., min_length=1), language: str = Query(..., min_length=1)):
    svc = get_service()
    result = svc.find_best_match(query, language)
    # result jau grąžina {"qa_id","language","distance"} arba None
    return result

# ---------- Dokumentų indeksavimas / paieška ----------

@router.post("/docs/index", summary="Indeksuoti dokumento chunk'us")
def index_document(req: DocumentIndexRequest):
    svc = get_service()
    svc.index_document_chunks(req.chunks, req.document_id, req.language)
    return {"status": "ok", "count": len(req.chunks)}

@router.get("/docs/search", response_model=DocumentSearchResponse, summary="Ieškoti dokumentuose (RAG)")
def search_documents(query: str = Query(..., min_length=1), language: str = Query(..., min_length=1)):
    svc = get_service()
    chunks = svc.search_documents(query, language)
    return {"chunks": chunks}
