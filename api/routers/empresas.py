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

class EmpresaUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    cnpj: str | None = None
    cnae_principal: str | None = None
    regime_tributario: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    codigo_fpas: str | None = None
    grau_risco: int | None = None
    grau_risco_declarado: int | None = None
    rat_aplicado: float | None = None
    anexo_simples: str | None = None
    apura_cprb: bool | None = None
    qtd_estabelecimentos: int | None = None
    contato_nome: str | None = None
    contato_email: str | None = None
    contato_telefone: str | None = None


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
    # P0-1: devolver TODOS os campos editáveis. Antes só retornava 5 campos, então a
    # tela reabria FPAS/regime/anexo/CPRB/RAT vazios e o PUT regravava vazio (perda de dados).
    return {
        "id": str(empresa.id),
        "razao_social": empresa.razao_social,
        "nome_fantasia": empresa.nome_fantasia,
        "cnpj": empresa.cnpj,
        "cnae_principal": empresa.cnae_principal,
        "regime_tributario": empresa.regime_tributario,
        "endereco": empresa.endereco,
        "cidade": empresa.cidade,
        "uf": empresa.uf,
        "cep": empresa.cep,
        "codigo_fpas": empresa.codigo_fpas,
        "anexo_simples": empresa.anexo_simples,
        "apura_cprb": empresa.apura_cprb,
        "grau_risco": empresa.grau_risco,
        "grau_risco_declarado": empresa.grau_risco_declarado,
        "rat_aplicado": float(empresa.rat_aplicado) if empresa.rat_aplicado is not None else None,
        "qtd_estabelecimentos": empresa.qtd_estabelecimentos,
        "possui_sesmt": empresa.possui_sesmt,
        "possui_cipa": empresa.possui_cipa,
        "contato_nome": empresa.contato_nome,
        "contato_email": empresa.contato_email,
        "contato_telefone": empresa.contato_telefone,
    }


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


@router.put("/{empresa_id}")
async def atualizar_empresa(
    empresa_id: UUID,
    data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Atualiza os dados da empresa. Isolamento: só a própria empresa do usuário."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    campos = data.model_dump(exclude_unset=True)
    for k, v in campos.items():
        setattr(empresa, k, v)
    await db.commit()
    await db.refresh(empresa)
    return {"id": str(empresa.id), "ok": True}


@router.get("/opcoes/fpas")
async def listar_fpas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista os códigos FPAS para o dropdown do cadastro (código, descrição, % Terceiros)."""
    from api.models.tabela_fpas import TabelaFPAS
    rows = (await db.execute(
        select(TabelaFPAS).where(TabelaFPAS.ativo == True).order_by(TabelaFPAS.codigo_fpas)
    )).scalars().all()
    return [{"codigo": r.codigo_fpas, "descricao": r.descricao, "aliquota_terceiros": float(r.aliquota_terceiros)} for r in rows]
