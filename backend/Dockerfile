FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /app
COPY backend/pyproject.toml backend/poetry.lock* ./
RUN poetry install --only main --no-root

COPY backend/app ./app
COPY evaluation ./evaluation
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY backend/entrypoint.sh ./entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
