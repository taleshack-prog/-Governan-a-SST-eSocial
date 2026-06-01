# ==============================================================
# SST ESOCIAL GOV — Tasks: Automações de Afastamento
# Arquivo: api/tasks/afastamento_tasks.py
# ==============================================================

from celery import shared_task
from datetime import date, datetime, timezone
from sqlalchemy import select, and_
import asyncio
import logging

logger = logging.getLogger(__name__)


def run_async(coro):
    """Executa coroutine em contexto síncrono do Celery."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="afastamentos.verificar_alertas", bind=True)
def verificar_alertas_afastamentos(self):
    """
    Verifica todos os afastamentos ativos e gera alertas automáticos.
    Deve ser executada diariamente.
    """
    return run_async(_verificar_alertas())


async def _verificar_alertas():
    from api.database import AsyncSessionLocal
    from api.models.afastamento import Afastamento, AlertaAfastamento

    alertas_gerados = []

    async with AsyncSessionLocal() as db:
        # Buscar todos afastamentos não encerrados
        result = await db.execute(
            select(Afastamento).where(
                Afastamento.status.notin_(["encerrado"])
            )
        )
        afastamentos = result.scalars().all()

        hoje = date.today()

        for a in afastamentos:
            dias = (hoje - a.data_inicio).days if a.data_inicio else 0

            # Alerta 1: Passou de 15 dias sem status INSS
            if dias > 15 and a.status in ["recebido", "em_analise", "pendente", "limbo"]:
                alerta = await _criar_alerta(
                    db, a,
                    tipo="inss_necessario",
                    mensagem=f"Afastamento de {dias} dias sem benefício INSS registrado. Verificar se auxílio-doença foi solicitado.",
                    prioridade="alta"
                )
                if alerta:
                    alertas_gerados.append(alerta)

            # Alerta 2: Retorno previsto em 3 dias
            if a.data_prevista_retorno:
                dias_para_retorno = (a.data_prevista_retorno - hoje).days
                if 0 <= dias_para_retorno <= 3:
                    alerta = await _criar_alerta(
                        db, a,
                        tipo="retorno_proximo",
                        mensagem=f"Retorno previsto em {dias_para_retorno} dia(s). Preparar avaliação médica de retorno ao trabalho.",
                        prioridade="media"
                    )
                    if alerta:
                        alertas_gerados.append(alerta)

            # Alerta 3: Alta INSS sem retorno agendado
            if a.status == "alta_inss" and not a.data_prevista_retorno:
                alerta = await _criar_alerta(
                    db, a,
                    tipo="alta_sem_retorno",
                    mensagem="INSS concedeu alta mas data de retorno não foi agendada. Agendar avaliação com médico do trabalho.",
                    prioridade="alta"
                )
                if alerta:
                    alertas_gerados.append(alerta)

            # Alerta 4: Limbo há mais de 30 dias
            if a.status == "limbo" and dias > 15:
                alerta = await _criar_alerta(
                    db, a,
                    tipo="limbo_prolongado",
                    mensagem=f"Caso em limbo judicial há {dias} dias. Verificar andamento do processo com advogado.",
                    prioridade="critica"
                )
                if alerta:
                    alertas_gerados.append(alerta)

            # Alerta 5: Em benefício há mais de 150 dias (próximo do limite)
            if a.status == "em_beneficio" and dias > 150:
                alerta = await _criar_alerta(
                    db, a,
                    tipo="beneficio_longo",
                    mensagem=f"Trabalhador em benefício há {dias} dias. Verificar possibilidade de prorrogação ou aposentadoria por invalidez.",
                    prioridade="media"
                )
                if alerta:
                    alertas_gerados.append(alerta)

        await db.commit()

    logger.info(f"Verificação concluída: {len(alertas_gerados)} alertas gerados")
    return {"alertas_gerados": len(alertas_gerados), "data": str(hoje)}


async def _criar_alerta(db, afastamento, tipo: str, mensagem: str, prioridade: str):
    """Cria alerta apenas se não existir alerta do mesmo tipo nos últimos 7 dias."""
    from api.models.afastamento import AlertaAfastamento
    from sqlalchemy import and_
    from datetime import timedelta

    # Verificar se já existe alerta recente do mesmo tipo
    sete_dias_atras = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    result = await db.execute(
        select(AlertaAfastamento).where(
            and_(
                AlertaAfastamento.afastamento_id == afastamento.id,
                AlertaAfastamento.tipo == tipo,
                AlertaAfastamento.created_at >= sete_dias_atras,
            )
        )
    )
    existente = result.scalar_one_or_none()

    if existente:
        return None  # Já existe alerta recente

    alerta = AlertaAfastamento(
        empresa_id=afastamento.empresa_id,
        afastamento_id=afastamento.id,
        trabalhador_id=afastamento.trabalhador_id,
        tipo=tipo,
        mensagem=mensagem,
        prioridade=prioridade,
    )
    db.add(alerta)
    return str(afastamento.id)


@shared_task(name="afastamentos.atualizar_status_automatico", bind=True)
def atualizar_status_automatico(self):
    """
    Atualiza status de afastamentos com base em regras automáticas.
    """
    return run_async(_atualizar_status())


async def _atualizar_status():
    from api.database import AsyncSessionLocal
    from api.models.afastamento import Afastamento

    atualizados = []

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Afastamento).where(
                Afastamento.status.notin_(["encerrado"])
            )
        )
        afastamentos = result.scalars().all()

        hoje = date.today()

        for a in afastamentos:
            # Auto-encerrar se data de retorno já passou e status é retorno_proximo
            if (a.status == "retorno_proximo" and
                a.data_prevista_retorno and
                a.data_prevista_retorno < hoje):
                a.status = "encerrado"
                atualizados.append(str(a.id))

            # Marcar retorno_proximo automaticamente
            if (a.data_prevista_retorno and
                a.status not in ["encerrado", "limbo", "em_beneficio"] and
                0 <= (a.data_prevista_retorno - hoje).days <= 3):
                a.status = "retorno_proximo"
                atualizados.append(str(a.id))

        await db.commit()

    return {"atualizados": len(atualizados)}
