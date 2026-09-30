import time

from fastapi import APIRouter, Depends
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.auth import require_api_key
from app.db.session import get_db
from app.models.query_log import QueryLog
from app.pipeline.llm.gemini import GeminiGenerator
from app.pipeline.query.embeddings import QueryEmbedder
from app.pipeline.query.reranker import rerank
from app.pipeline.query.retriever import HybridRetriever
from app.schemas.query import Citation, QueryRequest, QueryResponse

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(payload: QueryRequest, db: AsyncSession = Depends(get_db)):
    started = time.perf_counter()
    try:
        detected_language = detect(payload.question)
    except LangDetectException:
        detected_language = None
    embedder = QueryEmbedder()
    retriever = HybridRetriever()
    generator = GeminiGenerator()

    dense = await __import__("asyncio").to_thread(embedder.embed, payload.question)
    retrieved = await __import__("asyncio").to_thread(
        retriever.retrieve,
        dense,
        payload.question,
        payload.doc_id,
        payload.language,
        20,
    )
    final_chunks = await __import__("asyncio").to_thread(rerank, payload.question, retrieved, 4)
    context = [
        {"page": chunk.page, "chunk_id": chunk.chunk_id, "text": chunk.text}
        for chunk in final_chunks
    ]
    answer = await __import__("asyncio").to_thread(generator.generate, payload.question, context)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    db.add(QueryLog(
        question=payload.question,
        doc_id=payload.doc_id,
        detected_language=detected_language,
        retrieved_chunks=[{"page": c.page, "chunk_id": c.chunk_id, "text": c.text, "score": c.score} for c in retrieved],
        final_answer=answer,
        latency_ms=latency_ms,
    ))
    await db.commit()

    return QueryResponse(
        answer=answer,
        citations=[Citation(page=c.page, chunk_id=c.chunk_id, text_snippet=c.text[:300]) for c in final_chunks],
        model=generator.model,
        latency_ms=latency_ms,
        detected_language=detected_language,
        retrieved_context=context,
    )
