# api/services/enquadramento_situacao.py — SST ESOCIAL GOV
# Situacao de uma competencia do enquadramento (revisao da Carolina, item 5).
#
# O PROBLEMA QUE ISTO RESOLVE: havia dois estados — "conferencia" e "ok". Uma competencia com o
# devido calculado mas SEM o aplicado informado saia como "ok", e nao esta ok: ninguem comparou
# nada. A memoria de enquadramento e documento com peso juridico; ela nao pode afirmar
# conformidade de uma competencia que nunca foi verificada.
#
# TRES ESTADOS, cada um com significado proprio (revisao da Carolina de 19/10, item 1):
#   conferencia — tem PENDENCIA: falta dado, o motor nao concluiu (FAP do ano ausente, CNAE fora
#                 do Anexo I, sem quantitativo declarado, obra CNO). Nada a afirmar. DERIVADO.
#   apurado     — o motor calculou ate o fim sem pendencia. E afirmacao do SISTEMA. DERIVADO.
#   conferido   — uma PESSOA examinou e validou, com autor e data gravados. E afirmacao de
#                 PESSOA. ARMAZENADO (migration 040). Nada chega aqui sem acao explicita.
#
# O QUE ESTAVA ERRADO ATE 19/10. "conferido" era derivado de "o aplicado esta informado e a
# comparacao fechou" — isto e, o sistema se autodeclarava conferido. A maquina tinha, de fato,
# dois estados (com e sem pendencia) e o rotulo do terceiro estava aplicado ao segundo. Um laudo
# afirmaria que N competencias foram conferidas por quem subscreve a peca; nao foram, e a peca
# leva a assinatura da advogada, nao a do sistema. Conferir e ato profissional, nao resultado de
# calculo — e e justamente onde o cliente paga para alguem assinar embaixo.
#
# Que o APLICADO esteja informado ou nao NAO e mais estado: e atributo, visivel nas colunas
# Aplicado e Divergencia. Misturar as duas coisas foi o erro.
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

# Quem afirma cada estado — o laudo precisa dizer isso com clareza.
AUTORIA_ESTADO = {
    SITUACAO_CONFERENCIA: "pendência: o sistema não concluiu",
    SITUACAO_APURADO: "afirmação do sistema",
    SITUACAO_CONFERIDO: "validado por pessoa",
}


def situacao_de(em_fila: bool, aliquota_devida, conferido_por=None) -> str:
    """Situacao da competencia. Ver os tres estados no cabecalho do modulo.

    'conferido_por' vem GRAVADO na linha: e o ato humano. O sistema nunca o preenche, e por isso
    nunca se autodeclara conferido. Competencia com pendencia nao pode ser conferida — nao ha o
    que validar —, por isso a pendencia e testada primeiro.

    A assinatura mudou em 19/10: o terceiro parametro era 'aliquota_aplicada' e produzia
    'conferido' sozinho. Quem chamar com o aplicado no lugar do autor recebe 'conferido' por
    engano, entao o parametro foi renomeado de proposito — uma chamada antiga nao passa calada.
    """
    if em_fila or aliquota_devida is None:
        return SITUACAO_CONFERENCIA
    if conferido_por:
        return SITUACAO_CONFERIDO
    return SITUACAO_APURADO


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
