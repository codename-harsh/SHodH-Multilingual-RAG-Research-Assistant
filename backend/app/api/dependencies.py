"""Lazy factories used by API routes and replaceable in credential-free tests."""

from fastapi import HTTPException


def get_query_embedder():
    from app.pipeline.query.embeddings import QueryEmbedder

    try:
        return QueryEmbedder()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_hybrid_retriever():
    from app.pipeline.query.retriever import HybridRetriever

    return HybridRetriever()


def get_gemini_generator():
    from app.pipeline.llm.gemini import GeminiGenerator

    try:
        return GeminiGenerator()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_chunk_reranker():
    from app.pipeline.query.reranker import rerank

    return rerank


def get_ingestion_task():
    from app.workers.ingestion import ingest_document

    return ingest_document


def get_ingestion_result_factory():
    from celery.result import AsyncResult

    from app.workers.celery_app import celery_app

    return lambda job_id: AsyncResult(job_id, app=celery_app)
