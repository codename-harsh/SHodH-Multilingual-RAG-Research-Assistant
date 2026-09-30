from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from redis.asyncio import Redis
from qdrant_client import QdrantClient

from app.api.ingest import router as ingest_router
from app.api.query import router as query_router
from app.api.documents import router as documents_router
from app.api.query_logs import router as query_logs_router
from app.api.evaluate import router as evaluate_router
from app.core.config import get_settings
from app.db.session import engine
settings = get_settings()

app = FastAPI(
    title="Shodh API",
    version="0.1.0",
    description="Multilingual RAG research assistant API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(query_logs_router)
app.include_router(evaluate_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api", "version": app.version}


@app.get("/ready", tags=["system"])
async def ready() -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "error"

    try:
        redis = Redis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    try:
        QdrantClient(url=settings.qdrant_url).get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "error"

    healthy = all(value == "ok" for value in checks.values())
    return {"status": "ready" if healthy else "degraded", "checks": checks}
