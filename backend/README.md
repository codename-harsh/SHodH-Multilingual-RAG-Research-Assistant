# Shodh Backend

FastAPI service for ingestion, hybrid retrieval, generation, query history, and evaluation.

## Development

The normal development entry point is the repository-level compose stack:

```bash
cp .env.example .env
docker compose up --build
```

For a direct Python run, install with Poetry and provide PostgreSQL, Redis, and Qdrant yourself:

```bash
poetry install
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Production startup runs Alembic migrations through `entrypoint.sh` before Uvicorn starts.

## Tests

```bash
poetry run pytest
```
