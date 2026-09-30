from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    postgres_user: str = "shodh"
    postgres_password: str = "shodh"
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "shodh"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "shodh_docs"
    cohere_api_key: str = ""
    cohere_embed_model: str = "embed-multilingual-v3.0"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_eval_model: str = "gemini-2.0-flash"
    gemini_eval_embed_model: str = "models/text-embedding-004"
    shodh_api_key: str = ""
    shodh_api_url: str = "http://localhost:8000"
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=128, ge=0)
    embed_batch_size: int = Field(default=96, gt=0)
    hybrid_alpha: float = Field(default=0.7, ge=0.0, le=1.0)
    max_upload_mb: int = Field(default=25, gt=0)
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def resolve_database_url(cls, values):
        if not isinstance(values, dict) or values.get("database_url"):
            return values
        values["database_url"] = URL.create(
            "postgresql+asyncpg",
            username=values.get("postgres_user", "shodh"),
            password=values.get("postgres_password", "shodh"),
            host=values.get("postgres_host", "localhost"),
            port=int(values.get("postgres_port", 5432)),
            database=values.get("postgres_db", "shodh"),
        ).render_as_string(hide_password=False)
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()
