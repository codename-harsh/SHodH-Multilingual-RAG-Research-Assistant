from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.document import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    doc_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    detected_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_chunks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
