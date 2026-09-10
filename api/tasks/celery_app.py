# SST ESOCIAL GOV — Celery App
from celery import Celery
from api.config import settings

app = Celery(
    "sst_esocial",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["api.tasks.ai_tasks", "api.tasks.afastamento_tasks", "api.tasks.importacao_task", "api.tasks.prescricao_tasks"],
)

app.conf.beat_schedule = {
    "verificar-alertas-afastamentos": {
        "task": "afastamentos.verificar_alertas",
        "schedule": 86400.0,  # a cada 24 horas
    },
    "atualizar-status-afastamentos": {
        "task": "afastamentos.atualizar_status_automatico",
        "schedule": 3600.0,  # a cada 1 hora
    },
    "recalcular-prescricao-mensal": {
        "task": "prescricao.recalcular_memoria_mensal",
        "schedule": 2592000.0,  # a cada 30 dias (recálculo mensal — v2 seção 10)
    },
}

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
)
