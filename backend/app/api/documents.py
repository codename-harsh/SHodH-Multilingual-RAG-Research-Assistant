import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document
from app.core.config import get_settings
from app.core.auth import require_api_key
from qdrant_client import QdrantClient, models

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["documents"])


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "n_chunks": doc.n_chunks,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "status": doc.status,
        }
        for doc in result.scalars()
    ]


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: UUID, db: AsyncSession = Depends(get_db)):
    document = await db.get(Document, doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url, timeout=5)
    try:
        if await asyncio.to_thread(client.collection_exists, settings.qdrant_collection):
            await asyncio.to_thread(
                client.delete,
                collection_name=settings.qdrant_collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=str(doc_id)))]
                    )
                ),
                wait=True,
            )
    finally:
        client.close()
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()
