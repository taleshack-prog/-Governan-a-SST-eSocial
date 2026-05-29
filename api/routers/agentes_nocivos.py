# api/routers/agentes_nocivos.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date

from api.database import get_db
from api.models.agente_nocivo import AgenteNocivo
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class AgenteCreate(BaseModel):
    trabalhador_id: str | None = None
    vinculo_id: str | None = None
    codigo_tabela24: str
    descricao_agente: str
    nivel_exposicao: str | None = None
    unidade_medida: str | None = None
    epc_eficaz: bool | None = None
    epi_eficaz: bool | None = None
    epi_ca: str | None = None
    data_inicio: date
    data_fim: date | None = None
    documento_origem_id: str | None = None


@router.get("/")
async def listar_agentes(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == current_user.empresa_id)
    )
    return [
        {
            "id": str(a.id),
            "codigo_tabela24": a.codigo_tabela24,
            "descricao_agente": a.descricao_agente,
            "nivel_exposicao": a.nivel_exposicao,
            "needs_review": a.needs_review,
            "confidence_score": a.confidence_score,
            "created_by_ai": a.created_by_ai,
        }
        for a in result.scalars()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_agente(
    data: AgenteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    agente = AgenteNocivo(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(agente)
    await db.commit()
    await db.refresh(agente)
    return {"id": str(agente.id), "codigo_tabela24": agente.codigo_tabela24}
