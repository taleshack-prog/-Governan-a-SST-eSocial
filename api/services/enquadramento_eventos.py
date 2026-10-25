# api/services/enquadramento_eventos.py — AJUSTA
# Gravacao da trilha de eventos do enquadramento (migration 047).
#
# Um lugar so grava evento. Os quatro pontos que disparam (motor, conferir, desconferir,
# revogacao) chamam daqui, e nenhum deles monta o dicionario por conta propria: evento gravado
# com campo faltando ou com texto que o CHECK recusa so falha em producao, e normalmente no
# caminho menos testado.
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.enquadramento_evento import (
    EnquadramentoEvento, EVENTO_APURADO, EVENTO_CONFERIDO, EVENTO_DESCONFERIDO, EVENTO_REVOGADO,
)

# Os campos cuja mudanca importa. Sao os que compoem o NUMERO — e e o numero que, ao mudar,
# desfaz a assinatura de quem conferiu. Procedencia, motivo de fila e data de apuracao mudam
# sem que o valor mude, e por isso nao entram aqui.
CASAS = {
    "aliquota_devida": 2,
    "fap": 4,
    "aliquota_efetiva": 4,
    "aliquota_aplicada": 4,
}
CAMPOS_CALCULO = ("grau_risco", "aliquota_devida", "fap", "aliquota_efetiva",
                  "aliquota_aplicada", "rat_aplicavel")

# Como o campo aparece escrito na peca. A trilha e lida por advogado, nao por quem escreveu a
# tabela: "aliquota_devida" nao se explica sozinho num documento assinado.
ROTULO_CAMPO = {
    "grau_risco": "grau de risco",
    "aliquota_devida": "alíquota RAT devida",
    "fap": "FAP",
    "aliquota_efetiva": "alíquota efetiva (RAT × FAP)",
    "aliquota_aplicada": "alíquota aplicada pela empresa",
    "rat_aplicavel": "aplicabilidade do RAT",
}


def _texto(campo: str, valor) -> str | None:
    """Valor em texto comparavel e legivel.

    Numero vira string com as casas da propria coluna: sem isso, 3.0 e 3.00 contariam como
    mudanca e a trilha encheria de alteracao que nao houve.
    """
    if valor is None:
        return None
    if campo == "rat_aplicavel":
        return "sim" if valor else "não"
    if campo == "grau_risco":
        return str(int(valor))
    return f"{Decimal(str(valor)):.{CASAS[campo]}f}"


def retrato(linha) -> dict:
    """Os valores de calculo de uma competencia, no formato que o evento guarda.

    Aceita tanto a linha do ORM quanto um dicionario — o motor monta os valores antes de existir
    linha, e nao faz sentido instanciar o modelo so para fotografa-lo.
    """
    pegar = linha.get if isinstance(linha, dict) else lambda c: getattr(linha, c, None)
    return {c: pegar(c) for c in CAMPOS_CALCULO}


def diferencas(antes: dict | None, depois: dict) -> list[dict]:
    """O que mudou, campo a campo: [{"campo","rotulo","de","para"}].

    Lista e nao par de colunas porque grau e fator costumam mudar juntos na mesma reapuracao —
    com um par so, um dos dois teria de ser descartado.
    """
    if antes is None:
        return []
    saida = []
    for c in CAMPOS_CALCULO:
        de, para = _texto(c, antes.get(c)), _texto(c, depois.get(c))
        if de != para:
            saida.append({"campo": c, "rotulo": ROTULO_CAMPO[c], "de": de, "para": para})
    return saida


def mudou(antes: dict | None, depois: dict) -> bool:
    """True quando ha o que registrar. Competencia nova (antes=None) sempre conta."""
    return antes is None or bool(diferencas(antes, depois))


async def registrar(
    db: AsyncSession,
    *,
    estabelecimento_id,
    competencia: date,
    evento: str,
    valores: dict,
    autor: str | None = None,
    alteracoes: list[dict] | None = None,
    motivo: str | None = None,
) -> EnquadramentoEvento:
    """Grava UM evento. Nao faz commit: quem chama decide a transacao.

    Argumentos por nome de proposito. Esta funcao recebe seis coisas parecidas entre si — uma
    competencia, um autor, um motivo, dois dicionarios — e posicional aqui seria convite a
    trocar dois deles sem que nada reclame.

    'escritorio_id' nao aparece: quem preenche e o trigger trg_fill_escritorio, a partir da GUC
    da requisicao. A chave de isolamento nunca vem do codigo da aplicacao.
    """
    ev = EnquadramentoEvento(
        estabelecimento_id=estabelecimento_id,
        competencia=competencia,
        evento=evento,
        autor=autor,
        ocorrido_em=datetime.now(timezone.utc),
        alteracoes=alteracoes or None,
        motivo=motivo,
        **retrato(valores),
    )
    db.add(ev)
    return ev


async def registrar_apuracao(
    db: AsyncSession, *, estabelecimento_id, competencia: date,
    antes: dict | None, depois: dict, autor: str | None,
    conferido_por: str | None = None,
) -> int:
    """Eventos de uma competencia recem-apurada. Devolve quantos gravou.

    SO REGISTRA QUANDO O NUMERO MUDA. Reapurar 60 competencias em que nada mudou geraria 60
    linhas identicas por salvamento, e a trilha ficaria ilegivel numa semana de uso — o oposto
    do que ela serve. Competencia nova sempre registra, porque nao havia nada antes.
    (Se um dia a Carolina preferir provar tambem que "o sistema reapurou em tal data e nada
    mudou", e trocar este if por um registro incondicional.)

    Quando a competencia estava CONFERIDA e o numero mudou, saem DOIS eventos: o 'apurado', com
    o numero novo, e o 'revogado', com o numero sobre o qual a pessoa havia assinado. Os dois
    sao necessarios — um diz o que passou a valer, o outro diz o que deixou de valer e de quem
    era a assinatura.
    """
    if not mudou(antes, depois):
        return 0

    mudancas = diferencas(antes, depois)
    await registrar(
        db, estabelecimento_id=estabelecimento_id, competencia=competencia,
        evento=EVENTO_APURADO, valores=depois, autor=autor, alteracoes=mudancas or None,
    )
    gravados = 1

    if conferido_por and mudancas:
        campos = ", ".join(m["rotulo"] for m in mudancas)
        await registrar(
            db, estabelecimento_id=estabelecimento_id, competencia=competencia,
            evento=EVENTO_REVOGADO,
            valores=antes,                      # o numero QUE FOI CONFERIDO, nao o novo
            autor=autor, alteracoes=mudancas,
            motivo=(f"Conferência de {conferido_por} revogada: {campos} "
                    f"{'mudaram' if len(mudancas) > 1 else 'mudou'} na reapuração."),
        )
        gravados += 1

    return gravados


async def registrar_ato_humano(
    db: AsyncSession, *, estabelecimento_id, competencia: date, conferindo: bool,
    valores: dict, autor: str, observacao: str | None = None,
) -> EnquadramentoEvento:
    """Conferencia ou retirada de conferencia. Sempre registra: e ato de pessoa, nao calculo.

    O retrato vai junto porque e o ponto do pedido da Carolina — a conferencia precisa guardar o
    valor sobre o qual foi dada. Sem ele, o sistema sabe que alguem assinou e nao sabe o que.
    """
    return await registrar(
        db, estabelecimento_id=estabelecimento_id, competencia=competencia,
        evento=EVENTO_CONFERIDO if conferindo else EVENTO_DESCONFERIDO,
        valores=valores, autor=autor, motivo=observacao,
    )
