from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "shodh",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.ingestion"],
)
celery_app.conf.task_track_started = True
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)
