# api/routers/rubricas.py — SST ESOCIAL GOV
# Etapa 3 (v2) / fase 3A-2 — CRUD de rubricas da empresa.
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from api.database import get_db
from api.models.rubrica_empresa import RubricaEmpresa
from api.models.estabelecimento import Estabelecimento
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class RubricaCreate(BaseModel):
    estabelecimento_id: UUID
    descricao: str
    codigo_esocial: str | None = None
    natureza_declarada: str | None = None
    incide_inss_praticado: bool = True
    incide_fgts_praticado: bool = True
    valor_mensal: float = 0


def _to_dict(r: RubricaEmpresa) -> dict:
    return {
        "id": str(r.id),
        "estabelecimento_id": str(r.estabelecimento_id),
        "codigo_esocial": r.codigo_esocial,
        "descricao": r.descricao,
        "natureza_declarada": r.natureza_declarada,
        "incide_inss_praticado": r.incide_inss_praticado,
        "incide_fgts_praticado": r.incide_fgts_praticado,
        "valor_mensal": float(r.valor_mensal) if r.valor_mensal is not None else 0.0,
        "status_conciliacao": r.status_conciliacao,
        "dicionario_rubrica_id": str(r.dicionario_rubrica_id) if r.dicionario_rubrica_id else None,
    }


async def _estab_da_empresa(estab_id: UUID, empresa_id: UUID, db: AsyncSession) -> Estabelecimento:
    estab = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id,
            Estabelecimento.empresa_id == empresa_id,
        )
    )).scalar_one_or_none()
    if estab is None:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado nesta empresa")
    return estab


@router.get("/")
async def listar_rubricas(
    estabelecimento_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == current_user.empresa_id)
    )).scalars().all()
    if not estabs:
        return []
    q = select(RubricaEmpresa).where(RubricaEmpresa.estabelecimento_id.in_(estabs))
    if estabelecimento_id is not None:
        q = q.where(RubricaEmpresa.estabelecimento_id == estabelecimento_id)
    result = await db.execute(q.order_by(RubricaEmpresa.descricao))
    return [_to_dict(r) for r in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_rubrica(
    data: RubricaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _estab_da_empresa(data.estabelecimento_id, current_user.empresa_id, db)
    rubrica = RubricaEmpresa(**data.model_dump())
    db.add(rubrica)
    await db.commit()
    await db.refresh(rubrica)
    return _to_dict(rubrica)
