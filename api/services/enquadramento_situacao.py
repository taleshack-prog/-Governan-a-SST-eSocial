# api/services/enquadramento_situacao.py — SST ESOCIAL GOV
# Situacao de uma competencia do enquadramento (revisao da Carolina, item 5).
#
# O PROBLEMA QUE ISTO RESOLVE: havia dois estados — "conferencia" e "ok". Uma competencia com o
# devido calculado mas SEM o aplicado informado saia como "ok", e nao esta ok: ninguem comparou
# nada. A memoria de enquadramento e documento com peso juridico; ela nao pode afirmar
# conformidade de uma competencia que nunca foi verificada.
#
# QUATRO ESTADOS, cada um com significado proprio (tres da revisao de 19/10, item 1; o quarto
# do teste da Carolina em 22/10):
#   nao_auditada — o REGIME afasta a apuracao: Simples fora do Anexo IV, em que a patronal e o
#                 RAT estao no documento unico de arrecadacao. Nao ha aliquota devida, logo nao
#                 ha divergencia nem credito. Nao e pendencia: e ausencia de objeto. DERIVADO.
#   conferencia — tem PENDENCIA: falta dado e a comparacao nao fecha. Duas causas, mesmo estado:
#                 (a) o motor nao concluiu o DEVIDO (FAP do ano ausente, CNAE fora do Anexo I,
#                 sem quantitativo declarado, obra CNO); (b) o APLICADO nao veio desdobrado em
#                 RAT base e FAP, e entao o mesmo numero admite duas leituras opostas — ver
#                 situacao_de(). Nada a afirmar. DERIVADO.
#   apurado     — o motor concluiu a COMPARACAO: ha devido calculado e ha aplicado desdobrado
#                 para comparar com ele. E afirmacao do SISTEMA. DERIVADO.
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
# RESSALVA DE 24/10, que nao desfaz o paragrafo acima. O aplicado informado SEM DESDOBRAMENTO em
# RAT base e FAP nao e atributo faltando: e comparacao que nao fecha, porque o mesmo numero
# admite duas leituras com resultados opostos — uma afirma credito, a outra afirma divergencia
# zero. Ali o motor nao concluiu, escolheu. Ver situacao_de() para o caso concreto.
#
# Fonte unica: tela, API e PDF importam DESTE modulo. Se a regra mudar, muda em um lugar so.

SITUACAO_CONFERENCIA = "conferencia"
SITUACAO_APURADO = "apurado"
SITUACAO_CONFERIDO = "conferido"
# QUARTO ESTADO (22/10): o modulo nao se aplica aquela competencia. Nao e pendencia nem
# resultado — e ausencia de objeto. No Simples fora do Anexo IV a patronal, e o RAT com ela,
# esta dentro do documento unico de arrecadacao: nao ha aliquota devida a comparar com a
# aplicada, logo nao ha divergencia nem credito. DERIVADO do regime declarado.
SITUACAO_NAO_AUDITADA = "nao_auditada"

ROTULO = {
    SITUACAO_CONFERENCIA: "conferência",
    SITUACAO_APURADO: "apurado",
    SITUACAO_CONFERIDO: "conferido",
    SITUACAO_NAO_AUDITADA: "não auditada",
}

# Quem afirma cada estado — o laudo precisa dizer isso com clareza.
AUTORIA_ESTADO = {
    SITUACAO_CONFERENCIA: "pendência: o sistema não concluiu",
    SITUACAO_APURADO: "afirmação do sistema",
    SITUACAO_CONFERIDO: "validado por pessoa",
    SITUACAO_NAO_AUDITADA: "o regime afasta a apuração",
}


def situacao_de(*, rat_aplicavel: bool, em_fila: bool, aliquota_devida,
                rat_aplicado, fap_aplicado, conferido_por=None) -> str:
    """Situacao da competencia. Ver os quatro estados no cabecalho do modulo.

    'conferido_por' vem GRAVADO na linha: e o ato humano. O sistema nunca o preenche, e por isso
    nunca se autodeclara conferido. Competencia com pendencia nao pode ser conferida — nao ha o
    que validar —, por isso a pendencia e testada antes.

    'rat_aplicavel' e testado PRIMEIRO porque e de outra ordem: pendencia e falta de dado,
    inaplicabilidade e falta de objeto. Uma competencia que nao tem RAT a apurar nao fica
    "pendente" de nada — nao ha o que esperar.

    APLICADO SEM DESDOBRAMENTO E PENDENCIA (Carolina, 24/10). Entrou 'rat_aplicado'/'fap_aplicado'
    porque, sem eles, a comparacao NAO FECHA e o sistema estava escolhendo sozinho a leitura que
    gera credito. O caso dela, real: empresa grau 3, RAT base 3,00%, FAP publicado 0,5000, devida
    1,50%. A linha de aplicado guarda "3,00%" sem dizer se e base ou efetiva, e as duas leituras
    dao resultados opostos:
        3,00% como EFETIVA aplicada  -> divergencia +1,50 p.p. (credito a recuperar)
        3,00% como BASE aplicada     -> 3,00% x 0,5000 = 1,50% -> divergencia ZERO
    E o erro de digitacao mais provavel nesse campo e justamente escrever a base, porque o numero
    coincide com o grau. O achado inteiro depende de qual campo foi preenchido — e isso sai
    assinado. Nas palavras dela: "incerteza vai para a fila de conferencia, nunca vira premissa".

    ISTO NAO CONTRADIZ A DECISAO DE 19/10 ("que o aplicado esteja informado ou nao nao e estado,
    e atributo"). Aquilo separou 'o sistema calculou' de 'uma pessoa validou', e segue valendo. O
    que muda e o significado de 'apurado': e a afirmacao de que o motor CONCLUIU a comparacao.
    Sem o desdobramento ele nao concluiu — escolheu um dos dois sentidos possiveis. Competencia
    cuja comparacao nao fecha nao e apurada com um atributo faltando; e comparacao em aberto.

    A ORDEM IMPORTA: a falta do desdobramento e testada ANTES de 'conferido_por'. Invertendo,
    bastaria alguem clicar em Conferir para o sistema voltar a afirmar credito sobre o numero
    ambiguo — a assinatura passaria a valer como se fosse o dado que falta.

    A ASSINATURA E SO POR NOME, de proposito, e mudou tres vezes pelo mesmo motivo. Em 19/10 o
    terceiro parametro era 'aliquota_aplicada' e produzia 'conferido' sozinho. Em 22/10 entrou
    'rat_aplicavel', e sem ele uma competencia inaplicavel — que tem aliquota devida NULL —
    voltaria 'conferencia', afirmando pendencia onde nao ha nada a apurar. Agora entram as duas
    origens do aplicado, SEM VALOR PADRAO: chamada que nao as passe levanta TypeError na hora, em
    vez de devolver 'apurado' em silencio sobre uma comparacao que nao fechou.
    """
    if not rat_aplicavel:
        return SITUACAO_NAO_AUDITADA
    if em_fila or aliquota_devida is None:
        return SITUACAO_CONFERENCIA
    if rat_aplicado is None or fap_aplicado is None:
        return SITUACAO_CONFERENCIA
    if conferido_por:
        return SITUACAO_CONFERIDO
    return SITUACAO_APURADO


def divergencia_confirmada(rat_aplicado, fap_aplicado) -> bool:
    """A divergencia pode ser AFIRMADA? So quando o aplicado veio desdobrado.

    Existe como funcao, e nao como 'if' repetido em cada tela, porque a regra precisa ser a mesma
    nos tres lugares que mostram divergencia (cadastro, estabelecimentos, memoria). Era a
    duplicacao da regra que deixava a tela afirmar credito enquanto o quadro ao lado admitia, no
    mesmo cartao, que a origem nao podia ser afirmada.
    """
    return rat_aplicado is not None and fap_aplicado is not None


# Por que a competencia esta em conferencia. O texto vai para o rodape da tela e para a fila: o
# usuario precisa saber O QUE informar, nao so que algo falta.
FALTA_APLICADO = "Faltam o RAT base e o FAP aplicados."


def motivo_conferencia(*, em_fila: bool, motivo_fila, aliquota_devida,
                       rat_aplicado, fap_aplicado) -> str | None:
    """Motivo legivel da pendencia, ou None quando a competencia nao esta em conferencia.

    Duas pendencias diferentes caem no mesmo estado e pedem acoes opostas: a do motor se resolve
    declarando atividade, FAP ou CNAE; a do aplicado se resolve informando o que a empresa
    recolheu. Um rodape que diga apenas "em conferencia" manda o usuario procurar.
    """
    if em_fila or aliquota_devida is None:
        return motivo_fila or "O motor não concluiu a apuração desta competência."
    if rat_aplicado is None or fap_aplicado is None:
        return FALTA_APLICADO
    return None


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
