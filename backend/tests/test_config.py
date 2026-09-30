import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_database_url_is_built_with_escaped_password():
    settings = Settings(postgres_user="dev", postgres_password="p@ss:/#word", postgres_host="postgres")

    parsed = make_url(settings.database_url)

    assert parsed.username == "dev"
    assert parsed.password == "p@ss:/#word"
    assert parsed.host == "postgres"


def test_explicit_database_url_override_is_preserved():
    settings = Settings(database_url="postgresql+asyncpg://alice:secret@db.example:5432/research")

    assert settings.database_url == "postgresql+asyncpg://alice:secret@db.example:5432/research"


@pytest.mark.parametrize(
    "override",
    [
        {"hybrid_alpha": -0.1},
        {"hybrid_alpha": 1.1},
        {"chunk_size": 0},
        {"chunk_overlap": -1},
        {"embed_batch_size": 0},
        {"max_upload_mb": 0},
    ],
)
def test_invalid_runtime_ranges_are_rejected(override):
    with pytest.raises(ValueError):
        Settings(**override)
