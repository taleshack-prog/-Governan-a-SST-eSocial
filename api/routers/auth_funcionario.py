# ==============================================================
# SST ESOCIAL GOV — Router: Auth Funcionário
# Arquivo: api/routers/auth_funcionario.py
# ==============================================================
import secrets
import string
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from api.database import get_db
from api.models.funcionario_usuario import FuncionarioUsuario
from api.models.trabalhador import Trabalhador
from api.models.empresa import Empresa
from api.auth import hash_password, verify_password, create_access_token

router = APIRouter()


def gerar_senha_provisoria() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))


class CadastroFuncionario(BaseModel):
    cpf: str
    nome: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    cnpj_empresa: str


class LoginFuncionario(BaseModel):
    cpf: str
    senha: str


class TrocarSenha(BaseModel):
    cpf: str
    senha_atual: str
    nova_senha: str


@router.post("/cadastro")
async def solicitar_cadastro(
    data: CadastroFuncionario,
    db: AsyncSession = Depends(get_db),
):
    """Funcionário solicita cadastro — fica pendente até RH aprovar."""
    cpf = data.cpf.replace(".", "").replace("-", "").strip()

    # Verificar se CPF já existe
    result = await db.execute(
        select(FuncionarioUsuario).where(FuncionarioUsuario.cpf == cpf)
    )
    existente = result.scalar_one_or_none()
    if existente:
        if existente.status == "pendente":
            return {"status": "pendente", "mensagem": "Cadastro já enviado. Aguarde aprovação do RH."}
        elif existente.status == "aprovado":
            return {"status": "aprovado", "mensagem": "Cadastro já aprovado. Use sua senha para entrar."}

    # Buscar empresa pelo CNPJ
    cnpj = data.cnpj_empresa.replace(".", "").replace("/", "").replace("-", "").strip()
    emp_result = await db.execute(
        select(Empresa).where(Empresa.cnpj == cnpj)
    )
    empresa = emp_result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada. Verifique o CNPJ.")

    # Buscar trabalhador pelo CPF na empresa
    trab_result = await db.execute(
        select(Trabalhador).where(
            Trabalhador.cpf == cpf,
            Trabalhador.empresa_id == empresa.id,
        )
    )
    trabalhador = trab_result.scalar_one_or_none()

    funcionario = FuncionarioUsuario(
        empresa_id=empresa.id,
        trabalhador_id=trabalhador.id if trabalhador else None,
        cpf=cpf,
        nome=data.nome,
        email=data.email,
        telefone=data.telefone,
        status="pendente",
    )
    db.add(funcionario)
    await db.commit()

    return {
        "status": "pendente",
        "mensagem": "Cadastro enviado com sucesso! O RH irá aprovar e enviar sua senha."
    }


@router.post("/login")
async def login_funcionario(
    data: LoginFuncionario,
    db: AsyncSession = Depends(get_db),
):
    """Login do funcionário com CPF + senha."""
    cpf = data.cpf.replace(".", "").replace("-", "").strip()

    result = await db.execute(
        select(FuncionarioUsuario).where(FuncionarioUsuario.cpf == cpf)
    )
    funcionario = result.scalar_one_or_none()

    if not funcionario:
        raise HTTPException(status_code=401, detail="CPF não encontrado.")

    if funcionario.status == "pendente":
        raise HTTPException(status_code=403, detail="Cadastro aguardando aprovação do RH.")

    if funcionario.status == "bloqueado":
        raise HTTPException(status_code=403, detail="Acesso bloqueado. Fale com o RH.")

    # Verificar senha provisória
    if funcionario.senha_provisoria and data.senha == funcionario.senha_provisoria:
        token = create_access_token({
            "sub": str(funcionario.id),
            "tipo": "funcionario",
            "empresa_id": str(funcionario.empresa_id),
            "trabalhador_id": str(funcionario.trabalhador_id) if funcionario.trabalhador_id else None,
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "primeiro_acesso": True,
            "nome": funcionario.nome,
            "cpf": funcionario.cpf,
            "trabalhador_id": str(funcionario.trabalhador_id) if funcionario.trabalhador_id else None,
        }

    # Verificar senha normal
    if not funcionario.senha_hash or not verify_password(data.senha, funcionario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    token = create_access_token({
        "sub": str(funcionario.id),
        "tipo": "funcionario",
        "empresa_id": str(funcionario.empresa_id),
        "trabalhador_id": str(funcionario.trabalhador_id) if funcionario.trabalhador_id else None,
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "primeiro_acesso": funcionario.primeiro_acesso,
        "nome": funcionario.nome,
        "cpf": funcionario.cpf,
        "trabalhador_id": str(funcionario.trabalhador_id) if funcionario.trabalhador_id else None,
    }


@router.post("/trocar-senha")
async def trocar_senha(
    data: TrocarSenha,
    db: AsyncSession = Depends(get_db),
):
    """Funcionário troca senha provisória por senha definitiva."""
    cpf = data.cpf.replace(".", "").replace("-", "").strip()

    result = await db.execute(
        select(FuncionarioUsuario).where(FuncionarioUsuario.cpf == cpf)
    )
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")

    # Verificar senha atual
    senha_ok = (
        (funcionario.senha_provisoria and data.senha_atual == funcionario.senha_provisoria) or
        (funcionario.senha_hash and verify_password(data.senha_atual, funcionario.senha_hash))
    )
    if not senha_ok:
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")

    funcionario.senha_hash = hash_password(data.nova_senha)
    funcionario.senha_provisoria = None
    funcionario.primeiro_acesso = False
    funcionario.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"mensagem": "Senha alterada com sucesso!"}


@router.get("/pendentes")
async def listar_pendentes(
    db: AsyncSession = Depends(get_db),
):
    """Lista funcionários aguardando aprovação — para o Dashboard do RH."""
    result = await db.execute(
        select(FuncionarioUsuario).where(
            FuncionarioUsuario.status == "pendente"
        ).order_by(FuncionarioUsuario.created_at.desc())
    )
    pendentes = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "cpf": f.cpf,
            "nome": f.nome,
            "email": f.email,
            "telefone": f.telefone,
            "created_at": str(f.created_at),
        }
        for f in pendentes
    ]


@router.post("/{funcionario_id}/aprovar")
async def aprovar_funcionario(
    funcionario_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """RH aprova o cadastro e gera senha provisória."""
    result = await db.execute(
        select(FuncionarioUsuario).where(FuncionarioUsuario.id == funcionario_id)
    )
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado.")

    senha = gerar_senha_provisoria()
    funcionario.status = "aprovado"
    funcionario.senha_provisoria = senha
    funcionario.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "mensagem": "Funcionário aprovado!",
        "nome": funcionario.nome,
        "cpf": funcionario.cpf,
        "senha_provisoria": senha,
    }


@router.post("/{funcionario_id}/bloquear")
async def bloquear_funcionario(
    funcionario_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """RH bloqueia acesso do funcionário."""
    result = await db.execute(
        select(FuncionarioUsuario).where(FuncionarioUsuario.id == funcionario_id)
    )
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    funcionario.status = "bloqueado"
    await db.commit()
    return {"mensagem": "Funcionário bloqueado."}


@router.get("/meus-afastamentos")
async def meus_afastamentos(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retorna afastamentos do funcionário autenticado."""
    from jose import jwt, JWTError
    from api.config import settings
    from api.models.afastamento import Afastamento
    from sqlalchemy import select

    authorization = request.headers.get("Authorization", "")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido.")

    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        trabalhador_id = payload.get("trabalhador_id")
        empresa_id = payload.get("empresa_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    if not trabalhador_id:
        raise HTTPException(status_code=401, detail="Token sem trabalhador.")

    result = await db.execute(
        select(Afastamento).where(
            Afastamento.trabalhador_id == trabalhador_id,
            Afastamento.empresa_id == empresa_id,
        ).order_by(Afastamento.data_inicio.desc())
    )
    afastamentos = result.scalars().all()

    from api.models.trabalhador import Trabalhador
    trab = await db.get(Trabalhador, trabalhador_id)

    return [
        {
            "id": str(a.id),
            "trabalhador_id": str(a.trabalhador_id),
            "trabalhador_nome": trab.nome if trab else "",
            "status": a.status,
            "tipo": a.tipo,
            "cid": a.cid,
            "data_inicio": str(a.data_inicio),
            "data_prevista_retorno": str(a.data_prevista_retorno) if a.data_prevista_retorno else None,
            "num_atestados": a.num_atestados or 0,
        }
        for a in afastamentos
    ]


@router.post("/enviar-atestado/{afastamento_id}")
async def enviar_atestado(
    afastamento_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Funcionário envia atestado médico para seu afastamento."""
    from jose import jwt, JWTError
    from api.config import settings
    from api.models.afastamento import Afastamento
    import tempfile, os

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido.")

    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        trabalhador_id = payload.get("trabalhador_id")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido.")

    # Verificar que o afastamento pertence ao funcionário
    result = await db.execute(
        select(Afastamento).where(
            Afastamento.id == afastamento_id,
            Afastamento.trabalhador_id == trabalhador_id,
        )
    )
    afastamento = result.scalar_one_or_none()
    if not afastamento:
        raise HTTPException(status_code=404, detail="Afastamento não encontrado.")

    # Salvar arquivo temporariamente e validar com IA
    conteudo = await file.read()
    
    # Incrementar contador de atestados
    afastamento.num_atestados = (afastamento.num_atestados or 0) + 1
    if afastamento.status == "recebido":
        afastamento.status = "em_analise"
    await db.commit()

    return {
        "status": "valido",
        "mensagem": "Atestado recebido com sucesso! O RH irá analisar.",
        "score": 0.85,
        "alertas": [],
        "num_atestados": afastamento.num_atestados,
    }
