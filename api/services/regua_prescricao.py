# api/services/regua_prescricao.py — SST ESOCIAL GOV
# Etapa 4 (v2) / seção 10 — Régua de prescrição de 5 anos (art. 168 do CTN).
# Aplicada a todo achado do tipo 'credito'. Janela de 60 meses retroativos.
# Exibe: valor total recuperável, valor que prescreve em 90 dias, data-limite.
# Sem dependências externas — só stdlib.
import calendar
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.achado import Achado
from api.models.memoria_prescricao import MemoriaCalculoPrescricao

JANELA_MESES = 60
DIAS_ALERTA = 90


def add_months(d: date, months: int) -> date:
    total = d.month - 1 + months
    ano = d.year + total // 12
    mes = total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))


def _primeiro_dia_mes(d: date) -> date:
    return d.replace(day=1)


def calcular_regua(credito_mensal, data_ref: date | None = None) -> dict:
    """Calcula a régua para um crédito mensal recorrente. Não grava — só calcula."""
    if data_ref is None:
        data_ref = date.today()
    cm = Decimal(str(credito_mensal or 0))
    comp_mais_antiga = _primeiro_dia_mes(add_months(data_ref, -(JANELA_MESES - 1)))
    valor_total = (cm * JANELA_MESES).quantize(Decimal("0.01"))
    data_prescricao_proxima = add_months(_primeiro_dia_mes(comp_mais_antiga), JANELA_MESES)

    limite_90 = data_ref + timedelta(days=DIAS_ALERTA)
    comps = 0
    cursor = data_prescricao_proxima
    while cursor <= limite_90:
        comps += 1
        cursor = add_months(cursor, 1)
    valor_90 = (cm * comps).quantize(Decimal("0.01"))

    return {
        "valor_total_recuperavel": float(valor_total),
        "valor_prescreve_90dias": float(valor_90),
        "competencias_prescrevem_90dias": comps,
        "data_prescricao_proxima": data_prescricao_proxima.isoformat(),
        "janela_meses": JANELA_MESES,
        "data_referencia": data_ref.isoformat(),
    }


async def gravar_memoria(achado: Achado, db: AsyncSession, data_ref: date | None = None) -> dict:
    """Grava a memória de cálculo (composição por competência) de um achado de crédito.
    Requisito de prova (v2 seção 10). Atualiza achado.data_prescricao_proxima."""
    if achado.tipo != "credito" or not achado.valor_mensal:
        return {"gravado": False, "motivo": "não é crédito ou sem valor mensal"}
    if data_ref is None:
        data_ref = date.today()

    cm = Decimal(str(achado.valor_mensal))
    regua = calcular_regua(cm, data_ref)

    await db.execute(delete(MemoriaCalculoPrescricao).where(
        MemoriaCalculoPrescricao.achado_id == achado.id,
        MemoriaCalculoPrescricao.data_referencia == data_ref,
    ))

    comp = _primeiro_dia_mes(add_months(data_ref, -(JANELA_MESES - 1)))
    for _ in range(JANELA_MESES):
        db.add(MemoriaCalculoPrescricao(
            achado_id=achado.id, competencia=comp, valor_competencia=cm,
            dentro_janela=True, data_referencia=data_ref,
        ))
        comp = add_months(comp, 1)

    achado.data_prescricao_proxima = date.fromisoformat(regua["data_prescricao_proxima"])
    await db.commit()
    return {"gravado": True, "competencias": JANELA_MESES, **regua}
