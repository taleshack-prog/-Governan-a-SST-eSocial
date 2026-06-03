# ==============================================================
# RADAR PREVIDENCIÁRIO — Router: Admin (Multi-empresa)
# Arquivo: api/routers/admin.py
# ==============================================================
from uuid import UUID
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from api.database import get_db
from api.models.empresa import Empresa
from api.models.usuario import Usuario
from api.models.trabalhador import Trabalhador
from api.models.afastamento import Afastamento
from api.auth import get_current_user, hash_password

router = APIRouter()

PLANOS = {
    "trial":        {"label": "Trial",        "dias": 15,  "max_trab": 5,    "preco": 0},
    "basico":       {"label": "Básico",       "dias": 365, "max_trab": 50,   "preco": 297},
    "profissional": {"label": "Profissional", "dias": 365, "max_trab": 200,  "preco": 697},
    "enterprise":   {"label": "Enterprise",   "dias": 365, "max_trab": 9999, "preco": 1497},
}


class CadastroEmpresa(BaseModel):
    razao_social: str
    cnpj: str
    cnae_principal: str
    grau_risco: int = 1
    plano: str = "trial"
    contato_nome: str
    contato_email: str
    contato_telefone: Optional[str] = None
    admin_senha: str = "Radar@2026"


class AtualizarPlano(BaseModel):
    plano: str
    dias_adicionais: Optional[int] = 365


@router.get("/empresas")
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista todas as empresas — apenas superadmin."""
    result = await db.execute(
        select(Empresa).order_by(Empresa.created_at.desc())
    )
    empresas = result.scalars().all()

    lista = []
    for e in empresas:
        # Contar trabalhadores
        trab_count = await db.execute(
            select(func.count(Trabalhador.id)).where(Trabalhador.empresa_id == e.id)
        )
        n_trab = trab_count.scalar() or 0

        # Contar afastamentos ativos
        afas_count = await db.execute(
            select(func.count(Afastamento.id)).where(
                Afastamento.empresa_id == e.id,
                Afastamento.status != "encerrado"
            )
        )
        n_afas = afas_count.scalar() or 0

        lista.append({
            "id": str(e.id),
            "razao_social": e.razao_social,
            "cnpj": e.cnpj,
            "cnae_principal": e.cnae_principal,
            "grau_risco": e.grau_risco,
            "plano": e.plano or "trial",
            "plano_expira_em": str(e.plano_expira_em) if e.plano_expira_em else None,
            "ativo": e.ativo,
            "contato_nome": e.contato_nome,
            "contato_email": e.contato_email,
            "contato_telefone": e.contato_telefone,
            "n_trabalhadores": n_trab,
            "n_afastamentos_ativos": n_afas,
            "created_at": str(e.created_at),
        })

    return lista


@router.post("/empresas")
async def cadastrar_empresa(
    data: CadastroEmpresa,
    db: AsyncSession = Depends(get_db),
):
    """Cadastra nova empresa cliente."""
    cnpj = data.cnpj.replace(".", "").replace("/", "").replace("-", "").strip()

    # Verificar CNPJ duplicado
    result = await db.execute(select(Empresa).where(Empresa.cnpj == cnpj))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado.")

    plano_cfg = PLANOS.get(data.plano, PLANOS["trial"])
    expira = date.today() + timedelta(days=plano_cfg["dias"])

    empresa = Empresa(
        razao_social=data.razao_social,
        cnpj=cnpj,
        cnae_principal=data.cnae_principal,
        grau_risco=data.grau_risco,
        plano=data.plano,
        plano_expira_em=expira,
        max_trabalhadores=plano_cfg["max_trab"],
        contato_nome=data.contato_nome,
        contato_email=data.contato_email,
        contato_telefone=data.contato_telefone,
        ativo=True,
    )
    db.add(empresa)
    await db.flush()

    # Criar usuário admin da empresa
    usuario = Usuario(
        empresa_id=empresa.id,
        nome=data.contato_nome,
        email=data.contato_email,
        senha_hash=hash_password(data.admin_senha),
        perfil="admin",
        ativo=True,
    )
    db.add(usuario)
    await db.commit()

    return {
        "mensagem": "Empresa cadastrada com sucesso!",
        "empresa_id": str(empresa.id),
        "plano": data.plano,
        "expira_em": str(expira),
        "admin_email": data.contato_email,
        "admin_senha": data.admin_senha,
    }


@router.patch("/empresas/{empresa_id}/plano")
async def atualizar_plano(
    empresa_id: UUID,
    data: AtualizarPlano,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Atualiza plano de uma empresa."""
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")

    plano_cfg = PLANOS.get(data.plano, PLANOS["trial"])
    empresa.plano = data.plano
    empresa.plano_expira_em = date.today() + timedelta(days=data.dias_adicionais or 365)
    empresa.max_trabalhadores = plano_cfg["max_trab"]
    await db.commit()

    return {"mensagem": "Plano atualizado!", "plano": data.plano}


@router.patch("/empresas/{empresa_id}/ativar")
async def ativar_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Não encontrada.")
    empresa.ativo = not empresa.ativo
    await db.commit()
    return {"ativo": empresa.ativo}


@router.get("/planos")
async def listar_planos():
    return PLANOS
