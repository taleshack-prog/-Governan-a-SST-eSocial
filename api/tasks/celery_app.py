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

    # ------------------------------------------------------------------
    # TETO DE MEMORIA DOS PROCESSOS FILHOS (06/11)
    #
    # O worker sobe em modo prefork com --concurrency=2 (ver railway-worker.json): dois
    # processos filhos permanentes. Sem limite de reciclagem, filho que cresce nunca encolhe.
    #
    # Aqui isso nao e teorico. A task processar_ltcat abre PDF com PyMuPDF a partir de bytes
    # (fitz.open(stream=...)). O close() e chamado, mas memoria liberada por biblioteca em C
    # raramente volta ao sistema operacional: o processo mantem o pico alcancado.
    #
    # Precedente medido em outro projeto da mesma conta Railway (LinkPost AI, 10/2026): um
    # worker Celery sem estes limites segurava 4,21 GB de RAM com o processador em 0,0014
    # vCPU — US$ 43,53 num mes, quase metade da fatura inteira da conta.
    #
    # O limite nao diagnostica vazamento; ele limita o estrago havendo ou nao. Com dois
    # filhos a 400.000 KiB, o teto fica em ~0,78 GB.
    #
    # Unidade conferida na documentacao: --max-memory-per-child e em KiB, e o filho TERMINA
    # a tarefa em andamento antes de ser substituido — nenhuma importacao morre no meio.
    # https://manpages.debian.org/trixie/celery/celery-worker.1.en.html
    # ------------------------------------------------------------------
    worker_max_tasks_per_child=20,
    worker_max_memory_per_child=400000,   # KiB (~390 MB)
    worker_prefetch_multiplier=1,         # nao acumula tarefas dentro do filho
)
