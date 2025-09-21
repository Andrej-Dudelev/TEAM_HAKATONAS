from typing import AsyncGenerator, Dict, List, Optional
import time
from langdetect import detect, LangDetectException

from app.db.models.chat import ResponseSourceLayer
from app.services.open_ai import (
    stream_general_knowledge_response,
    stream_rag_response
)
from app.services.semantic_search import get_service as get_semantic_service
from app.db.session import SessionLocal
from app.db.models.qa import QAPair

async def generate_response_stream(
    query: str,
    language: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    lesson_context: Optional[str] = None
) -> AsyncGenerator[Dict, None]:
    start_time = time.perf_counter()
    semantic_service = get_semantic_service()
    
    search_language = "lt"
    try:
        detected_lang = detect(query)
        if detected_lang in ['en', 'lt']:
                search_language = detected_lang
    except LangDetectException:
        pass
    
    if language:
        search_language = language.lower()

    print(f"User query: '{query}'. Using language '{search_language}' for search.")

    qa_match = semantic_service.find_best_match(query, search_language)
    if qa_match:
        db = SessionLocal()
        try:
            qa_id = qa_match["qa_id"]
            answer_obj = db.query(QAPair).filter(QAPair.qa_id == qa_id).first()
            if answer_obj and answer_obj.answer:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                print(f"QA Match found. Responding in {elapsed_ms}ms.")
                yield {
                    "content": answer_obj.answer,
                    "meta": {
                        "source_layer": ResponseSourceLayer.QA,
                        "source_qa_id": qa_id,
                        "source_document_chunks": None,
                        "response_time_ms": elapsed_ms,
                    },
                }
                return
        finally:
            db.close()

    doc_chunks = semantic_service.search_documents(query, search_language)
    if doc_chunks:
        print(f"Found {len(doc_chunks)} relevant document chunks. Generating RAG response.")
        final_meta = {
            "source_layer": ResponseSourceLayer.RAG,
            "source_qa_id": None,
            "source_document_chunks": doc_chunks,
        }
        async for chunk in stream_rag_response(query, doc_chunks, lesson_context=lesson_context):
            yield {"content": chunk, "meta": None}

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        final_meta["response_time_ms"] = elapsed_ms
        print(f"RAG response streamed in {elapsed_ms}ms.")
        yield {"content": None, "meta": final_meta}
        return

    print("No QA or RAG match. Falling back to general knowledge model.")
    final_meta = {
        "source_layer": ResponseSourceLayer.GENERAL,
        "source_qa_id": None,
        "source_document_chunks": None,
    }
    async for chunk in stream_general_knowledge_response(query, history, lesson_context=lesson_context):
        yield {"content": chunk, "meta": None}

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    final_meta["response_time_ms"] = elapsed_ms
    print(f"General response streamed in {elapsed_ms}ms.")
    yield {"content": None, "meta": final_meta}