# api/routers/estabelecimentos.py — SST ESOCIAL GOV
# Módulo 0 (v2) — Cadastro de Estabelecimento
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel

from api.database import get_db
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_fap import EstabelecimentoFAP
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil

router = APIRouter()

TIPOS_ESTABELECIMENTO = ("CNPJ", "CNO")
POSICOES = ("matriz", "filial")
STATUS_VALIDOS = ("ativa", "paralisada", "encerrada")
GRAUS_RISCO = (1, 2, 3)


class EstabelecimentoCreate(BaseModel):
    codigo: str
    nome: str
    tipo_estabelecimento: str = "CNPJ"
    posicao: str = "filial"
    cnpj: str | None = None
    identificador: str | None = None
    cnae: str | None = None
    grau_risco: int | None = None
    aliquota_rat: float | None = None
    fpas: str | None = None
    atividade_descrita: str | None = None
    status: str = "ativa"
    cidade: str | None = None
    uf: str | None = None


@router.get("/")
async def listar_estabelecimentos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Estabelecimento)
        .where(Estabelecimento.empresa_id == current_user.empresa_id)
        .order_by(Estabelecimento.codigo)
    )
    return [
        {
            "id": str(e.id),
            "codigo": e.codigo,
            "nome": e.nome,
            "tipo_estabelecimento": e.tipo_estabelecimento,
            "posicao": e.posicao,
            "cnpj": e.cnpj,
            "identificador": e.identificador,
            "cnae": e.cnae,
            "grau_risco": e.grau_risco,
            "aliquota_rat": float(e.aliquota_rat) if e.aliquota_rat is not None else None,
            "fpas": e.fpas,
            "atividade_descrita": e.atividade_descrita,
            "status": e.status,
            "cidade": e.cidade,
            "uf": e.uf,
        }
        for e in result.scalars()
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_estabelecimento(
    data: EstabelecimentoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if data.tipo_estabelecimento not in TIPOS_ESTABELECIMENTO:
        raise HTTPException(status_code=422, detail="tipo_estabelecimento deve ser CNPJ ou CNO")
    if data.posicao not in POSICOES:
        raise HTTPException(status_code=422, detail="posicao deve ser matriz ou filial")
    if data.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=422, detail="status deve ser ativa, paralisada ou encerrada")
    if data.grau_risco is not None and data.grau_risco not in GRAUS_RISCO:
        raise HTTPException(status_code=422, detail="grau_risco deve ser 1, 2 ou 3")

    existente = await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == current_user.empresa_id,
            Estabelecimento.codigo == data.codigo,
        )
    )
    if existente.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Já existe um estabelecimento com este código")

    estabelecimento = Estabelecimento(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(estabelecimento)
    await db.commit()
    await db.refresh(estabelecimento)

    return {
        "id": str(estabelecimento.id),
        "codigo": estabelecimento.codigo,
        "nome": estabelecimento.nome,
        "tipo_estabelecimento": estabelecimento.tipo_estabelecimento,
        "posicao": estabelecimento.posicao,
        "cnpj": estabelecimento.cnpj,
        "identificador": estabelecimento.identificador,
        "cnae": estabelecimento.cnae,
        "grau_risco": estabelecimento.grau_risco,
        "aliquota_rat": float(estabelecimento.aliquota_rat) if estabelecimento.aliquota_rat is not None else None,
        "fpas": estabelecimento.fpas,
        "atividade_descrita": estabelecimento.atividade_descrita,
        "status": estabelecimento.status,
        "cidade": estabelecimento.cidade,
        "uf": estabelecimento.uf,
    }


class FapAnoIn(BaseModel):
    ano: int
    fap: float


@router.get("/{estab_id}/fap")
async def listar_fap(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista os FAPs por ano do estabelecimento (para a tela de histórico)."""
    rows = (await db.execute(
        select(EstabelecimentoFAP).where(EstabelecimentoFAP.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoFAP.ano_vigencia)
    )).scalars().all()
    return [{"ano": r.ano_vigencia, "fap": float(r.valor_fap)} for r in rows]


@router.put("/{estab_id}/fap")
async def salvar_fap(
    estab_id: UUID,
    faps: list[FapAnoIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Salva/atualiza os FAPs por ano (upsert por ano_vigencia). Roteiro Módulo 0/4:
    o cálculo retroativo usa o FAP de cada ano."""
    for item in faps:
        existe = (await db.execute(
            select(EstabelecimentoFAP).where(
                EstabelecimentoFAP.estabelecimento_id == estab_id,
                EstabelecimentoFAP.ano_vigencia == item.ano,
            )
        )).scalar_one_or_none()
        if existe:
            existe.valor_fap = item.fap
        else:
            db.add(EstabelecimentoFAP(estabelecimento_id=estab_id, ano_vigencia=item.ano, valor_fap=item.fap))
    await db.commit()
    return {"ok": True, "salvos": len(faps)}
