# app/api/chat_routes.py
from __future__ import annotations
import time
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# DB session dependency (pakeisk, jei pas tave kitur)
from app.db.session import get_db

# SQLAlchemy modeliai (pakoreguok kelią, jei failas kitas)
from app.db.models.chat import (
    ChatSession,
    ChatMessage,
    MessageResponse,
    ResponseSourceLayer,
)

# LLM paslaugos
from app.services.open_ai import (
    get_general_knowledge_response,
    get_rag_response,
)

# (nebūtina) semantinis RAG kontekstas iš dokumentų
try:
    from app.services.semantic_search import get_service  # lazy singleton
except Exception:
    get_service = None

router = APIRouter(tags=["Chat"])

# --------- Schemos (Pydantic) ---------
class CreateSessionResponse(BaseModel):
    session_id: str

class MessageResponseMeta(BaseModel):
    response_time_ms: int
    source_layer: ResponseSourceLayer
    source_qa_id: Optional[str] = None
    source_document_chunks: Optional[List[str]] = None

class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    timestamp: Optional[str] = None
    response_details: Optional[MessageResponseMeta] = None

class ChatSessionOut(BaseModel):
    id: str
    created_at: Optional[str] = None
    messages: List[ChatMessageOut] = Field(default_factory=list)

class SendMessageIn(BaseModel):
    message: str = Field(..., min_length=1, description="Vartotojo žinutė")
    mode: Literal["general", "rag"] = "general"
    language: str = "en"
    context: List[str] = Field(default_factory=list)          # RAG rankinis kontekstas
    use_semantic_docs: bool = False                           # jei True – paims chunk'us iš semantic_search
    history_limit: int = 10                                   # kiek ankstesnių žinučių paduoti LLM istorijai

class SendMessageOut(BaseModel):
    session_id: str
    user_message_id: int
    assistant_message_id: int
    answer: str
    response_meta: MessageResponseMeta

# --------- Pagalbinės ---------
def _build_history(db: Session, session_id: str, limit: int) -> List[dict]:
    if limit <= 0:
        return []
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    msgs.reverse()
    history: List[dict] = []
    for m in msgs:
        role = "assistant" if m.role == "assistant" else "user"
        history.append({"role": role, "content": m.content})
    return history

# --------- Endpoint'ai ---------
@router.post("/sessions", response_model=CreateSessionResponse, summary="Sukurti naują chat sesiją")
def create_session(db: Session = Depends(get_db)):
    sess = ChatSession()
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return CreateSessionResponse(session_id=sess.id)

@router.get("/sessions/{session_id}", response_model=ChatSessionOut, summary="Gauti sesijos žinutes")
def get_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    out_msgs: List[ChatMessageOut] = []
    # jei nori laiko tvarka – gali pridėti .order_by(ChatMessage.id.asc())
    for m in sess.messages:
        resp = (
            db.query(MessageResponse)
            .filter(MessageResponse.message_id == m.id)
            .first()
        )
        resp_meta = (
            MessageResponseMeta(
                response_time_ms=resp.response_time_ms,
                source_layer=resp.source_layer,
                source_qa_id=resp.source_qa_id,
                source_document_chunks=resp.source_document_chunks,
            )
            if resp
            else None
        )
        out_msgs.append(
            ChatMessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp.isoformat() if m.timestamp else None,
                response_details=resp_meta,
            )
        )

    return ChatSessionOut(
        id=sess.id,
        created_at=sess.created_at.isoformat() if sess.created_at else None,
        messages=out_msgs,
    )

@router.post(
    "/sessions/{session_id}/send",
    response_model=SendMessageOut,
    summary="Siųsti žinutę į LLM ir įrašyti atsakymą (GENERAL arba RAG)",
)
async def send_message(session_id: str, body: SendMessageIn, db: Session = Depends(get_db)):
    # 1) Sesija
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2) Išsaugom user žinutę
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3) Istorija LLM'ui
    history = _build_history(db, session_id, body.history_limit)

    # 4) RAG kontekstas (rankinis + semantinis, jei paprašyta)
    rag_context: List[str] = list(body.context)
    if body.mode == "rag" and body.use_semantic_docs:
        if get_service is None:
            raise HTTPException(status_code=400, detail="Semantic search service is not available.")
        svc = get_service()
        doc_chunks = svc.search_documents(body.message, body.language)
        rag_context.extend(doc_chunks)

    # 5) Kvietimas LLM
    start = time.perf_counter()
    if body.mode == "rag" and rag_context:
        answer = await get_rag_response(body.message, rag_context)
        source_layer = ResponseSourceLayer.RAG
        used_chunks = rag_context
    else:
        answer = await get_general_knowledge_response(body.message, history=history)
        source_layer = ResponseSourceLayer.GENERAL
        used_chunks = None
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # 6) Įrašom asistento žinutę
    asst_msg = ChatMessage(session_id=session_id, role="assistant", content=answer or "")
    db.add(asst_msg)
    db.commit()
    db.refresh(asst_msg)

    # 7) Įrašom MessageResponse (meta)
    meta = MessageResponse(
        message_id=asst_msg.id,
        response_time_ms=elapsed_ms,
        source_layer=source_layer,
        source_qa_id=None,                       # jei turėsi QA sluoksnį – užpildysi
        source_document_chunks=used_chunks,
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)

    return SendMessageOut(
        session_id=session_id,
        user_message_id=user_msg.id,
        assistant_message_id=asst_msg.id,
        answer=answer or "",
        response_meta=MessageResponseMeta(
            response_time_ms=meta.response_time_ms,
            source_layer=meta.source_layer,
            source_qa_id=meta.source_qa_id,
            source_document_chunks=meta.source_document_chunks,
        ),
    )
