# api/services/empresa_ciclo_vida.py — AJUSTA
# Arquivar, restaurar e excluir: a trilha e a trava (revisao da Carolina, 22/10 e 27/10).
#
# DOIS PEDIDOS, NUM LUGAR SO.
#
# 1) A EXCLUSAO DEIXA DE SER INCONDICIONAL. Ela: "num sistema que produz prova, 'apaga a empresa e
#    todo o enquadramento ja apurado' so pode valer enquanto nada foi assinado nem emitido. Se uma
#    competencia foi conferida por uma pessoa e a memoria de calculo foi para uma peca protocolada,
#    excluir a empresa apaga o registro que sustenta o que foi apresentado. Esse registro pode ser
#    pedido anos depois, dentro do prazo de cinco anos do pedido de restituicao."
#
#    Duas condicoes impedem a exclusao, e qualquer uma basta: competencia conferida (ato humano,
#    com autor e data desde a 040) ou memoria emitida (desde a 054). Empresa sem nada assinado e
#    sem documento emitido continua podendo ser excluida — a fricção que ja existia, de digitar a
#    razao social e ser titular, permanece para esse caso.
#
# 2) OS TRES ATOS PASSAM A TER AUTOR E DATA, pela mesma regra da conferencia e da declaracao do
#    regime. Arquivar e restaurar ficam visiveis no proprio bloco; a exclusao fica na trilha do
#    escritorio, que sobrevive a empresa.
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.escritorio_evento import (
    EscritorioEvento, EVENTO_ARQUIVADA, EVENTO_RESTAURADA, EVENTO_EXCLUIDA,
)
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.services.memoria_registro import quantas_emitidas


async def registrar_ato(
    db: AsyncSession, *, evento: str, empresa, autor: str, detalhe: str | None = None,
) -> EscritorioEvento:
    """Grava um ato na trilha do escritorio. Nao faz commit.

    A razao social e o CNPJ entram como COPIA, lidos da empresa agora: depois da exclusao nao ha
    de onde le-los, e e justamente ai que a linha precisa continuar dizendo de quem se tratava.
    """
    ev = EscritorioEvento(
        evento=evento,
        empresa_id=empresa.id,
        razao_social=(getattr(empresa, "razao_social", None) or "").strip() or "(sem razão social)",
        cnpj=getattr(empresa, "cnpj", None),
        autor=autor,
        ocorrido_em=datetime.now(timezone.utc),
        detalhe=detalhe,
    )
    db.add(ev)
    return ev


async def competencias_conferidas(db: AsyncSession, empresa_id) -> int:
    """Quantas competencias da empresa carregam assinatura de pessoa.

    Atravessa estabelecimentos porque a conferencia vive na competencia, e a exclusao e da
    empresa: basta UMA competencia assinada em UM estabelecimento para que apagar a empresa
    destrua o registro que sustenta aquela assinatura.
    """
    return int((await db.execute(
        select(func.count(EstabelecimentoEnquadramento.id))
        .join(Estabelecimento, Estabelecimento.id == EstabelecimentoEnquadramento.estabelecimento_id)
        .where(Estabelecimento.empresa_id == empresa_id,
               EstabelecimentoEnquadramento.conferido_por.isnot(None))
    )).scalar() or 0)


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


async def situacao_exclusao(db: AsyncSession, empresa_id) -> dict:
    """Se a empresa pode ser excluida, e por que nao, quando nao pode.

    Devolve as duas contagens mesmo quando a exclusao e possivel: a tela mostra os numeros, e um
    "nao pode" sem dizer quanto nem do que nao se confere.
    """
    conferidas = await competencias_conferidas(db, empresa_id)
    memorias = await quantas_emitidas(db, empresa_id)
    pode = conferidas == 0 and memorias == 0

    motivo = None
    if not pode:
        partes = []
        if conferidas:
            partes.append(_plural(conferidas, "competência conferida", "competências conferidas"))
        if memorias:
            partes.append(_plural(memorias, "memória de cálculo emitida", "memórias de cálculo emitidas"))
        motivo = (
            f"Esta empresa tem {' e '.join(partes)}. "
            "Excluir apagaria o registro que sustenta esses documentos. Use Arquivar."
        )

    return {
        "pode_excluir": pode,
        "motivo": motivo,
        "competencias_conferidas": conferidas,
        "memorias_emitidas": memorias,
    }


async def historico_arquivamento(db: AsyncSession, empresa_id) -> dict:
    """O ultimo arquivamento e a ultima restauracao, para a linha do bloco.

    Os dois mais recentes de cada tipo, e nao a trilha inteira: o bloco mostra uma linha
    ("Arquivada por... · Restaurada por..."), e a trilha completa e outra tela.
    """
    saida: dict[str, dict | None] = {"arquivada": None, "restaurada": None}
    for evento, chave in ((EVENTO_ARQUIVADA, "arquivada"), (EVENTO_RESTAURADA, "restaurada")):
        ev = (await db.execute(
            select(EscritorioEvento)
            .where(EscritorioEvento.empresa_id == empresa_id, EscritorioEvento.evento == evento)
            .order_by(EscritorioEvento.ocorrido_em.desc()).limit(1)
        )).scalars().first()
        if ev:
            saida[chave] = {"autor": ev.autor,
                            "em": ev.ocorrido_em.isoformat() if ev.ocorrido_em else None}
    return saida


__all__ = [
    "registrar_ato", "competencias_conferidas", "situacao_exclusao", "historico_arquivamento",
    "EVENTO_ARQUIVADA", "EVENTO_RESTAURADA", "EVENTO_EXCLUIDA",
]
