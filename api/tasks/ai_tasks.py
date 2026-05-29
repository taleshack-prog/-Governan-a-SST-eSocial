# SST ESOCIAL GOV — Tasks de IA
from api.tasks.celery_app import app
import logging

logger = logging.getLogger("sst_tasks")

@app.task(name="validar_documento")
def validar_documento_task(documento_id: str, empresa_id: str):
    logger.info(f"Validando documento {documento_id}")
    return {"status": "concluido", "documento_id": documento_id}
