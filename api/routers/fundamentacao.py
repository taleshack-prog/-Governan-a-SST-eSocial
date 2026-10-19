# api/routers/fundamentacao.py — SST ESOCIAL GOV
# Serve a fundamentacao normativa de um campo derivado, lida da tabela versionada
# (item 3 da revisao da Carolina). A interface NUNCA escreve citacao no proprio codigo:
# pergunta aqui, informando o campo e a data de referencia.
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from api.database import get_db
from api.models.fundamentacao_campo import FundamentacaoCampo
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


def _to_dict(f: FundamentacaoCampo) -> dict:
    return {
        "campo": f.campo,
        "dispositivo": f.dispositivo,
        "ato_normativo": f.ato_normativo,
        "anexo": f.anexo,
        "observacao": f.observacao,
        "vigencia_inicio": f.vigencia_inicio.isoformat(),
        "vigencia_fim": f.vigencia_fim.isoformat() if f.vigencia_fim else None,
    }


@router.get("/{campo}")
async def fundamentacao_de(
    campo: str,
    em: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dispositivo em vigor para o campo na data informada (padrão: hoje).

    Devolve 404 quando o campo não tem linha cadastrada — melhor a interface não exibir ícone
    nenhum do que exibir fundamento inventado.
    """
    ref = em or date.today()
    f = (await db.execute(
        select(FundamentacaoCampo).where(
            FundamentacaoCampo.campo == campo,
            FundamentacaoCampo.vigencia_inicio <= ref,
            or_(FundamentacaoCampo.vigencia_fim.is_(None), FundamentacaoCampo.vigencia_fim >= ref),
        ).order_by(FundamentacaoCampo.vigencia_inicio.desc()).limit(1)
    )).scalars().first()
    if f is None:
        raise HTTPException(status_code=404, detail=f"Sem fundamentação cadastrada para '{campo}'.")
    return _to_dict(f)


@router.get("/{campo}/historico")
async def historico_de(
    campo: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Todas as vigências do campo, da mais antiga para a mais nova.

    É o que permite a um documento gerado para competência antiga citar o que valia na época,
    em vez do texto de hoje.
    """
    rows = (await db.execute(
        select(FundamentacaoCampo).where(FundamentacaoCampo.campo == campo)
        .order_by(FundamentacaoCampo.vigencia_inicio)
    )).scalars().all()
    return [_to_dict(f) for f in rows]
