# api/services/enquadramento_situacao.py — SST ESOCIAL GOV
# Situacao de uma competencia do enquadramento (revisao da Carolina, item 5).
#
# O PROBLEMA QUE ISTO RESOLVE: havia dois estados — "conferencia" e "ok". Uma competencia com o
# devido calculado mas SEM o aplicado informado saia como "ok", e nao esta ok: ninguem comparou
# nada. A memoria de enquadramento e documento com peso juridico; ela nao pode afirmar
# conformidade de uma competencia que nunca foi verificada.
#
# TRES ESTADOS:
#   conferencia — falta dado para apurar o DEVIDO (FAP do ano ausente, CNAE fora do Anexo I,
#                 sem quantitativo declarado, obra CNO). Nada a afirmar.
#   apurado     — o devido esta completo, mas o APLICADO nao foi informado. Metade do trabalho:
#                 sabemos o que era devido, nao sabemos o que a empresa usou na folha.
#   conferido   — devido e aplicado existem e foram comparados. So aqui ha divergencia (ou a
#                 afirmacao de que nao ha).
#
# Derivado, nao armazenado: os tres estados sao funcao do que ja esta gravado na serie. Guardar
# uma coluna criaria uma segunda verdade, que envelhece quando a serie e reapurada.
#
# Fonte unica: tela, API e PDF importam DESTE modulo. Se a regra mudar, muda em um lugar so.

SITUACAO_CONFERENCIA = "conferencia"
SITUACAO_APURADO = "apurado"
SITUACAO_CONFERIDO = "conferido"

ROTULO = {
    SITUACAO_CONFERENCIA: "conferência",
    SITUACAO_APURADO: "apurado",
    SITUACAO_CONFERIDO: "conferido",
}


def situacao_de(em_fila: bool, aliquota_devida, aliquota_aplicada) -> str:
    """Situacao da competencia. Ver os tres estados no cabecalho do modulo."""
    if em_fila or aliquota_devida is None:
        return SITUACAO_CONFERENCIA
    if aliquota_aplicada is None:
        return SITUACAO_APURADO
    return SITUACAO_CONFERIDO


def divergencia_de(aliquota_efetiva, aliquota_aplicada):
    """Divergencia em pontos percentuais: APLICADO menos EFETIVA.

    A base e a aliquota EFETIVA (RAT x FAP), nao o RAT devido puro. A folha recolhe o GILRAT ja
    multiplicado pelo FAP; comparar o aplicado contra o RAT puro acusaria divergencia em toda
    competencia com FAP diferente de 1,0 — achado falso num documento com peso juridico.

    Sem efetiva (FAP do ano nao informado) nao ha divergencia: a competencia fica em conferencia.
    """
    if aliquota_efetiva is None or aliquota_aplicada is None:
        return None
    return round(aliquota_aplicada - aliquota_efetiva, 4)
