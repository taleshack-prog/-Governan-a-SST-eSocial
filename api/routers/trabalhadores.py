# api/routers/trabalhadores.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date

from api.database import get_db
from api.models.trabalhador import Trabalhador
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class TrabalhadorCreate(BaseModel):
    cpf: str
    nome: str
    data_nascimento: date | None = None
    sexo: str | None = None
    pis_pasep: str | None = None


@router.get("/")
async def listar_trabalhadores(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == current_user.empresa_id)
    )
    return [{"id": str(t.id), "nome": t.nome, "cpf": t.cpf} for t in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_trabalhador(
    data: TrabalhadorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    trab = Trabalhador(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(trab)
    await db.commit()
    await db.refresh(trab)
    return {"id": str(trab.id), "nome": trab.nome}


@router.get("/{trab_id}")
async def obter_trabalhador(
    trab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Trabalhador).where(
            Trabalhador.id == trab_id,
            Trabalhador.empresa_id == current_user.empresa_id,
        )
    )
    trab = result.scalar_one_or_none()
    if not trab:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")
    return {"id": str(trab.id), "nome": trab.nome, "cpf": trab.cpf, "pis_pasep": trab.pis_pasep}
