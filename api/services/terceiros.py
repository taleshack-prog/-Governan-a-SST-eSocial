# api/services/terceiros.py — SST ESOCIAL GOV
# Leitura da aliquota de Terceiros POR COMPETENCIA (Carolina, 18/10, item 1).
#
# A regra que este modulo existe para impor: nunca "a aliquota atual". Sempre a aliquota que
# estava em vigor NA COMPETENCIA apurada, com o ato normativo que a fixou. Uma tabela sem
# vigencia aplica o valor de hoje a todo o passado e erra sem emitir erro — o calculo conclui e
# devolve um numero. Numero errado com aparencia de numero certo e o pior defeito num laudo.
#
# A fonte volta junto com o valor de proposito: o laudo cita o fundamento, e um documento que
# apure 03/2022 citando a IN RFB 2.110/2022 afirma que vigia norma que ainda nao existia.
#
# Tres vigencias na janela (levantamento da curadoria):
#   IN RFB 971/2009              ate a vigencia da IN RFB 2.110/2022
#   IN RFB 2.110/2022, Anexo III ate 31/03/2026
#   IN RFB 2.321/2026            de 01/04/2026 em diante  <- corte em 1º de ABRIL, nao na
#                                                            publicacao (14/04/2026)
from datetime import date

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.tabela_fpas import TabelaFPAS


def _sem_vigencia_cobrindo(codigo: str, competencia: date) -> dict:
    """Resposta para competencia sem linha cadastrada. NUNCA devolve aliquota presumida."""
    return {
        "codigo_fpas": codigo,
        "aliquota_terceiros": None,
        "descricao": None,
        "fonte": None,
        "vigencia_inicio": None,
        "vigencia_fim": None,
        "em_conferencia": True,
        "motivo": (f"Sem alíquota de Terceiros cadastrada para o FPAS {codigo} na competência "
                   f"{competencia.strftime('%m/%Y')}. A carga daquela vigência está pendente."),
    }


def _to_dict(t: TabelaFPAS) -> dict:
    return {
        "codigo_fpas": t.codigo_fpas,
        "aliquota_terceiros": float(t.aliquota_terceiros),
        "descricao": t.descricao,
        "codigo_terceiros": t.codigo_terceiros,
        "fonte": t.fonte,
        "vigencia_inicio": t.vigencia_inicio.isoformat() if t.vigencia_inicio else None,
        "vigencia_fim": t.vigencia_fim.isoformat() if t.vigencia_fim else None,
        "em_conferencia": not t.confirmado,
        "motivo": None if t.confirmado else "Alíquota marcada como pendente de confirmação.",
    }


async def aliquota_em(codigo_fpas: str, competencia: date, db: AsyncSession) -> dict:
    """Alíquota de Terceiros do código, em vigor NA competência informada.

    Devolve sempre um dicionário; quando não há linha cobrindo a competência, vem com
    aliquota_terceiros None e em_conferencia True — a competência vai à fila, nunca recebe
    valor presumido.
    """
    t = (await db.execute(
        select(TabelaFPAS).where(
            TabelaFPAS.codigo_fpas == codigo_fpas,
            TabelaFPAS.ativo.is_(True),
            TabelaFPAS.vigencia_inicio <= competencia,
            or_(TabelaFPAS.vigencia_fim.is_(None), TabelaFPAS.vigencia_fim >= competencia),
        ).order_by(TabelaFPAS.vigencia_inicio.desc()).limit(1)
    )).scalars().first()
    return _to_dict(t) if t else _sem_vigencia_cobrindo(codigo_fpas, competencia)


async def vigencias_de(codigo_fpas: str, db: AsyncSession) -> list[dict]:
    """Todas as vigências do código, da mais antiga para a mais nova.

    É o que permite ao laudo de uma competência antiga citar o ato que valia na época.
    """
    rows = (await db.execute(
        select(TabelaFPAS).where(TabelaFPAS.codigo_fpas == codigo_fpas)
        .order_by(TabelaFPAS.vigencia_inicio)
    )).scalars().all()
    return [_to_dict(t) for t in rows]


async def opcoes_em(competencia: date, db: AsyncSession) -> list[dict]:
    """Códigos FPAS oferecíveis na competência (para o select da tela).

    Filtrado por vigência: oferecer um código que não vigia naquela competência seria convidar
    o usuário a declarar o impossível.
    """
    rows = (await db.execute(
        select(TabelaFPAS).where(
            TabelaFPAS.ativo.is_(True),
            TabelaFPAS.vigencia_inicio <= competencia,
            or_(TabelaFPAS.vigencia_fim.is_(None), TabelaFPAS.vigencia_fim >= competencia),
        ).order_by(TabelaFPAS.codigo_fpas)
    )).scalars().all()
    return [_to_dict(t) for t in rows]
