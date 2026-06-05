# ==============================================================
# RADAR PREVIDENCIÁRIO — Motor Financeiro (Sprint 1 — Tela WOW)
# Arquivo: api/routers/radar_financeiro.py
# ==============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date, timedelta
from typing import Optional

from api.database import get_db, set_tenant
from api.models.afastamento import Afastamento
from api.models.trabalhador import Trabalhador
from api.auth import get_current_user
from api.models.usuario import Usuario

router = APIRouter()

CUSTO_DIA_MEDIO = 280  # R$/dia — base de cálculo conservadora
CUSTO_HORA_EXTRA = 85  # R$/hora extra


def calcular_score(dados: dict) -> dict:
    """
    Score de Pressão Previdenciária 0-100.
    Quanto maior, mais crítico.
    """
    score = 0
    detalhes = []

    # Peso 1: % de trabalhadores afastados (max 25pts)
    if dados["total_trabalhadores"] > 0:
        pct = dados["ativos"] / dados["total_trabalhadores"]
        pts = min(25, int(pct * 100))
        score += pts
        if pts > 10:
            detalhes.append(f"{int(pct*100)}% da equipe afastada")

    # Peso 2: casos em limbo/judicial (max 25pts)
    limbo_pts = min(25, dados["limbo"] * 12)
    score += limbo_pts
    if dados["limbo"] > 0:
        detalhes.append(f"{dados['limbo']} caso(s) em via judicial")

    # Peso 3: retornos atrasados (max 20pts)
    atraso_pts = min(20, dados["retorno_atrasado"] * 10)
    score += atraso_pts
    if dados["retorno_atrasado"] > 0:
        detalhes.append(f"{dados['retorno_atrasado']} retorno(s) atrasado(s)")

    # Peso 4: tempo médio de afastamento (max 15pts)
    if dados["media_dias"] > 30:
        pts = min(15, int((dados["media_dias"] - 30) / 10) * 5)
        score += pts
        detalhes.append(f"Média de {int(dados['media_dias'])} dias por caso")

    # Peso 5: sem previsão de retorno (max 15pts)
    sem_prev_pts = min(15, dados["sem_previsao"] * 8)
    score += sem_prev_pts
    if dados["sem_previsao"] > 0:
        detalhes.append(f"{dados['sem_previsao']} caso(s) sem previsão de retorno")

    score = min(100, score)

    if score >= 70:
        nivel = "crítico"
        cor = "#ef4444"
    elif score >= 40:
        nivel = "atenção"
        cor = "#f59e0b"
    else:
        nivel = "controlado"
        cor = "#10b981"

    return {"score": score, "nivel": nivel, "cor": cor, "fatores": detalhes}


@router.get("/score")
async def get_score(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)

    # Dados de afastamentos
    hoje = date.today()

    result = await db.execute(
        select(
            func.count(Afastamento.id).label("total"),
            func.count(func.nullif(Afastamento.status.in_(["encerrado"]), True)).label("ativos"),
            func.avg(
                func.extract("epoch", func.now() - Afastamento.data_inicio) / 86400
            ).label("media_dias"),
        ).where(Afastamento.empresa_id == current_user.empresa_id)
    )
    row = result.one()

    # Contar por status
    def count_status(*statuses):
        return db.execute(
            select(func.count(Afastamento.id)).where(
                Afastamento.empresa_id == current_user.empresa_id,
                Afastamento.status.in_(statuses)
            )
        )

    limbo_r = await count_status("limbo")
    limbo = limbo_r.scalar() or 0

    ativos_r = await db.execute(
        select(func.count(Afastamento.id)).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    ativos = ativos_r.scalar() or 0

    retorno_r = await db.execute(
        select(func.count(Afastamento.id)).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.data_prevista_retorno < hoje,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    retorno_atrasado = retorno_r.scalar() or 0

    sem_prev_r = await db.execute(
        select(func.count(Afastamento.id)).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.data_prevista_retorno == None,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    sem_previsao = sem_prev_r.scalar() or 0

    # Total trabalhadores
    trab_r = await db.execute(
        select(func.count(Trabalhador.id)).where(
            Trabalhador.empresa_id == current_user.empresa_id
        )
    )
    total_trabalhadores = trab_r.scalar() or 1

    dados = {
        "total": row.total or 0,
        "ativos": ativos,
        "limbo": limbo,
        "retorno_atrasado": retorno_atrasado,
        "sem_previsao": sem_previsao,
        "media_dias": float(row.media_dias or 0),
        "total_trabalhadores": total_trabalhadores,
    }

    score_data = calcular_score(dados)
    return {**score_data, **dados}


@router.get("/perdas-evitageis")
async def get_perdas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    hoje = date.today()

    result = await db.execute(
        select(Afastamento, Trabalhador).join(
            Trabalhador, Afastamento.trabalhador_id == Trabalhador.id
        ).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.status.notin_(["encerrado"])
        ).order_by(Afastamento.data_inicio.asc())
    )
    rows = result.all()

    perdas = []
    total_recuperavel = 0

    for afastamento, trabalhador in rows:
        dias = (hoje - afastamento.data_inicio).days if afastamento.data_inicio else 0
        salario_dia = float(afastamento.salario_base or 3000) / 30
        custo_total = dias * salario_dia

        # Calcular perda evitável por tipo
        if afastamento.status == "limbo":
            perda = custo_total * 0.4  # 40% recuperável via ação jurídica
            acao = "Acionar assessoria jurídica para encerrar via judicial"
            urgencia = "alta"
        elif afastamento.data_prevista_retorno and afastamento.data_prevista_retorno < hoje:
            perda = dias * CUSTO_DIA_MEDIO * 0.6
            acao = f"Confirmar retorno — atrasado {(hoje - afastamento.data_prevista_retorno).days} dias"
            urgencia = "alta"
        elif afastamento.data_prevista_retorno:
            dias_retorno = (afastamento.data_prevista_retorno - hoje).days
            if dias_retorno <= 7:
                perda = dias_retorno * CUSTO_DIA_MEDIO
                acao = f"Preparar retorno em {dias_retorno} dia(s) — organizar substituição"
                urgencia = "media"
            else:
                perda = 0
                acao = "Monitorar evolução"
                urgencia = "baixa"
        else:
            perda = custo_total * 0.3
            acao = "Definir previsão de retorno com médico"
            urgencia = "media"

        if perda > 0:
            total_recuperavel += perda
            perdas.append({
                "trabalhador": trabalhador.nome,
                "setor": trabalhador.setor or "—",
                "status": afastamento.status,
                "dias_afastado": dias,
                "custo_acumulado": round(custo_total),
                "perda_evitavel": round(perda),
                "acao": acao,
                "urgencia": urgencia,
            })

    perdas.sort(key=lambda x: x["perda_evitavel"], reverse=True)

    return {
        "total_recuperavel": round(total_recuperavel),
        "casos": perdas[:10],
    }


@router.get("/recomendacoes")
async def get_recomendacoes(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    hoje = date.today()

    result = await db.execute(
        select(Afastamento, Trabalhador).join(
            Trabalhador, Afastamento.trabalhador_id == Trabalhador.id
        ).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    rows = result.all()

    recomendacoes = []
    prioridade = 1

    for afastamento, trabalhador in rows:
        dias = (hoje - afastamento.data_inicio).days if afastamento.data_inicio else 0
        salario_dia = float(afastamento.salario_base or 3000) / 30

        if afastamento.status == "limbo":
            recomendacoes.append({
                "prioridade": prioridade,
                "acao": f"Resolver caso judicial de {trabalhador.nome}",
                "detalhe": f"Em via judicial há {dias} dias. Custo crescendo R$ {round(salario_dia)}/dia.",
                "impacto_estimado": round(dias * salario_dia * 0.4),
                "urgencia": "alta",
                "icone": "⚖️",
            })
            prioridade += 1

        elif afastamento.data_prevista_retorno and afastamento.data_prevista_retorno < hoje:
            atraso = (hoje - afastamento.data_prevista_retorno).days
            recomendacoes.append({
                "prioridade": prioridade,
                "acao": f"Confirmar retorno de {trabalhador.nome}",
                "detalhe": f"Retorno estava previsto há {atraso} dia(s). Verificar situação médica.",
                "impacto_estimado": round(atraso * salario_dia),
                "urgencia": "alta",
                "icone": "🔴",
            })
            prioridade += 1

        elif afastamento.data_prevista_retorno:
            dias_ret = (afastamento.data_prevista_retorno - hoje).days
            if 0 <= dias_ret <= 5:
                recomendacoes.append({
                    "prioridade": prioridade,
                    "acao": f"Preparar retorno de {trabalhador.nome}",
                    "detalhe": f"Retorno em {dias_ret} dia(s). Organizar substituição e integração.",
                    "impacto_estimado": round(dias_ret * salario_dia),
                    "urgencia": "media",
                    "icone": "📅",
                })
                prioridade += 1
        else:
            recomendacoes.append({
                "prioridade": prioridade,
                "acao": f"Definir previsão para {trabalhador.nome}",
                "detalhe": f"Sem previsão de retorno. Acionar médico do trabalho.",
                "impacto_estimado": round(dias * salario_dia * 0.2),
                "urgencia": "media",
                "icone": "❓",
            })
            prioridade += 1

    recomendacoes.sort(key=lambda x: (
        0 if x["urgencia"] == "alta" else 1 if x["urgencia"] == "media" else 2,
        -x["impacto_estimado"]
    ))

    for i, r in enumerate(recomendacoes):
        r["prioridade"] = i + 1

    # Projeção fim do mês
    dias_restantes = (date(hoje.year, hoje.month + 1 if hoje.month < 12 else 1, 1) - hoje).days
    custo_diario_total = sum(
        float(a.salario_base or 3000) / 30
        for a, _ in rows
    )
    projecao_mes = round(custo_diario_total * dias_restantes)

    return {
        "recomendacoes": recomendacoes[:6],
        "projecao_fim_mes": projecao_mes,
        "custo_diario": round(custo_diario_total),
    }
