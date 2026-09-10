# api/routers/achados.py — SST ESOCIAL GOV
# Etapa 3 (v2) / fase 3A-3 — Expõe os achados do comparador de folha.
# Regra de ouro (v2): fundamento jurídico NUNCA é retornado ao cliente comum.
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.achado import Achado
from api.models.estabelecimento import Estabelecimento
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.comparador_folha import rodar_comparador
from api.services.regua_prescricao import calcular_regua

router = APIRouter()


def _to_dict(a: Achado) -> dict:
    d = {
        "id": str(a.id),
        "estabelecimento_id": str(a.estabelecimento_id),
        "tipo": a.tipo,
        "descricao": a.descricao,
        "valor_mensal": float(a.valor_mensal) if a.valor_mensal is not None else None,
        "valor_retroativo": float(a.valor_retroativo) if a.valor_retroativo is not None else None,
        "grau_seguranca": a.grau_seguranca,
        "status": a.status,
        "esfera": a.esfera,
        "tipo_valor": a.tipo_valor,
        "acao_sugerida": a.acao_sugerida,
    }
    # Régua de prescrição (v2 seção 10): só para achados de crédito.
    if a.tipo == "credito" and a.valor_mensal:
        r = calcular_regua(a.valor_mensal)
        d["prescricao"] = {
            "valor_prescreve_90dias": r["valor_prescreve_90dias"],
            "data_prescricao_proxima": r["data_prescricao_proxima"],
            "competencias_90dias": r["competencias_prescrevem_90dias"],
        }
    return d


@router.post("/recalcular")
async def recalcular_achados(
    ano: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dispara o comparador de folha para a empresa do usuário e regrava os achados."""
    resumo = await rodar_comparador(current_user.empresa_id, db, ano=ano)
    return {
        "total_achados": resumo.get("total_achados", 0),
        "creditos": resumo.get("creditos", 0),
        "alertas": resumo.get("alertas", 0),
        "total_credito_retroativo_estimado": resumo.get("total_credito_retroativo_estimado", 0),
    }


@router.get("/")
async def listar_achados(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista os achados dos estabelecimentos da empresa do usuário logado."""
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == current_user.empresa_id)
    )).scalars().all()
    if not estabs:
        return {"total": 0, "total_credito": 0.0, "achados": []}

    result = await db.execute(
        select(Achado).where(Achado.estabelecimento_id.in_(estabs)).order_by(Achado.valor_retroativo.desc().nullslast())
    )
    achados = [_to_dict(a) for a in result.scalars()]
    total_credito = sum(a["valor_retroativo"] or 0 for a in achados if a["tipo"] == "credito")
    total_prescreve_90dias = sum(
        (a.get("prescricao") or {}).get("valor_prescreve_90dias", 0) for a in achados if a["tipo"] == "credito"
    )
    return {
        "total": len(achados),
        "total_credito": round(total_credito, 2),
        "total_prescreve_90dias": round(total_prescreve_90dias, 2),
        "achados": achados,
    }
