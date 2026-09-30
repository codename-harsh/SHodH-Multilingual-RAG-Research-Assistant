from uuid import UUID

from pydantic import BaseModel


class IngestAccepted(BaseModel):
    job_id: str
    doc_id: UUID
    status: str


class IngestStatus(BaseModel):
    job_id: str
    doc_id: UUID
    status: str
    n_chunks: int | None = None
    error: str | None = None
