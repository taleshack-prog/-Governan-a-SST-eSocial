# api/routers/empresas.py — SST ESOCIAL GOV
# Adendo 03: o enquadramento e do ESTABELECIMENTO (matriz), nao da empresa (RN-17).
# A empresa guarda identificacao, periodo de apuracao, regime/CPRB por periodo e contato.
import re
from uuid import UUID
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from api.database import get_db
from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.empresa_regime import EmpresaRegime
from api.models.empresa_cprb import EmpresaCprb
from api.models.cnae_enquadramento import CnaeEnquadramento
from api.models.cnae_fpas_sugestao import CnaeFpasSugestao
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil

router = APIRouter()

GRAU_LABEL = {1: "leve", 2: "médio", 3: "grave"}


# ---------------- helpers ----------------
def _cnpj_dv(base: str) -> int:
    pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * p for d, p in zip(base, pesos))
    r = s % 11
    return 0 if r < 2 else 11 - r


def _cnpj_matriz(cnpj_informado: Optional[str]) -> Optional[str]:
    """Matriz = raiz (8 dígitos) + ordem 0001 + dígitos verificadores (RF-0.152)."""
    d = re.sub(r"\D", "", cnpj_informado or "")
    if len(d) < 8:
        return None
    base = d[:8] + "0001"
    dv1 = _cnpj_dv(base)
    dv2 = _cnpj_dv(base + str(dv1))
    return base + str(dv1) + str(dv2)


def _sem_sobreposicao(periodos: list[tuple[date, Optional[date]]]) -> bool:
    """True se os períodos [inicio, fim] (fim None = aberto) não se sobrepõem."""
    ordenados = sorted(periodos, key=lambda p: p[0])
    for i in range(1, len(ordenados)):
        fim_ant = ordenados[i - 1][1] or date.max
        if ordenados[i][0] <= fim_ant:
            return False
    return True


async def _garantir_matriz(empresa: Empresa, db: AsyncSession) -> None:
    """RF-0.152: ao salvar a empresa, garante o estabelecimento matriz e seu enquadramento
    vigente (v1: uma linha, início na abertura/competência, fim em aberto). O enquadramento
    vive em tabela filha por vigência (RN-17), nunca como coluna da empresa."""
    matriz = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa.id, Estabelecimento.posicao == "matriz"
        )
    )).scalars().first()
    if matriz is None:
        matriz = Estabelecimento(
            empresa_id=empresa.id, codigo="MATRIZ", nome=empresa.razao_social or "Matriz",
            cnpj=_cnpj_matriz(empresa.cnpj), cnae=empresa.cnae_principal,
            posicao="matriz", status="ativa", tipo_estabelecimento="CNPJ",
            endereco=empresa.endereco, cidade=empresa.cidade, uf=empresa.uf,
        )
        db.add(matriz)
        await db.flush()
    else:
        if empresa.cnae_principal:
            matriz.cnae = empresa.cnae_principal

    # deriva grau/RAT/FPAS do CNAE (determinístico para o que der; demais ficam nulos)
    grau = rat = fpas = None
    if empresa.cnae_principal:
        ce = (await db.execute(
            select(CnaeEnquadramento).where(CnaeEnquadramento.cnae == empresa.cnae_principal)
        )).scalar_one_or_none()
        if ce:
            grau, rat = ce.grau_risco, ce.aliquota_rat
        try:
            div = int(empresa.cnae_principal[:2])
            sug = (await db.execute(
                select(CnaeFpasSugestao).where(
                    CnaeFpasSugestao.divisao_ini <= div, CnaeFpasSugestao.divisao_fim >= div
                )
            )).scalars().first()
            fpas = sug.fpas_sugerido if sug else None
        except ValueError:
            pass

    inicio = empresa.periodo_apuracao_inicio or getattr(matriz, "data_inicio", None) or date.today()
    enq = (await db.execute(
        select(EstabelecimentoEnquadramento).where(
            EstabelecimentoEnquadramento.estabelecimento_id == matriz.id,
            EstabelecimentoEnquadramento.vigencia_fim.is_(None),
        ).order_by(EstabelecimentoEnquadramento.vigencia_inicio.desc())
    )).scalars().first()
    if enq is None:
        db.add(EstabelecimentoEnquadramento(
            estabelecimento_id=matriz.id, vigencia_inicio=inicio,
            cnae=empresa.cnae_principal, grau_risco=grau, aliquota_rat=rat, codigo_fpas=fpas,
            origem=(empresa.origem_cadastro or "declarado"),
        ))
    else:
        enq.cnae = empresa.cnae_principal
        enq.grau_risco = grau
        enq.aliquota_rat = rat
        if fpas and not enq.codigo_fpas:
            enq.codigo_fpas = fpas


# ---------------- schemas ----------------
class EmpresaCreate(BaseModel):
    razao_social: str
    cnpj: str
    cnae_principal: str | None = None
    regime_tributario: str | None = None


class EmpresaUpdate(BaseModel):
    razao_social: str | None = None
    nome_fantasia: str | None = None
    cnpj: str | None = None
    cnae_principal: str | None = None            # usado p/ semear o enquadramento da matriz
    periodo_apuracao_inicio: date | None = None
    periodo_apuracao_fim: date | None = None
    origem_cadastro: str | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    contato_nome: str | None = None
    contato_email: str | None = None
    contato_telefone: str | None = None


class RegimeItem(BaseModel):
    regime: str
    anexo_simples: str | None = None
    inicio: date
    fim: date | None = None


class CprbItem(BaseModel):
    inicio: date
    fim: date | None = None


# ---------------- CRUD empresa ----------------
@router.get("/")
async def listar_empresas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    result = await db.execute(select(Empresa).where(Empresa.ativo == True))
    return [{"id": str(e.id), "razao_social": e.razao_social, "cnpj": e.cnpj} for e in result.scalars()]


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


# ---- Consulta pública de CNPJ (RF-0.150), via backend + adapter ----
@router.get("/consulta-cnpj/{cnpj}")
async def consulta_cnpj(
    cnpj: str,
    current_user: Usuario = Depends(get_current_user),
):
    """Consulta os dados públicos cadastrais pelo CNPJ raiz. A chamada sai do backend.
    Retorno marcado como 'consultado, não confirmado' — o usuário confirma antes de valer."""
    from api.services.cnpj_lookup import consultar_cnpj, CnpjConsultaError
    try:
        return await consultar_cnpj(cnpj)
    except CnpjConsultaError as e:
        # 422: sem bloquear o fluxo — o front abre manual e marca "declarado"
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/opcoes/fpas")
async def listar_fpas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from api.models.tabela_fpas import TabelaFPAS
    rows = (await db.execute(
        select(TabelaFPAS).where(TabelaFPAS.ativo == True).order_by(TabelaFPAS.codigo_fpas)
    )).scalars().all()
    return [{"codigo": r.codigo_fpas, "descricao": r.descricao, "aliquota_terceiros": float(r.aliquota_terceiros)} for r in rows]


@router.get("/{empresa_id}")
async def obter_empresa(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    # RF-0.159: número de estabelecimentos é contagem derivada (ativos), não campo digitado
    num_estab = (await db.execute(
        select(func.count()).select_from(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa_id, Estabelecimento.status == "ativa"
        )
    )).scalar_one()
    return {
        "id": str(empresa.id),
        "razao_social": empresa.razao_social,
        "nome_fantasia": empresa.nome_fantasia,
        "cnpj": empresa.cnpj,
        "cnae_principal": empresa.cnae_principal,   # semente do enquadramento da matriz
        "periodo_apuracao_inicio": empresa.periodo_apuracao_inicio.isoformat() if empresa.periodo_apuracao_inicio else None,
        "periodo_apuracao_fim": empresa.periodo_apuracao_fim.isoformat() if empresa.periodo_apuracao_fim else None,
        "origem_cadastro": empresa.origem_cadastro,
        "endereco": empresa.endereco,
        "numero": empresa.numero,
        "complemento": empresa.complemento,
        "bairro": empresa.bairro,
        "cidade": empresa.cidade,
        "uf": empresa.uf,
        "cep": empresa.cep,
        "num_estabelecimentos": int(num_estab),
        "contato_nome": empresa.contato_nome,
        "contato_email": empresa.contato_email,
        "contato_telefone": empresa.contato_telefone,
    }


@router.get("/{empresa_id}/cadastro-status")
async def cadastro_status(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a empresa de outro tenant")
    from api.services.cadastro_completo import verificar_cadastro
    return await verificar_cadastro(empresa_id, db)


@router.put("/{empresa_id}")
async def atualizar_empresa(
    empresa_id: UUID,
    data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(empresa, k, v)
    await _garantir_matriz(empresa, db)   # RF-0.152
    await db.commit()
    return {"id": str(empresa.id), "ok": True}


# ---- Espelho do enquadramento da matriz (RF-0.155) ----
@router.get("/{empresa_id}/matriz-enquadramento")
async def matriz_enquadramento(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    matriz = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == empresa_id, Estabelecimento.posicao == "matriz"
        )
    )).scalars().first()
    if matriz is None:
        return {"existe": False}
    enq = (await db.execute(
        select(EstabelecimentoEnquadramento).where(
            EstabelecimentoEnquadramento.estabelecimento_id == matriz.id,
            EstabelecimentoEnquadramento.vigencia_fim.is_(None),
        ).order_by(EstabelecimentoEnquadramento.vigencia_inicio.desc())
    )).scalars().first()
    if enq is None:
        return {"existe": True, "estabelecimento_id": str(matriz.id), "enquadramento": None}
    return {
        "existe": True,
        "estabelecimento_id": str(matriz.id),
        "enquadramento": {
            "cnae": enq.cnae,
            "grau_risco": enq.grau_risco,
            "grau_label": GRAU_LABEL.get(enq.grau_risco or 0, ""),
            "aliquota_rat": float(enq.aliquota_rat) if enq.aliquota_rat is not None else None,
            "codigo_fpas": enq.codigo_fpas,
            "vigencia_inicio": enq.vigencia_inicio.isoformat() if enq.vigencia_inicio else None,
            "origem": enq.origem,
            "confirmado": enq.confirmado,
        },
    }


# ---- Regime tributário por período (RF-0.156) ----
@router.get("/{empresa_id}/regime")
async def listar_regime(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    rows = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id).order_by(EmpresaRegime.inicio)
    )).scalars().all()
    return [{"regime": r.regime, "anexo_simples": r.anexo_simples,
             "inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None} for r in rows]


@router.put("/{empresa_id}/regime")
async def salvar_regime(
    empresa_id: UUID,
    data: List[RegimeItem],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos de regime. Valida sem sobreposição (RF-0.156)."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    for it in data:
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período de regime com fim anterior ao início.")
    if not _sem_sobreposicao([(it.inicio, it.fim) for it in data]):
        raise HTTPException(status_code=422, detail="Períodos de regime se sobrepõem.")
    existentes = (await db.execute(
        select(EmpresaRegime).where(EmpresaRegime.empresa_id == empresa_id)
    )).scalars().all()
    for e in existentes:
        await db.delete(e)
    for it in data:
        db.add(EmpresaRegime(empresa_id=empresa_id, regime=it.regime, anexo_simples=it.anexo_simples,
                             inicio=it.inicio, fim=it.fim))
    await db.commit()
    return {"ok": True, "total": len(data)}


# ---- CPRB por período (RF-0.157) ----
@router.get("/{empresa_id}/cprb")
async def listar_cprb(
    empresa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    rows = (await db.execute(
        select(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id).order_by(EmpresaCprb.inicio)
    )).scalars().all()
    return [{"inicio": r.inicio.isoformat(), "fim": r.fim.isoformat() if r.fim else None} for r in rows]


@router.put("/{empresa_id}/cprb")
async def salvar_cprb(
    empresa_id: UUID,
    data: List[CprbItem],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de períodos de CPRB. Valida sem sobreposição (RF-0.157)."""
    if str(empresa_id) != str(current_user.empresa_id):
        raise HTTPException(status_code=403, detail="Sem permissão para esta empresa")
    for it in data:
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Período de CPRB com fim anterior ao início.")
    if not _sem_sobreposicao([(it.inicio, it.fim) for it in data]):
        raise HTTPException(status_code=422, detail="Períodos de CPRB se sobrepõem.")
    existentes = (await db.execute(
        select(EmpresaCprb).where(EmpresaCprb.empresa_id == empresa_id)
    )).scalars().all()
    for e in existentes:
        await db.delete(e)
    for it in data:
        db.add(EmpresaCprb(empresa_id=empresa_id, inicio=it.inicio, fim=it.fim))
    await db.commit()
    return {"ok": True, "total": len(data)}
