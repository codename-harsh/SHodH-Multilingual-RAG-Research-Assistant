from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://shodh:shodh@postgres:5432/shodh"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "shodh_docs"
    cohere_api_key: str = ""
    cohere_embed_model: str = "embed-multilingual-v3.0"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    shodh_api_key: str = ""
    chunk_size: int = 512
    chunk_overlap: int = 128
    embed_batch_size: int = 96
    hybrid_alpha: float = 0.7
    max_upload_mb: int = 25
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
