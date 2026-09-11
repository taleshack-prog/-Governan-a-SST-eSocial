# api/services/correcao_selic.py — SST ESOCIAL GOV
# Roteiro Módulo 2 Camada 3 — Correção pela SELIC.
# Regra Receita (art. 39 §4 Lei 9.250/95): SELIC acumulada do mês SEGUINTE ao pagamento
# até o mês ANTERIOR à restituição; no mês da restituição soma-se 1%. Por SOMA (série 4390).
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.indice_selic import IndiceSelic


def _primeiro_dia(d: date) -> date:
    return d.replace(day=1)


async def fator_selic(competencia_pagamento: date, data_restituicao: date, db: AsyncSession) -> Decimal:
    comp_pgto = _primeiro_dia(competencia_pagamento)
    mes_restituicao = _primeiro_dia(data_restituicao)

    inicio = _primeiro_dia(date(comp_pgto.year + (comp_pgto.month // 12), (comp_pgto.month % 12) + 1, 1))
    if mes_restituicao.month == 1:
        fim = date(mes_restituicao.year - 1, 12, 1)
    else:
        fim = date(mes_restituicao.year, mes_restituicao.month - 1, 1)

    if inicio > fim:
        return Decimal("1.01")

    rows = (await db.execute(
        select(IndiceSelic).where(
            IndiceSelic.competencia >= inicio,
            IndiceSelic.competencia <= fim,
        )
    )).scalars().all()
    acumulado = sum((Decimal(str(r.taxa_mensal)) for r in rows), Decimal("0"))
    return Decimal("1") + (acumulado / Decimal("100")) + (Decimal("1") / Decimal("100"))


async def corrigir_valor(valor, competencia_pagamento: date, data_restituicao: date, db: AsyncSession) -> Decimal:
    f = await fator_selic(competencia_pagamento, data_restituicao, db)
    return (Decimal(str(valor)) * f).quantize(Decimal("0.01"))


async def carregar_fatores_ate(data_restituicao: date, db: AsyncSession) -> dict:
    """Pré-calcula os fatores SELIC de cada competência até data_restituicao, carregando a
    tabela UMA vez. Retorna {competencia(date): fator(Decimal)}. Usado no comparador para
    evitar N queries no loop de competências."""
    mes_restituicao = _primeiro_dia(data_restituicao)
    todas = (await db.execute(select(IndiceSelic).order_by(IndiceSelic.competencia))).scalars().all()
    # mapa competencia -> taxa
    taxas = {r.competencia: Decimal(str(r.taxa_mensal)) for r in todas}
    comps = sorted(taxas.keys())

    # soma acumulada reversa: para cada competência de pagamento, a SELIC do mês seguinte
    # até o mês anterior à restituição.
    fatores = {}
    for comp_pgto in comps:
        # início = mês seguinte ao pagamento
        if comp_pgto.month == 12:
            inicio = date(comp_pgto.year + 1, 1, 1)
        else:
            inicio = date(comp_pgto.year, comp_pgto.month + 1, 1)
        # fim = mês anterior à restituição
        if mes_restituicao.month == 1:
            fim = date(mes_restituicao.year - 1, 12, 1)
        else:
            fim = date(mes_restituicao.year, mes_restituicao.month - 1, 1)
        if inicio > fim:
            fatores[comp_pgto] = Decimal("1.01")
        else:
            acum = sum((taxas[c] for c in comps if inicio <= c <= fim), Decimal("0"))
            fatores[comp_pgto] = Decimal("1") + (acum / Decimal("100")) + (Decimal("1") / Decimal("100"))
    return fatores
