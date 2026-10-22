# api/routers/fundamentacao.py — SST ESOCIAL GOV
# Serve a fundamentacao normativa de um campo derivado. Toda a logica de resolucao vive em
# api/services/fundamentacao.py, que e a fonte unica — aqui so entra o transporte.
#
# A DATA E OBRIGATORIA. Antes 'em' era opcional e caia em "hoje" quando ausente, e era
# exatamente isso que fazia uma peca sobre competencia de 2021 citar a redacao de 2026 sem
# ninguem perceber. Quem pergunta informa a data a que a pergunta se refere: a competencia,
# quando houver uma; o fim do periodo de apuracao, nos blocos de cadastro que nao tem
# competencia. Sem data nao ha pergunta bem formada, e o 422 e preferivel a uma citacao errada
# com aparencia de certa.
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.fundamentacao import citacao_de, historico_de

router = APIRouter()


@router.get("/{campo}")
async def fundamentacao_de(
    campo: str,
    em: date = Query(..., description="Data a que a citação se refere (competência ou fim da apuração)"),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Dispositivo em vigor para o campo NA data informada.

    404 quando o campo não tem citação cadastrada para aquela data — melhor a interface não
    exibir ícone nenhum do que exibir fundamento inventado ou fora de vigência.
    """
    c = await citacao_de(campo, em, db)
    if c is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sem fundamentação cadastrada para '{campo}' em {em.isoformat()}.",
        )
    return c


@router.get("/{campo}/historico")
async def historico(
    campo: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Todas as vigências do campo, da mais antiga para a mais nova.

    É o que permite a um documento gerado para competência antiga citar o que valia na época,
    e a quem revisa ver quando a redação mudou.
    """
    return await historico_de(campo, db)
