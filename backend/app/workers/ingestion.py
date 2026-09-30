import asyncio
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.pipeline.ingestion.chunker import chunk_pages
from app.pipeline.ingestion.embeddings import CohereEmbedder
from app.pipeline.ingestion.pdf import extract_pdf_pages
from app.pipeline.ingestion.qdrant import QdrantDocumentStore
from app.workers.celery_app import celery_app


async def _run_ingestion(doc_id: UUID, filename: str, upload_path: str) -> int:
    async with SessionLocal() as session:
        document = await session.get(Document, doc_id)
        if document is None:
            raise ValueError("Document row not found")
        document.status = "processing"
        await session.commit()

    try:
        pages = extract_pdf_pages(upload_path)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No extractable text was found in the PDF")

        embedder = CohereEmbedder()
        vectors = await asyncio.to_thread(embedder.embed, [chunk.text for chunk in chunks])
        store = QdrantDocumentStore()
        await asyncio.to_thread(store.ensure_collection, len(vectors[0]))
        await asyncio.to_thread(store.upsert, doc_id, chunks, vectors)

        async with SessionLocal() as session:
            document = await session.get(Document, doc_id)
            document.n_chunks = len(chunks)
            document.status = "complete"
            await session.commit()

        return len(chunks)
    except Exception:
        async with SessionLocal() as session:
            document = await session.get(Document, doc_id)
            if document:
                document.status = "failed"
                await session.commit()
        raise
    finally:
        try:
            Path(upload_path).unlink(missing_ok=True)
        except OSError:
            pass


@celery_app.task(name="shodh.ingest_document")
def ingest_document(doc_id: str, filename: str, upload_path: str) -> int:
    return asyncio.run(_run_ingestion(UUID(doc_id), filename, upload_path))
