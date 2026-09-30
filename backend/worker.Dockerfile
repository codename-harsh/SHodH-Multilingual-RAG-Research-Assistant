FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_NO_INTERACTION=1 POETRY_VIRTUALENVS_CREATE=false
RUN pip install --no-cache-dir "poetry==2.1.1"
WORKDIR /app
COPY backend/pyproject.toml backend/poetry.lock* ./
RUN poetry install --only main --no-root
COPY backend/app ./app
CMD ["celery", "-A", "app.workers.celery_app.celery_app", "worker", "--loglevel=INFO"]
