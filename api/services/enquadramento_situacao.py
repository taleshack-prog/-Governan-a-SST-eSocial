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


ORIGEM_NENHUMA = "nenhuma"
ORIGEM_GRAU = "grau"
ORIGEM_FAP = "fap"
ORIGEM_AMBAS = "ambas"

ROTULO_ORIGEM = {
    ORIGEM_NENHUMA: "sem divergência de origem",
    ORIGEM_GRAU: "grau de risco",
    ORIGEM_FAP: "FAP",
    ORIGEM_AMBAS: "grau e FAP",
}

# Como se corrige cada origem — e por que a pergunta importa (S-1005 / item 1 da revisão).
DEFESA_ORIGEM = {
    ORIGEM_GRAU: "Reenquadramento, com memória de atividade preponderante.",
    ORIGEM_FAP: "Portaria do FAP e extrato do FAPWeb.",
    ORIGEM_AMBAS: "Reenquadramento (grau) e portaria/extrato do FAPWeb (FAP) — duas frentes.",
}


def origem_divergencia(aliquota_devida, fap_devido, rat_aplicado, fap_aplicado):
    """Diz QUAL das duas origens causou a divergência: grau, FAP, ambas ou nenhuma.

    O eSocial (S-1005) valida que aliqRatAjust é o produto de aliqRat por fap. Logo o erro nunca
    está no ajustado — está no grau de risco ou no fator. E a resposta decide a defesa: grau
    errado se corrige com reenquadramento e memória de atividade preponderante; FAP errado, com
    a portaria e o extrato do FAPWeb.

    Devolve None quando a comparação não é possível: faltam dados, ou a linha de RAT aplicado é
    antiga e guarda só a efetiva, sem o desdobramento. Nesse caso o sistema sabe que divergiu e
    NÃO afirma de onde — nunca presume rat=3/fap=1,0 para fechar a conta.
    """
    if None in (aliquota_devida, fap_devido, rat_aplicado, fap_aplicado):
        return None
    grau_difere = round(float(rat_aplicado), 2) != round(float(aliquota_devida), 2)
    fap_difere = round(float(fap_aplicado), 4) != round(float(fap_devido), 4)
    if grau_difere and fap_difere:
        return ORIGEM_AMBAS
    if grau_difere:
        return ORIGEM_GRAU
    if fap_difere:
        return ORIGEM_FAP
    return ORIGEM_NENHUMA


def divergencia_amparada(origem, processo_rat, processo_fap) -> bool:
    """True quando a divergência tem processo informado para a(s) origem(ns) que divergiu.

    O leiaute do eSocial só aceita alíquota divergente da prevista se houver processo
    administrativo ou judicial informado. Sem considerar isso, o sistema apontaria achado onde
    existe decisão amparando — achado falso ao contrário, que é igualmente grave num laudo.
    """
    tem_rat = bool(processo_rat and str(processo_rat).strip())
    tem_fap = bool(processo_fap and str(processo_fap).strip())
    if origem == ORIGEM_GRAU:
        return tem_rat
    if origem == ORIGEM_FAP:
        return tem_fap
    if origem == ORIGEM_AMBAS:
        return tem_rat and tem_fap
    return False


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
