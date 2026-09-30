from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    doc_id: UUID | None = None
    language: str | None = None


class Citation(BaseModel):
    page: int
    chunk_id: str
    text_snippet: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    latency_ms: float
    detected_language: str | None = None
    retrieved_context: list[dict] = Field(default_factory=list)
