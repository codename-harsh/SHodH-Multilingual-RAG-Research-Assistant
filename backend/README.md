# Shodh Backend

FastAPI service for ingestion, hybrid retrieval, generation, query history, and evaluation.

## Development

The normal development entry point is the repository-level Compose stack. Provider keys are not required to start it:

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

Without provider credentials, `/health` and `/ready` remain usable. Ingestion returns a failed job with a `COHERE_API_KEY` message; query requests return HTTP 503 identifying the missing provider. RAGAS evaluation does not run against the checked-in placeholder dataset.

## Tests

```bash
poetry run pytest
```
