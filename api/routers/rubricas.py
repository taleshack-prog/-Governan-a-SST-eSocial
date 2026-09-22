# api/routers/rubricas.py — SST ESOCIAL GOV
# Etapa 3 (v2) / fase 3A-2 — CRUD de rubricas da empresa.
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from api.database import get_db
from api.models.rubrica_empresa import RubricaEmpresa
from api.models.estabelecimento import Estabelecimento
from api.models.dicionario_rubrica import DicionarioRubrica
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil

router = APIRouter()


class RubricaCreate(BaseModel):
    estabelecimento_id: UUID
    descricao: str
    codigo_esocial: str | None = None
    natureza_declarada: str | None = None
    incide_inss_praticado: bool = True
    incide_fgts_praticado: bool = True
    valor_mensal: float = 0


def _to_dict(r: RubricaEmpresa) -> dict:
    return {
        "id": str(r.id),
        "estabelecimento_id": str(r.estabelecimento_id),
        "codigo_esocial": r.codigo_esocial,
        "descricao": r.descricao,
        "natureza_declarada": r.natureza_declarada,
        "incide_inss_praticado": r.incide_inss_praticado,
        "incide_fgts_praticado": r.incide_fgts_praticado,
        "valor_mensal": float(r.valor_mensal) if r.valor_mensal is not None else 0.0,
        "status_conciliacao": r.status_conciliacao,
        "dicionario_rubrica_id": str(r.dicionario_rubrica_id) if r.dicionario_rubrica_id else None,
    }


async def _estab_da_empresa(estab_id: UUID, empresa_id: UUID, db: AsyncSession) -> Estabelecimento:
    estab = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id,
            Estabelecimento.empresa_id == empresa_id,
        )
    )).scalar_one_or_none()
    if estab is None:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado nesta empresa")
    return estab


@router.get("/")
async def listar_rubricas(
    estabelecimento_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == current_user.empresa_id)
    )).scalars().all()
    if not estabs:
        return []
    q = select(RubricaEmpresa).where(RubricaEmpresa.estabelecimento_id.in_(estabs))
    if estabelecimento_id is not None:
        q = q.where(RubricaEmpresa.estabelecimento_id == estabelecimento_id)
    result = await db.execute(q.order_by(RubricaEmpresa.descricao))
    return [_to_dict(r) for r in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_rubrica(
    data: RubricaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _estab_da_empresa(data.estabelecimento_id, current_user.empresa_id, db)
    rubrica = RubricaEmpresa(**data.model_dump())
    db.add(rubrica)
    await db.commit()
    await db.refresh(rubrica)
    return _to_dict(rubrica)


# ===================== FILA DE CLASSIFICACAO MANUAL (Caixa 3) =====================
class ClassificarIn(BaseModel):
    classificacao: str          # 'incide' | 'nao_incide'
    justificativa: str | None = None


@router.get("/fila-classificacao")
async def fila_classificacao(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Rubricas condicionais (Caixa 3) ainda sem decisao manual, isoladas por empresa."""
    estabs = (await db.execute(
        select(Estabelecimento.id, Estabelecimento.nome).where(
            Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).all()
    if not estabs:
        return []
    estab_ids = [e[0] for e in estabs]
    nomes = {e[0]: e[1] for e in estabs}

    rows = (await db.execute(
        select(RubricaEmpresa, DicionarioRubrica)
        .join(DicionarioRubrica, RubricaEmpresa.dicionario_rubrica_id == DicionarioRubrica.id)
        .where(
            RubricaEmpresa.estabelecimento_id.in_(estab_ids),
            DicionarioRubrica.tratamento_correto == "condicional",
            RubricaEmpresa.classificacao_manual.is_(None),
        )
        .order_by(RubricaEmpresa.descricao)
    )).all()

    pode_fundamento = current_user.perfil in ("admin", "advogada")
    out = []
    for r, dic in rows:
        item = {
            "id": str(r.id),
            "estabelecimento_id": str(r.estabelecimento_id),
            "estabelecimento_nome": nomes.get(r.estabelecimento_id),
            "descricao": r.descricao,
            "codigo_esocial": r.codigo_esocial,
            "valor_mensal": float(r.valor_mensal) if r.valor_mensal is not None else 0.0,
            "incide_inss_praticado": r.incide_inss_praticado,
            "rubrica_dicionario": dic.descricao,
            "condicao": dic.condicao,
            "grau_seguranca": dic.grau_seguranca,
        }
        if pode_fundamento:
            item["fundamento"] = dic.fundamento
        out.append(item)
    return out


@router.put("/{rubrica_id}/classificar")
async def classificar_rubrica(
    rubrica_id: UUID,
    data: ClassificarIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("advogada")),
):
    if data.classificacao not in ("incide", "nao_incide"):
        raise HTTPException(status_code=422, detail="classificacao deve ser 'incide' ou 'nao_incide'")

    row = (await db.execute(
        select(RubricaEmpresa)
        .join(Estabelecimento, RubricaEmpresa.estabelecimento_id == Estabelecimento.id)
        .where(RubricaEmpresa.id == rubrica_id,
               Estabelecimento.empresa_id == current_user.empresa_id)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Rubrica nao encontrada nesta empresa")

    row.classificacao_manual = data.classificacao
    row.classificado_por = getattr(current_user, "email", None) or getattr(current_user, "nome", None) or "sistema"
    row.classificado_em = datetime.utcnow()
    row.justificativa_classificacao = data.justificativa
    await db.commit()
    await db.refresh(row)
    return {
        "ok": True,
        "id": str(row.id),
        "classificacao_manual": row.classificacao_manual,
        "classificado_por": row.classificado_por,
    }
