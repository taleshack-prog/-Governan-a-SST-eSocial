# ==============================================================
# SST ESOCIAL GOV — Tasks: Recálculo mensal da prescrição
# Arquivo: api/tasks/prescricao_tasks.py
# Base: v2 seção 10 — recálculo mensal registrado em log (requisito de prova).
# Grava a memória de cálculo de todos os achados de crédito.
# ==============================================================
from celery import shared_task
from datetime import date
from sqlalchemy import select
import asyncio
import logging

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="prescricao.recalcular_memoria_mensal", bind=True)
def recalcular_memoria_mensal(self):
    """Recalcula e grava a memória de prescrição de todos os achados de crédito.
    Executado mensalmente (v2 seção 10)."""
    return run_async(_recalcular())


async def _recalcular():
    from api.database import get_db
    from api.models.achado import Achado
    from api.services.regua_prescricao import gravar_memoria

    agen = get_db()
    db = await agen.__anext__()
    processados = 0
    try:
        achados = (await db.execute(
            select(Achado).where(Achado.tipo == "credito")
        )).scalars().all()
        hoje = date.today()
        for a in achados:
            res = await gravar_memoria(a, db, hoje)
            if res.get("gravado"):
                processados += 1
        logger.info(f"[prescricao] memória recalculada para {processados} achados")
    except Exception as e:
        logger.error(f"[prescricao] erro no recálculo mensal: {e}")
        raise
    finally:
        try:
            await agen.__anext__()
        except StopAsyncIteration:
            pass
    return {"processados": processados}
