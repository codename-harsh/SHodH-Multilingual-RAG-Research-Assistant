from app.models.document import Base
from app.models.ingestion_job import IngestionJob  # noqa: F401
from app.models.query_log import QueryLog  # noqa: F401
from app.db.session import engine


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
