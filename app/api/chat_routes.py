from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
import json
from typing import List

from app.db.session import get_db
from app.db.models.chat import ChatSession, ChatMessage, MessageResponse
from app.schemas.chat import CreateSessionResponse, ChatSessionOut, SendMessageIn
from app.services.chat_service import generate_response_stream

router = APIRouter(tags=["Chat"])

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
    return [{"role": m.role, "content": m.content} for m in msgs]

@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(db: Session = Depends(get_db)):
    sess = ChatSession()
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return CreateSessionResponse(session_id=sess.id)

@router.get("/sessions/{session_id}", response_model=ChatSessionOut)
def get_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSessionOut.from_orm(sess)

@router.post("/sessions/{session_id}/send")
async def send_message_stream(session_id: str, body: SendMessageIn, db: Session = Depends(get_db)):
    sess = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    history = _build_history(db, session_id, limit=10)

    async def event_generator():
        full_response = ""
        final_meta = {}
        stream = generate_response_stream(
            query=body.message, 
            language=body.language, 
            history=history, 
            lesson_context=body.context
        )
        async for result in stream:
            content_chunk = result.get("content")
            meta_chunk = result.get("meta")
            if content_chunk:
                full_response += content_chunk
                yield f"data: {json.dumps({'content': content_chunk})}\n\n"
            if meta_chunk:
                final_meta = meta_chunk
                
        asst_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
        db.add(asst_msg)
        db.commit()
        db.refresh(asst_msg)

        if final_meta:
            meta = MessageResponse(
                message_id=asst_msg.id, 
                response_time_ms=final_meta.get("response_time_ms", 0), 
                source_layer=final_meta["source_layer"], 
                source_qa_id=final_meta.get("source_qa_id"), 
                source_document_chunks=final_meta.get("source_document_chunks")
            )
            db.add(meta)
            db.commit()
            
        yield f"event: done\ndata: {json.dumps(final_meta)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")