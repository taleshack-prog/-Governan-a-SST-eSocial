# api/routers/estabelecimentos.py — SST ESOCIAL GOV
# Adendo 04: o estabelecimento guarda identificacao/natureza/datas; o enquadramento (grau/RAT)
# e DERIVADO da atividade preponderante (RN-20) — não é campo escolhido. A entrada do motor é a
# lista de atividades com quantitativo por periodo (RF-0.173).
import re
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel

from api.database import get_db
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_fap import EstabelecimentoFAP
from api.models.estabelecimento_atividade import EstabelecimentoAtividade
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.cnae_enquadramento import CnaeEnquadramento
from api.models.usuario import Usuario
from api.auth import get_current_user, require_perfil

router = APIRouter()

TIPOS_ESTABELECIMENTO = ("CNPJ", "CNO", "CAEPF")   # RF-0.171
POSICOES = ("matriz", "filial", "obra")
STATUS_VALIDOS = ("ativa", "paralisada", "encerrada")


def _cnpj_valido(v: str | None) -> bool:
    c = re.sub(r"\D", "", v or "")
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def dv(base: str) -> int:
        pesos = [5,4,3,2,9,8,7,6,5,4,3,2] if len(base) == 12 else [6,5,4,3,2,9,8,7,6,5,4,3,2]
        s = sum(int(d) * p for d, p in zip(base, pesos))
        r = s % 11
        return 0 if r < 2 else 11 - r
    return dv(c[:12]) == int(c[12]) and dv(c[:13]) == int(c[13])


def _validar(data) -> None:
    if data.tipo_estabelecimento not in TIPOS_ESTABELECIMENTO:
        raise HTTPException(status_code=422, detail="Natureza deve ser CNPJ, CNO ou CAEPF.")
    if data.posicao not in POSICOES:
        raise HTTPException(status_code=422, detail="Posição deve ser matriz, filial ou obra.")
    if data.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=422, detail="Status inválido.")
    if data.tipo_estabelecimento == "CNPJ" and not _cnpj_valido(data.cnpj):
        raise HTTPException(status_code=422, detail="CNPJ obrigatório e válido (dígito verificador) para natureza CNPJ.")
    if data.tipo_estabelecimento == "CNO" and not (data.identificador and data.identificador.strip()):
        raise HTTPException(status_code=422, detail="Matrícula CNO obrigatória para natureza CNO.")
    if not data.data_abertura:
        raise HTTPException(status_code=422, detail="Data de abertura é obrigatória.")


def _to_dict(e: Estabelecimento) -> dict:
    return {
        "id": str(e.id), "codigo": e.codigo, "nome": e.nome,
        "tipo_estabelecimento": e.tipo_estabelecimento, "posicao": e.posicao,
        "cnpj": e.cnpj, "identificador": e.identificador,
        "status": e.status, "cidade": e.cidade, "uf": e.uf, "endereco": e.endereco,
        "data_abertura": e.data_abertura.isoformat() if e.data_abertura else None,
        "data_encerramento": e.data_encerramento.isoformat() if e.data_encerramento else None,
    }


class EstabelecimentoIn(BaseModel):
    codigo: str
    nome: str
    tipo_estabelecimento: str = "CNPJ"
    posicao: str = "filial"
    cnpj: str | None = None
    identificador: str | None = None
    status: str = "ativa"
    endereco: str | None = None
    cidade: str | None = None
    uf: str | None = None
    data_abertura: date | None = None
    data_encerramento: date | None = None


@router.get("/")
async def listar_estabelecimentos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Estabelecimento).where(Estabelecimento.empresa_id == current_user.empresa_id)
        .order_by(Estabelecimento.codigo)
    )
    return [_to_dict(e) for e in result.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_estabelecimento(
    data: EstabelecimentoIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    _validar(data)
    existente = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.empresa_id == current_user.empresa_id,
            Estabelecimento.codigo == data.codigo,
        )
    )).scalar_one_or_none()
    if existente:
        raise HTTPException(status_code=409, detail="Já existe um estabelecimento com este código.")
    e = Estabelecimento(empresa_id=current_user.empresa_id, **data.model_dump())
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return _to_dict(e)


@router.put("/{estab_id}")
async def atualizar_estabelecimento(
    estab_id: UUID,
    data: EstabelecimentoIn,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    _validar(data)
    e = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id, Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado.")
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    await db.commit()
    await db.refresh(e)
    return _to_dict(e)


# ---- Lista de atividades com quantitativo por período (RF-0.173) ----
class AtividadeIn(BaseModel):
    cnae: str
    descricao: str | None = None
    quantitativo: int | None = None
    inicio: date
    fim: date | None = None


async def _tenant_estab(estab_id: UUID, current_user: Usuario, db: AsyncSession) -> Estabelecimento:
    e = (await db.execute(
        select(Estabelecimento).where(
            Estabelecimento.id == estab_id, Estabelecimento.empresa_id == current_user.empresa_id
        )
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Estabelecimento não encontrado.")
    return e


@router.get("/{estab_id}/atividades")
async def listar_atividades(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoAtividade.vigencia_inicio)
    )).scalars().all()
    return [{"cnae": r.cnae, "descricao": r.descricao, "quantitativo": r.quantitativo,
             "inicio": r.vigencia_inicio.isoformat(), "fim": r.vigencia_fim.isoformat() if r.vigencia_fim else None,
             "declarado_por": r.declarado_por} for r in rows]


@router.put("/{estab_id}/atividades")
async def salvar_atividades(
    estab_id: UUID,
    data: list[AtividadeIn],
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Substitui a lista de atividades. Rejeita CNAE inexistente no Anexo I (RF-0.173).
    Grava autoria (RN-23)."""
    await _tenant_estab(estab_id, current_user, db)
    for it in data:
        cnae = re.sub(r"\D", "", it.cnae or "")
        if len(cnae) != 7:
            raise HTTPException(status_code=422, detail=f"CNAE '{it.cnae}' deve ter 7 dígitos.")
        existe = (await db.execute(
            select(CnaeEnquadramento.cnae).where(CnaeEnquadramento.cnae == cnae)
        )).scalar_one_or_none()
        if not existe:
            raise HTTPException(status_code=422, detail=f"CNAE {cnae} não existe no Anexo I. Confira a subclasse.")
        if it.fim and it.fim < it.inicio:
            raise HTTPException(status_code=422, detail="Atividade com fim anterior ao início.")
    declarante = getattr(current_user, "email", None) or getattr(current_user, "nome", None)
    antigas = (await db.execute(
        select(EstabelecimentoAtividade).where(EstabelecimentoAtividade.estabelecimento_id == estab_id)
    )).scalars().all()
    for a in antigas:
        await db.delete(a)
    for it in data:
        db.add(EstabelecimentoAtividade(
            estabelecimento_id=estab_id, cnae=re.sub(r"\D", "", it.cnae), descricao=it.descricao,
            quantitativo=it.quantitativo, vigencia_inicio=it.inicio, vigencia_fim=it.fim,
            declarado_por=declarante, declarado_em=datetime.utcnow(),
        ))
    await db.commit()
    from api.services.motor_enquadramento import apurar_estabelecimento
    await apurar_estabelecimento(estab_id, db)   # reapura a série ao mudar as atividades
    return {"ok": True, "total": len(data)}


# ---- FAP por ano (RF-0.177) ----
class FapAnoIn(BaseModel):
    ano: int
    fap: float


@router.get("/{estab_id}/fap")
async def listar_fap(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await _tenant_estab(estab_id, current_user, db)
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
    """FAP por ano (0,5 a 2,0). Campo vazio não é 1,0 — simplesmente não é enviado."""
    await _tenant_estab(estab_id, current_user, db)
    for item in faps:
        if not (0.5 <= item.fap <= 2.0):
            raise HTTPException(status_code=422, detail=f"FAP {item.fap} fora da faixa 0,5–2,0 (ano {item.ano}).")
        existe = (await db.execute(
            select(EstabelecimentoFAP).where(
                EstabelecimentoFAP.estabelecimento_id == estab_id,
                EstabelecimentoFAP.ano_vigencia == item.ano,
            )
        )).scalar_one_or_none()
        if existe:
            existe.valor_fap = item.fap
            existe.origem = "declarado"
            existe.declarado_em = datetime.utcnow()
        else:
            db.add(EstabelecimentoFAP(estabelecimento_id=estab_id, ano_vigencia=item.ano, valor_fap=item.fap,
                                      origem="declarado", declarado_em=datetime.utcnow()))
    await db.commit()
    from api.services.motor_enquadramento import apurar_estabelecimento
    await apurar_estabelecimento(estab_id, db)   # reapura a série ao mudar o FAP
    return {"ok": True, "salvos": len(faps)}


# ---- Motor de apuração do enquadramento (RF-0.175-182) ----
@router.post("/{estab_id}/apurar")
async def apurar(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    """Recalcula a série mensal de enquadramento (preponderância → grau → RAT × FAP)."""
    await _tenant_estab(estab_id, current_user, db)
    from api.services.motor_enquadramento import apurar_estabelecimento
    return await apurar_estabelecimento(estab_id, db)


@router.get("/{estab_id}/enquadramento")
async def serie_enquadramento(
    estab_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Série apurada por competência (somente leitura). Divergência = devido − aplicado (RF-0.180)."""
    await _tenant_estab(estab_id, current_user, db)
    rows = (await db.execute(
        select(EstabelecimentoEnquadramento).where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id)
        .order_by(EstabelecimentoEnquadramento.competencia)
    )).scalars().all()
    out = []
    for r in rows:
        dev = float(r.aliquota_efetiva) if r.aliquota_efetiva is not None else None
        apl = float(r.aliquota_aplicada) if r.aliquota_aplicada is not None else None
        out.append({
            "competencia": r.competencia.isoformat(),
            "cnae_preponderante": r.cnae_preponderante,
            "criterio": r.criterio,
            "grau_risco": r.grau_risco,
            "aliquota_devida": float(r.aliquota_devida) if r.aliquota_devida is not None else None,
            "fap": float(r.fap) if r.fap is not None else None,
            "aliquota_efetiva": dev,
            "aliquota_aplicada": apl,
            "divergencia_pp": round(apl - dev, 4) if (dev is not None and apl is not None) else None,
            "em_fila": r.em_fila,
            "motivo_fila": r.motivo_fila,
            "fundamentacao": {
                "dispositivo": r.fund_dispositivo, "ato_normativo": r.fund_ato_normativo,
                "anexo": r.fund_anexo, "vigencia": r.fund_vigencia,
            },
        })
    return out
