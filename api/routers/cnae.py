# api/routers/cnae.py — SST ESOCIAL GOV
# Enquadramento CNAE -> grau de risco -> aliquota RAT (Modulo 4, Frente 1 do roteiro).
# Fonte determinística: Anexo V do Decreto 3.048/99 (red. Decreto 10.410/2020), CNAE 2.3.
import re
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.cnae_enquadramento import CnaeEnquadramento
from api.models.cnae_fpas_sugestao import CnaeFpasSugestao
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.terceiros import aliquota_em

router = APIRouter()

GRAU_LABEL = {1: "leve", 2: "médio", 3: "grave"}


@router.get("/buscar")
async def buscar_cnae(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Autocomplete sobre o Anexo I (RF-0.173): busca por código (dígitos) ou descrição."""
    termo = (q or "").strip()
    if len(termo) < 2:
        return []
    digitos = re.sub(r"\D", "", termo)
    cond = CnaeEnquadramento.descricao.ilike(f"%{termo}%")
    if digitos:
        cond = cond | CnaeEnquadramento.cnae.like(f"{digitos}%")
    rows = (await db.execute(
        select(CnaeEnquadramento).where(cond).order_by(CnaeEnquadramento.cnae).limit(15)
    )).scalars().all()
    return [{"cnae": r.cnae, "cnae_fmt": r.cnae_fmt, "descricao": r.descricao,
             "grau_risco": r.grau_risco, "grau_label": GRAU_LABEL.get(r.grau_risco, ""),
             "aliquota_rat": float(r.aliquota_rat)} for r in rows]


@router.get("/{codigo}/enquadramento")
async def enquadrar_cnae(
    codigo: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dado um CNAE, retorna o enquadramento OFICIAL (determinístico) do Anexo V:
    grau de risco (1 leve / 2 médio / 3 grave) e a alíquota RAT devida (1% / 2% / 3%).

    FPAS NÃO é determinado pelo Anexo V (depende da atividade). Aqui ele vem como
    SUGESTÃO por seção do CNAE (tabela cnae_fpas_sugestao, heurística) — a tela
    pré-seleciona marcando "sugerido — confirmar"; a validação jurídica é obrigatória.
    """
    cnae = re.sub(r"\D", "", codigo or "")
    if len(cnae) != 7:
        raise HTTPException(
            status_code=400,
            detail="CNAE deve ter 7 dígitos (subclasse CNAE 2.3, ex.: 2512800).",
        )
    row = (await db.execute(
        select(CnaeEnquadramento).where(CnaeEnquadramento.cnae == cnae)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"CNAE {cnae} não encontrado no Anexo V (CNAE 2.3). Confira a subclasse.",
        )

    # Sugestão de FPAS por seção (divisão = 2 primeiros dígitos). Heurística, não lei.
    divisao = int(cnae[:2])
    sug = (await db.execute(
        select(CnaeFpasSugestao).where(
            CnaeFpasSugestao.divisao_ini <= divisao,
            CnaeFpasSugestao.divisao_fim >= divisao,
        )
    )).scalars().first()
    fpas_sugerido = sug.fpas_sugerido if sug else None
    fpas_descricao = None
    fpas_terceiros = None
    fpas_vigencia = None
    if fpas_sugerido:
        # A migration 038 deu DIMENSAO DE TEMPO a tabela de FPAS: a chave passou a ser
        # (codigo_fpas, vigencia_inicio). Buscar por codigo e pedir scalar_one_or_none()
        # levantava MultipleResultsFound — 500 — no instante em que o codigo ganhasse a segunda
        # vigencia, ou seja, assim que a carga da IN RFB 2.321/2026 entrasse. E, mesmo com uma
        # vigencia so, devolver "a" aliquota sem dizer de QUANDO ela e exatamente o defeito que
        # a 038 existe para fechar. Agora vem pelo servico, que escolhe a vigencia que cobre a
        # competencia e diz qual e.
        t = await aliquota_em(fpas_sugerido, date.today(), db)
        fpas_descricao = t.get("descricao")
        fpas_terceiros = t.get("aliquota_terceiros")
        fpas_vigencia = t.get("vigencia_inicio")

    return {
        "cnae": row.cnae,
        "cnae_fmt": row.cnae_fmt,
        "descricao": row.descricao,
        "grau_risco": row.grau_risco,
        "grau_label": GRAU_LABEL.get(row.grau_risco, ""),
        "aliquota_rat": float(row.aliquota_rat),
        "fonte": row.fonte,
        # FPAS = sugestão por seção (confirmar)
        "fpas_sugerido": fpas_sugerido,
        "fpas_setor": sug.setor if sug else None,
        "fpas_descricao": fpas_descricao,
        "fpas_terceiros": fpas_terceiros,
        # De QUAL vigência é essa alíquota. Sem isso o número não é auditável: Terceiros mudou
        # com a IN RFB 2.321/2026 (01/04/2026) e muda de novo no futuro.
        "fpas_terceiros_vigencia": fpas_vigencia,
        "fpas_observacao": (sug.observacao if sug and sug.observacao else None),
        "fpas_fonte": "Sugestão por seção do CNAE — confirme o código conforme a atividade.",
    }
