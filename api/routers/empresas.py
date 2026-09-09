# api/routers/empresas.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from api.database import get_db
from api.models.empresa import Empresa
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil

router = APIRouter()


class EmpresaCreate(BaseModel):
    razao_social: str
    cnpj: str
    cnae_principal: str
    grau_risco: int | None = None
    regime_tributario: str | None = None


@router.get("/")
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    result = await db.execute(select(Empresa).where(Empresa.ativo == True))
    return [{"id": str(e.id), "razao_social": e.razao_social, "cnpj": e.cnpj, "grau_risco": e.grau_risco} for e in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_empresa(
    data: EmpresaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    empresa = Empresa(**data.model_dump())
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)
    return {"id": str(empresa.id), "razao_social": empresa.razao_social}


@router.get("/{empresa_id}")
async def obter_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {"id": str(empresa.id), "razao_social": empresa.razao_social, "cnpj": empresa.cnpj, "cnae_principal": empresa.cnae_principal, "grau_risco": empresa.grau_risco}


# ---- Módulo 0 / RF-0.07: status do cadastro (bloqueio) ----
@router.get("/{empresa_id}/cadastro-status")
async def cadastro_status(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """RF-0.07: informa se o cadastro da empresa está completo e o que falta.
    Os módulos de cálculo consultam isto antes de calcular; o frontend usa
    para bloquear e exibir a mensagem. Isolamento: usuário só vê a própria empresa."""
    if current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Acesso negado a empresa de outro tenant")
    from api.services.cadastro_completo import verificar_cadastro
    return await verificar_cadastro(empresa_id, db)
