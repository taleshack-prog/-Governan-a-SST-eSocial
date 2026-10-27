# api/services/resumo_enquadramento.py — AJUSTA
# AGREGACOES DA SERIE: posicao na janela, estado das competencias, resumo por ano e o que falta.
#
# FONTE UNICA, e este e o motivo de o modulo existir (Carolina, 27/10): "a contagem '22 com
# credito · 24 com debito · 12 sem divergencia' ja existe na memoria de calculo. A lista e a
# pagina tem que usar a MESMA funcao, nao uma conta nova, para a tela e o documento nunca
# mostrarem numeros diferentes."
#
# A contagem vivia escrita dentro do gerador do PDF. Copia-la para a lista e para a pagina criaria
# tres implementacoes da mesma regra, e elas divergiriam — foi o que aconteceu com a citacao do
# § 3º e com a frase do aprendiz, e e o que esta tabela de agregacoes existe para impedir.
#
# DIVISAO DE TRABALHO COM enquadramento_situacao.py: aquele modulo decide o estado de UMA
# competencia; este resume um CONJUNTO delas. Nenhuma regra de classificacao nasce aqui — o sinal
# da divergencia e a situacao chegam prontos na serie.
from collections import OrderedDict

from api.services.enquadramento_situacao import (
    SITUACAO_CONFERENCIA, SITUACAO_APURADO, SITUACAO_CONFERIDO, SITUACAO_NAO_AUDITADA,
)

# Qual situacao representa o ANO quando as competencias dele nao concordam. A pendencia vem
# primeiro de proposito: um ano com onze competencias apuradas e uma em conferencia e um ano que
# exige acao, e exibi-lo como "apurado" esconderia justamente a linha que falta resolver.
_PRECEDENCIA = (SITUACAO_CONFERENCIA, SITUACAO_NAO_AUDITADA, SITUACAO_APURADO, SITUACAO_CONFERIDO)


def _comp(iso: str | None) -> str:
    """'2021-11-01' -> '11/2021'. Devolve o que veio quando nao reconhece o formato."""
    s = (iso or "")[:10]
    return f"{s[5:7]}/{s[:4]}" if len(s) >= 7 and s[4] == "-" else (iso or "")


def _ano(iso: str | None) -> str:
    return (iso or "")[:4]


def posicao_na_janela(serie: list[dict]) -> dict:
    """As competencias agrupadas pelo SINAL da divergencia.

    Devolve as listas, e nao so os totais, porque a memoria precisa dizer ONDE cada grupo cai
    ("22 com crédito (2023, 2026)") e a tela precisa apenas do numero. Uma funcao para os dois
    evita que o documento e a tela contem de formas diferentes.

    'divergencia_pp' nulo e competencia NAO APURADA — distinta de zero, que e apurada e sem
    divergencia. Tratar as duas como a mesma coisa diria que uma competencia sem resultado esta
    conforme.
    """
    com_credito, com_debito, sem_divergencia, nao_apuradas = [], [], [], []
    for r in serie:
        d = r.get("divergencia_pp")
        if d is None:
            nao_apuradas.append(r)
        elif d > 0:
            com_credito.append(r)
        elif d < 0:
            com_debito.append(r)
        else:
            sem_divergencia.append(r)
    return {
        "com_credito": com_credito,
        "com_debito": com_debito,
        "sem_divergencia": sem_divergencia,
        "nao_apuradas": nao_apuradas,
        "total": len(serie),
        # O sinal se inverte dentro da janela: o fato que a memoria destaca e que impede
        # qualquer conclusao automatica sobre haver valor a recuperar.
        "inverte_sinal": bool(com_credito and com_debito),
    }


def contagem_posicao(serie: list[dict]) -> dict:
    """So os numeros, para quem nao precisa das listas (a lista de estabelecimentos)."""
    p = posicao_na_janela(serie)
    return {k: len(p[k]) for k in
            ("com_credito", "com_debito", "sem_divergencia", "nao_apuradas")} | {
        "total": p["total"], "inverte_sinal": p["inverte_sinal"]}


def estado_na_janela(serie: list[dict]) -> dict:
    """Quantas competencias em cada estado: apuradas, em conferencia, conferidas, nao auditadas."""
    contagem = {SITUACAO_APURADO: 0, SITUACAO_CONFERENCIA: 0,
                SITUACAO_CONFERIDO: 0, SITUACAO_NAO_AUDITADA: 0}
    for r in serie:
        s = r.get("situacao")
        if s in contagem:
            contagem[s] += 1
    return {
        "apuradas": contagem[SITUACAO_APURADO],
        "em_conferencia": contagem[SITUACAO_CONFERENCIA],
        "conferidas": contagem[SITUACAO_CONFERIDO],
        "nao_auditadas": contagem[SITUACAO_NAO_AUDITADA],
        "total": len(serie),
    }


def _unico(valores: list):
    """O valor, quando todos concordam; None quando divergem.

    Um ano tem doze competencias, e a tela mostra uma linha. Imprimir a primeira como se fosse a
    do ano inteiro afirmaria sobre onze meses que ninguem conferiu. Quando divergem, a resposta e
    'varia' — e a serie mensal, a um clique, mostra onde.
    """
    distintos = {v for v in valores}
    return next(iter(distintos)) if len(distintos) == 1 else None


def resumo_por_ano(serie: list[dict]) -> list[dict]:
    """Uma linha por ano: competencias, preponderante, devida, aplicada, divergencia e situacao.

    Seis linhas em vez de sessenta, e a inversao de credito para debito visivel de relance. Cada
    campo sai com 'varia' quando as competencias do ano nao concordam: e o unico jeito honesto de
    resumir doze valores numa celula.
    """
    anos: "OrderedDict[str, list[dict]]" = OrderedDict()
    for r in sorted(serie, key=lambda x: x.get("competencia") or ""):
        anos.setdefault(_ano(r.get("competencia")), []).append(r)

    saida = []
    for ano, rs in anos.items():
        situacoes = {r.get("situacao") for r in rs}
        situacao = next((s for s in _PRECEDENCIA if s in situacoes), None)
        campos = {}
        for chave in ("cnae_preponderante", "aliquota_devida", "aliquota_aplicada", "divergencia_pp"):
            vals = [r.get(chave) for r in rs]
            v = _unico(vals)
            campos[chave] = v
            campos[f"{chave}_varia"] = v is None and len(vals) > 0 and len({x for x in vals}) > 1
        saida.append({
            "ano": ano,
            "competencias": len(rs),
            **campos,
            "situacao": situacao,
            "estado": estado_na_janela(rs),
        })
    return saida


def o_que_falta(serie: list[dict]) -> list[dict]:
    """As pendencias agrupadas por MOTIVO, com as competencias que cada uma trava.

    Nas palavras dela: "o topo diz o que falta e por quê — 'FAP publicado de 2021: trava nov e
    dez/2021'. O usuário não precisa adivinhar por que duas competências estão em conferência."
    Uma linha por competencia pendente seria a lista de sessenta de volta; o que resolve a
    pendencia e o motivo, e um motivo costuma travar varias competencias de uma vez.

    O texto do motivo vem de motivo_conferencia(), ja calculado por competencia — nao e escrito
    aqui. Agrupar preserva a redacao de la e nao inventa nenhuma.
    """
    grupos: "OrderedDict[str, list[str]]" = OrderedDict()
    for r in sorted(serie, key=lambda x: x.get("competencia") or ""):
        motivo = r.get("motivo_conferencia")
        if not motivo:
            continue
        grupos.setdefault(motivo, []).append(_comp(r.get("competencia")))

    saida = []
    for motivo, comps in grupos.items():
        # Ate tres competencias saem nomeadas; acima disso, o intervalo — a mesma regra que a
        # memoria ja usa para nao transformar a frase numa lista de meses.
        onde = ", ".join(comps) if len(comps) <= 3 else f"{comps[0]} a {comps[-1]}"
        saida.append({
            "motivo": motivo,
            "competencias": comps,
            "texto": f"{motivo.rstrip('.')} — trava {onde}",
        })
    return saida
