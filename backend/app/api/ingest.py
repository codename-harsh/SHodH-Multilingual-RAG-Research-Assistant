from pathlib import Path
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.auth import require_api_key
from app.db.session import get_db
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.schemas.ingestion import IngestAccepted, IngestStatus
from app.workers.celery_app import celery_app
from app.workers.ingestion import ingest_document

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["ingestion"])
settings = get_settings()
UPLOAD_DIR = Path("/data/uploads")


@router.post("/ingest", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
async def ingest(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    chunks: list[bytes] = []
    while True:
        piece = await file.read(1024 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail=f"PDF exceeds {settings.max_upload_mb} MB limit")
        chunks.append(piece)
    if not chunks:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    data = b"".join(chunks)

    doc_id = uuid4()
    task_id = str(uuid4())
    filename = file.filename or "document.pdf"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOAD_DIR / f"{doc_id}.pdf"
    upload_path.write_bytes(data)

    db.add(Document(id=doc_id, filename=filename, status="queued"))
    db.add(IngestionJob(job_id=task_id, doc_id=doc_id))
    await db.commit()

    ingest_document.apply_async(args=[str(doc_id), filename, str(upload_path)], task_id=task_id)
    return IngestAccepted(job_id=task_id, doc_id=doc_id, status="queued")


@router.get("/ingest/{job_id}", response_model=IngestStatus)
async def ingest_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    document = await db.get(Document, job.doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    result = AsyncResult(job_id, app=celery_app)
    error = None
    if result.failed():
        error = str(result.result)

    return IngestStatus(
        job_id=job_id,
        doc_id=job.doc_id,
        status=document.status,
        n_chunks=document.n_chunks,
        error=error,
    )
