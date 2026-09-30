from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.auth import require_api_key
from app.api.dependencies import get_ingestion_result_factory, get_ingestion_task
from app.db.session import get_db
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.schemas.ingestion import IngestAccepted, IngestStatus

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["ingestion"])
settings = get_settings()
UPLOAD_DIR = Path("/data/uploads")


@router.post("/ingest", response_model=IngestAccepted, status_code=status.HTTP_202_ACCEPTED)
async def ingest(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    ingestion_task=Depends(get_ingestion_task),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    doc_id = uuid4()
    task_id = str(uuid4())
    filename = Path(file.filename or "document.pdf").name[:512]
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UPLOAD_DIR / f"{doc_id}.pdf"
    header = b""
    try:
        with upload_path.open("xb") as output:
            while True:
                piece = await file.read(1024 * 1024)
                if not piece:
                    break
                total += len(piece)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"PDF exceeds {settings.max_upload_mb} MB limit",
                    )
                if len(header) < 5:
                    header += piece[: 5 - len(header)]
                output.write(piece)
        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
        if header != b"%PDF-":
            raise HTTPException(status_code=415, detail="Uploaded file is not a valid PDF")

        db.add(Document(id=doc_id, filename=filename, status="queued"))
        db.add(IngestionJob(job_id=task_id, doc_id=doc_id))
        await db.commit()
        try:
            ingestion_task.apply_async(args=[str(doc_id), filename, str(upload_path)], task_id=task_id)
        except Exception as exc:
            await db.execute(update(Document).where(Document.id == doc_id).values(status="failed"))
            await db.commit()
            upload_path.unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Ingestion queue is unavailable") from exc
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        raise
    except Exception:
        await db.rollback()
        upload_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return IngestAccepted(job_id=task_id, doc_id=doc_id, status="queued")


@router.get("/ingest/{job_id}", response_model=IngestStatus)
async def ingest_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    result_factory=Depends(get_ingestion_result_factory),
):
    job = await db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    document = await db.get(Document, job.doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    result = result_factory(job_id)
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
