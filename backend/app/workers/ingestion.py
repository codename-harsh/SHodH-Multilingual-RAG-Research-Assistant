import asyncio
import logging
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.upload_storage import delete_upload, materialize_pdf
from app.db.session import SessionLocal
from app.models.document import Document
from app.pipeline.ingestion.chunker import chunk_pages
from app.pipeline.ingestion.embeddings import CohereEmbedder
from app.pipeline.ingestion.pdf import extract_pdf_pages
from app.pipeline.ingestion.qdrant import QdrantDocumentStore
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_ingestion(doc_id: UUID, filename: str, upload_path: str) -> int:
    async with SessionLocal() as session:
        document = await session.get(Document, doc_id)
        if document is None:
            raise ValueError("Document row not found")
        document.status = "processing"
        await session.commit()

    try:
        local_path, is_temporary = await asyncio.to_thread(materialize_pdf, upload_path)
        pages = extract_pdf_pages(str(local_path))
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
            await asyncio.to_thread(delete_upload, upload_path)
        except Exception:
            logger.exception("Could not delete processed upload %s", upload_path)
        if "is_temporary" in locals() and is_temporary:
            local_path.unlink(missing_ok=True)


@celery_app.task(name="shodh.ingest_document")
def ingest_document(doc_id: str, filename: str, upload_path: str) -> int:
    return asyncio.run(_run_ingestion(UUID(doc_id), filename, upload_path))
