import asyncio

from fastapi import FastAPI
from fastapi.responses import JSONResponse
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
async def ready() -> JSONResponse:
    async def check_postgres() -> str:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return "ok"
        except Exception:
            return "error"

    async def check_redis() -> str:
        redis = None
        try:
            redis = Redis.from_url(
                settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await redis.ping()
            return "ok"
        except Exception:
            return "error"
        finally:
            if redis is not None:
                await redis.aclose()

    async def check_qdrant() -> str:
        def probe() -> None:
            qdrant = QdrantClient(
                url=settings.qdrant_url,
                timeout=1,
                check_compatibility=False,
            )
            try:
                qdrant.get_collections()
            finally:
                qdrant.close()

        try:
            await asyncio.to_thread(probe)
            return "ok"
        except Exception:
            return "error"

    async def bounded(check) -> str:
        try:
            return await asyncio.wait_for(check(), timeout=2.5)
        except Exception:
            return "error"

    postgres, redis, qdrant = await asyncio.gather(
        bounded(check_postgres),
        bounded(check_redis),
        bounded(check_qdrant),
    )
    checks = {"postgres": postgres, "redis": redis, "qdrant": qdrant}

    healthy = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )
