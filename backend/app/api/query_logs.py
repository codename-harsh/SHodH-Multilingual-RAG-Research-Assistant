from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import require_api_key
from app.models.query_log import QueryLog

router = APIRouter(dependencies=[Depends(require_api_key)], tags=["query history"])


@router.get("/query_logs")
async def query_logs(limit: int = 30, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(QueryLog).order_by(QueryLog.created_at.desc()).limit(min(limit, 100)))
    return [
        {
            "id": str(row.id),
            "question": row.question,
            "doc_id": str(row.doc_id) if row.doc_id else None,
            "detected_language": row.detected_language,
            "answer": row.final_answer,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at.isoformat(),
        }
        for row in result.scalars()
    ]
