from typing import List, Dict, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.open_ai import (
    get_general_knowledge_response,
    get_rag_response,
    stream_general_knowledge_response,
)
from app.core.config import settings

router = APIRouter()

class AskRequest(BaseModel):
    query: str
    mode: str = "general" 
    context: List[str] = []    
    history: Optional[List[Dict[str, str]]] = None

@router.get("/health")
async def health():
    status = "ok" if settings.OPENAI_API_KEY else "missing_api_key"
    return {"status": status, "model": settings.OPENAI_MODEL}

@router.post("/ask")
async def ask(req: AskRequest):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OpenAI API key is not configured.")

    if req.mode == "rag":
        answer = await get_rag_response(req.query, req.context)
    else:
        answer = await get_general_knowledge_response(req.query, req.history)

    return {"answer": answer}

@router.get("/ask-stream")
async def ask_stream(q: str):
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OpenAI API key is not configured.")

    async def gen() -> AsyncGenerator[bytes, None]:
        async for piece in stream_general_knowledge_response(q, history=None):
            yield f"data: {piece}\n\n".encode("utf-8")
        yield b"event: done\ndata: end\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
