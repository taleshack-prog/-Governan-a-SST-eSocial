# SST ESOCIAL GOV — Celery App
from celery import Celery
from api.config import settings

app = Celery(
    "sst_esocial",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["api.tasks.ai_tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
)
