# api/routers/exames_medicos.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date

from api.database import get_db
from api.models.exame_medico import ExameMedico
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class ExameCreate(BaseModel):
    trabalhador_id: str
    tipo_exame: str
    data_exame: date
    data_validade: date | None = None
    medico_nome: str | None = None
    medico_crm: str | None = None
    resultado: str | None = None
    observacoes: str | None = None


@router.get("/")
async def listar_exames(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(ExameMedico).where(ExameMedico.empresa_id == current_user.empresa_id)
    )
    return [
        {
            "id": str(e.id),
            "trabalhador_id": str(e.trabalhador_id),
            "tipo_exame": e.tipo_exame,
            "data_exame": str(e.data_exame),
            "resultado": e.resultado,
        }
        for e in result.scalars()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_exame(
    data: ExameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    exame = ExameMedico(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(exame)
    await db.commit()
    await db.refresh(exame)
    return {"id": str(exame.id), "tipo_exame": exame.tipo_exame}
