# api/routers/trabalhadores.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date
from typing import Optional
from api.database import get_db, set_tenant
from api.models.trabalhador import Trabalhador
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()

class TrabalhadorCreate(BaseModel):
    cpf: str
    nome: str
    data_nascimento: Optional[date] = None
    sexo: Optional[str] = None
    pis_pasep: Optional[str] = None
    cargo: Optional[str] = None
    setor: Optional[str] = None
    matricula: Optional[str] = None
    data_admissao: Optional[date] = None
    ges: Optional[str] = None

def trab_to_dict(t: Trabalhador) -> dict:
    return {
        "id": str(t.id),
        "nome": t.nome,
        "cpf": t.cpf,
        "sexo": t.sexo,
        "pis_pasep": t.pis_pasep,
        "cargo": t.cargo,
        "setor": t.setor,
        "matricula": t.matricula,
        "data_admissao": str(t.data_admissao) if t.data_admissao else None,
        "data_nascimento": str(t.data_nascimento) if t.data_nascimento else None,
        "ges": t.ges,
    }

@router.get("/")
async def listar_trabalhadores(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == current_user.empresa_id)
        .order_by(Trabalhador.nome)
    )
    return [trab_to_dict(t) for t in result.scalars()]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_trabalhador(
    data: TrabalhadorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    trab = Trabalhador(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(trab)
    await db.commit()
    await db.refresh(trab)
    return trab_to_dict(trab)

@router.get("/{trab_id}")
async def obter_trabalhador(
    trab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Trabalhador).where(
            Trabalhador.id == trab_id,
            Trabalhador.empresa_id == current_user.empresa_id,
        )
    )
    trab = result.scalar_one_or_none()
    if not trab:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")
    return trab_to_dict(trab)

@router.patch("/{trab_id}")
async def atualizar_trabalhador(
    trab_id: UUID,
    data: TrabalhadorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Trabalhador).where(
            Trabalhador.id == trab_id,
            Trabalhador.empresa_id == current_user.empresa_id,
        )
    )
    trab = result.scalar_one_or_none()
    if not trab:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(trab, field, value)
    await db.commit()
    await db.refresh(trab)
    return trab_to_dict(trab)
