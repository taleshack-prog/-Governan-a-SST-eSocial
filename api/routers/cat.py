# api/routers/cat.py — SST ESOCIAL GOV
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from api.database import get_db
from api.models.cat_registro import CatRegistro
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class CatCreate(BaseModel):
    trabalhador_id: str
    data_acidente: datetime
    tipo_cat: str = "inicial"
    local_acidente: str | None = None
    descricao: str | None = None
    cid_principal: str | None = None
    agente_causador: str | None = None
    afastamento: bool = False
    dias_afastamento: int | None = None


@router.get("/")
async def listar_cats(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(CatRegistro).where(CatRegistro.empresa_id == current_user.empresa_id)
    )
    return [
        {
            "id": str(c.id),
            "trabalhador_id": str(c.trabalhador_id),
            "tipo_cat": c.tipo_cat,
            "data_acidente": str(c.data_acidente),
            "status_esocial": c.status_esocial,
        }
        for c in result.scalars()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def registrar_cat(
    data: CatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cat = CatRegistro(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"id": str(cat.id), "status_esocial": cat.status_esocial}
