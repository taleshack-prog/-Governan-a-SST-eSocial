# ==============================================================
# RADAR PREVIDENCIÁRIO — Sprint 3: Tendências e Ranking
# Arquivo: api/routers/tendencias.py
# ==============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from datetime import date, timedelta
from calendar import monthrange

from api.database import get_db, set_tenant
from api.models.afastamento import Afastamento
from api.models.trabalhador import Trabalhador
from api.auth import get_current_user
from api.models.usuario import Usuario

router = APIRouter()


@router.get("/previsao-custo")
async def get_previsao_custo(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    hoje = date.today()
    empresa_id = current_user.empresa_id

    # Buscar afastamentos dos últimos 3 meses
    tres_meses_atras = hoje - timedelta(days=90)
    result = await db.execute(
        select(Afastamento).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.data_inicio >= tres_meses_atras
        ).order_by(Afastamento.data_inicio.asc())
    )
    afastamentos = result.scalars().all()

    # Agrupar por mês
    meses = {}
    for af in afastamentos:
        mes_key = af.data_inicio.strftime("%Y-%m")
        mes_label = af.data_inicio.strftime("%b/%Y")
        if mes_key not in meses:
            meses[mes_key] = {
                "mes": mes_label,
                "mes_key": mes_key,
                "total_casos": 0,
                "custo_total": 0.0,
                "dias_total": 0,
            }
        salario_dia = float(af.salario_base or 3000) / 30
        data_fim = af.data_retorno or hoje
        dias = max(0, (data_fim - af.data_inicio).days)
        custo = dias * salario_dia

        meses[mes_key]["total_casos"] += 1
        meses[mes_key]["custo_total"] += custo
        meses[mes_key]["dias_total"] += dias

    historico = sorted(meses.values(), key=lambda x: x["mes_key"])

    # Calcular tendência (variação % último vs penúltimo mês)
    tendencia_pct = 0
    tendencia_dir = "estavel"
    if len(historico) >= 2:
        ultimo = historico[-1]["custo_total"]
        penultimo = historico[-2]["custo_total"]
        if penultimo > 0:
            tendencia_pct = ((ultimo - penultimo) / penultimo) * 100
            if tendencia_pct > 5:
                tendencia_dir = "subindo"
            elif tendencia_pct < -5:
                tendencia_dir = "caindo"

    # Projeção próximo mês baseada na tendência
    afas_ativos = await db.execute(
        select(Afastamento).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    ativos = afas_ativos.scalars().all()

    dias_prox_mes = monthrange(
        hoje.year if hoje.month < 12 else hoje.year + 1,
        hoje.month + 1 if hoje.month < 12 else 1
    )[1]

    custo_diario = sum(float(a.salario_base or 3000) / 30 for a in ativos)
    projecao_prox_mes = custo_diario * dias_prox_mes

    if tendencia_dir == "subindo":
        projecao_prox_mes *= (1 + abs(tendencia_pct) / 100)
    elif tendencia_dir == "caindo":
        projecao_prox_mes *= (1 - abs(tendencia_pct) / 200)

    # Adicionar mês atual e próximo ao histórico para o gráfico
    mes_atual_key = hoje.strftime("%Y-%m")
    if mes_atual_key not in meses:
        custo_atual = custo_diario * hoje.day
        historico.append({
            "mes": hoje.strftime("%b/%Y"),
            "mes_key": mes_atual_key,
            "total_casos": len(ativos),
            "custo_total": round(custo_atual),
            "dias_total": len(ativos) * hoje.day,
        })

    prox_mes_date = date(
        hoje.year if hoje.month < 12 else hoje.year + 1,
        hoje.month + 1 if hoje.month < 12 else 1,
        1
    )
    historico.append({
        "mes": prox_mes_date.strftime("%b/%Y") + " (prev.)",
        "mes_key": prox_mes_date.strftime("%Y-%m"),
        "total_casos": len(ativos),
        "custo_total": round(projecao_prox_mes),
        "dias_total": 0,
        "projecao": True,
    })

    for h in historico:
        h["custo_total"] = round(h["custo_total"])

    return {
        "historico": historico,
        "tendencia_pct": round(tendencia_pct, 1),
        "tendencia_dir": tendencia_dir,
        "projecao_prox_mes": round(projecao_prox_mes),
        "custo_diario_atual": round(custo_diario),
    }


@router.get("/ranking-casos")
async def get_ranking_casos(
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

    ranking = []
    for af, trab in rows:
        dias = (hoje - af.data_inicio).days if af.data_inicio else 0
        salario_dia = float(af.salario_base or 3000) / 30
        custo_acumulado = dias * salario_dia

        # Calcular score de impacto
        score = 0
        fatores = []

        if af.status == "limbo":
            score += 40
            fatores.append("Via judicial")
        if af.data_prevista_retorno and af.data_prevista_retorno < hoje:
            score += 30
            fatores.append("Retorno atrasado")
        if not af.cid:
            score += 10
            fatores.append("Sem CID")
        if dias > 30:
            score += 20
            fatores.append(f"{dias} dias afastado")

        ranking.append({
            "trabalhador": trab.nome,
            "setor": trab.setor or "—",
            "cid": af.cid or "—",
            "status": af.status,
            "dias_afastado": dias,
            "custo_acumulado": round(custo_acumulado),
            "custo_diario": round(salario_dia),
            "score_impacto": min(100, score),
            "fatores": fatores,
            "data_inicio": str(af.data_inicio) if af.data_inicio else None,
            "data_retorno_prevista": str(af.data_prevista_retorno) if af.data_prevista_retorno else None,
        })

    ranking.sort(key=lambda x: (-x["score_impacto"], -x["custo_acumulado"]))
    for i, r in enumerate(ranking):
        r["posicao"] = i + 1

    return {
        "ranking": ranking,
        "total_custo_acumulado": round(sum(r["custo_acumulado"] for r in ranking)),
        "media_dias": round(sum(r["dias_afastado"] for r in ranking) / len(ranking)) if ranking else 0,
    }


@router.get("/impacto-setorial")
async def get_impacto_setorial(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    hoje = date.today()
    empresa_id = current_user.empresa_id

    trab_r = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == empresa_id)
    )
    trabalhadores = trab_r.scalars().all()

    afas_r = await db.execute(
        select(Afastamento, Trabalhador).join(
            Trabalhador, Afastamento.trabalhador_id == Trabalhador.id
        ).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    afastamentos = afas_r.all()

    # Agrupar trabalhadores por setor
    setores_total = {}
    for t in trabalhadores:
        setor = t.setor or "Sem setor"
        if setor not in setores_total:
            setores_total[setor] = 0
        setores_total[setor] += 1

    # Agrupar afastamentos por setor
    setores_afas = {}
    for af, trab in afastamentos:
        setor = trab.setor or "Sem setor"
        if setor not in setores_afas:
            setores_afas[setor] = {"count": 0, "custo": 0.0, "dias": 0}
        dias = (hoje - af.data_inicio).days if af.data_inicio else 0
        salario_dia = float(af.salario_base or 3000) / 30
        setores_afas[setor]["count"] += 1
        setores_afas[setor]["custo"] += dias * salario_dia
        setores_afas[setor]["dias"] += dias

    # Calcular impacto por setor
    resultado = []
    for setor, total in setores_total.items():
        afas = setores_afas.get(setor, {"count": 0, "custo": 0.0, "dias": 0})
        afastados = afas["count"]
        pct_capacidade_reduzida = (afastados / total * 100) if total > 0 else 0

        resultado.append({
            "setor": setor,
            "total_trabalhadores": total,
            "afastados": afastados,
            "pct_capacidade_reduzida": round(pct_capacidade_reduzida, 1),
            "custo_acumulado": round(afas["custo"]),
            "media_dias": round(afas["dias"] / afastados) if afastados > 0 else 0,
            "criticidade": "alta" if pct_capacidade_reduzida >= 30 else "media" if pct_capacidade_reduzida >= 10 else "baixa",
        })

    resultado.sort(key=lambda x: -x["pct_capacidade_reduzida"])

    return {
        "setores": resultado,
        "setor_mais_critico": resultado[0]["setor"] if resultado else None,
    }
