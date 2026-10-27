FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --default-timeout=100 --retries 10 "httpx>=0.27.0,<1" "poetry==$POETRY_VERSION"

WORKDIR /app
COPY backend/pyproject.toml backend/poetry.lock* ./
RUN poetry install --only main,reranking,evaluation --no-root

COPY backend/app ./app
COPY evaluation ./evaluation
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 10000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
