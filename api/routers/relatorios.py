# api/routers/relatorios.py — SST ESOCIAL GOV
# Etapa 5 (v2) / Módulo 6 — Endpoint do relatório executivo (PDF para download).
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.achado import Achado
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.motor_ratfap import calcular_ratfap
from api.services.regua_prescricao import calcular_regua
from api.services.relatorio_executivo import gerar_relatorio_executivo

router = APIRouter()

_EXIBICAO = {"verde": "Conferido", "amarelo": "Pendência de informação", "vermelho": "Divergência identificada"}


@router.get("/executivo")
async def relatorio_executivo(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Gera o relatório executivo mensal em PDF para a empresa do usuário logado."""
    empresa_id = current_user.empresa_id

    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()

    # Blocos (RAT×FAP calculado + os demais pendentes)
    ratfap = await calcular_ratfap(empresa_id, db)
    ratfap["exibicao"] = _EXIBICAO.get(ratfap.get("semaforo"), "")
    blocos = [
        {"bloco": "Cota Patronal", "exibicao": "Pendência de informação"},
        ratfap,
        {"bloco": "Terceiros", "exibicao": "Pendência de informação"},
        {"bloco": "FGTS", "exibicao": "Pendência de informação"},
    ]

    # Achados da empresa
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()
    achados = []
    total_credito = 0.0
    total_prescreve_90 = 0.0
    if estabs:
        rows = (await db.execute(
            select(Achado).where(Achado.estabelecimento_id.in_(estabs))
            .order_by(Achado.valor_retroativo.desc().nullslast())
        )).scalars().all()
        for a in rows:
            achados.append({
                "descricao": a.descricao, "tipo": a.tipo, "esfera": a.esfera,
                "prazo_dias": a.prazo_dias, "valor_retroativo": float(a.valor_retroativo) if a.valor_retroativo else None,
            })
            if a.tipo == "credito" and a.valor_retroativo:
                total_credito += float(a.valor_retroativo)
                if a.valor_mensal:
                    total_prescreve_90 += calcular_regua(a.valor_mensal)["valor_prescreve_90dias"]

    dados = {
        "empresa": {"razao_social": empresa.razao_social if empresa else "—"},
        "competencia": date.today().strftime("%m/%Y"),
        "blocos": blocos,
        "creditos": {"total_credito": round(total_credito, 2), "total_prescreve_90dias": round(total_prescreve_90, 2)},
        "achados": achados,
    }

    pdf = gerar_relatorio_executivo(dados)
    filename = f"relatorio-executivo-{date.today().strftime('%Y-%m')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
