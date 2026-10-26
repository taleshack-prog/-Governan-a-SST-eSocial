# api/services/cprb_transicao.py — AJUSTA
# A TRANSICAO DA CPRB ATE A EXTINCAO (revisao da Carolina, 26/10, pontos 3 e 4).
#
# Fonte unica das proporcoes e das regras do periodo de transicao. Existe como modulo, e nao
# como texto na tela, porque a mesma informacao aparece em tres lugares — o bloco do cadastro, a
# memoria de calculo e, quando houver, o comparador de folha. Duas copias da mesma regra divergem
# com o tempo: foi o que aconteceu com a citacao do § 3º e com a frase do aprendiz.
#
# O QUE A LEI 14.973/2024 FEZ. Ate 2024 a CPRB substituia integralmente a contribuicao patronal
# dos incisos I e III do art. 22 da Lei 8.212/91. De 2025 a 2027 as duas passam a coexistir em
# proporcoes decrescentes/crescentes, e em 2028 a CPRB se extingue.
#
# A RESSALVA DO DECIMO TERCEIRO, que faltava na tela (ponto 3 da revisao). Nas palavras dela:
# "Pelo art. 9º-A, §1º, da Lei 12.546/2011 (incluido pela Lei 14.973/2024), nesses tres anos os
# incisos I e III NAO incidem sobre o 13º. O RAT, ao contrario, incide."
#
# A tela dizia apenas "2025: 5% · 2026: 10% · 2027: 15%". Quem calculasse a patronal por essa
# linha aplicaria 5% sobre uma folha que inclui o decimo terceiro — cobrando a mais em tres
# exercicios. E quem generalizasse a regra para o RAT deixaria de cobra-lo sobre o 13º, que e o
# erro inverso e igualmente grave.

# Incisos I e III do art. 22 da Lei 8.212/91: 20% sobre a remuneracao. E a base sobre a qual as
# proporcoes abaixo incidem.
ALIQUOTA_INCISOS_I_III = 20.0

# ano -> (percentual da aliquota setorial da CPRB, percentual dos incisos I e III sobre a folha)
TRANSICAO = {
    2025: (80.0, 25.0),
    2026: (60.0, 50.0),
    2027: (40.0, 75.0),
}

ANO_EXTINCAO = 2028          # a partir daqui nao ha CPRB (Lei 14.973/2024)
ANO_INICIO_TRANSICAO = 2025
ANO_MINIMO = 2011            # a CPRB nasce com a Lei 12.546/2011

# Os anos em que os incisos I e III NAO alcancam o decimo terceiro. O RAT nunca entrou nesta
# regra — e por isso que ela precisa ser dita, e nao deduzida.
ANOS_SEM_DECIMO_TERCEIRO = tuple(TRANSICAO.keys())

TEXTO_DECIMO_TERCEIRO = (
    "Em 2025, 2026 e 2027 os incisos I e III não incidem sobre o décimo terceiro salário. "
    "O RAT não está nessa regra: incide sobre o décimo terceiro em todos os anos. "
    "RAT e Terceiros são sempre devidos."
)

TEXTO_ANO_CALENDARIO = (
    "A opção se manifesta no pagamento da CPRB de janeiro e é irretratável para todo o "
    "ano-calendário. Cada ano é uma opção nova — não existe período em aberto."
)


def regra_do_ano(ano: int) -> dict:
    """O que vale naquele ano-calendario. Nunca levanta: ano fora da faixa volta descrito.

    'folha_efetiva' e a aliquota que de fato incide sobre a folha — o percentual do ano aplicado
    sobre os 20% dos incisos. E o numero que a tela mostrava sozinho ("5%"), sem dizer de onde
    vinha nem sobre o que deixava de incidir.
    """
    if ano >= ANO_EXTINCAO:
        return {"ano": ano, "existe": False,
                "motivo": f"CPRB extinta a partir de {ANO_EXTINCAO} (Lei 14.973/2024)."}
    if ano < ANO_MINIMO:
        return {"ano": ano, "existe": False,
                "motivo": f"A CPRB foi instituída pela Lei 12.546/2011; não há opção antes de {ANO_MINIMO}."}
    cprb_pct, folha_pct = TRANSICAO.get(ano, (100.0, 0.0))
    return {
        "ano": ano,
        "existe": True,
        "cprb_percentual": cprb_pct,
        "folha_percentual": folha_pct,
        "folha_efetiva": round(folha_pct * ALIQUOTA_INCISOS_I_III / 100, 2),
        "coexiste": ano in TRANSICAO,
        # A ressalva vale SO nos anos de transicao: antes de 2025 nao ha patronal parcial a
        # ressalvar, porque a CPRB substituia os incisos por inteiro.
        "sem_decimo_terceiro": ano in ANOS_SEM_DECIMO_TERCEIRO,
    }


def anos_disponiveis() -> list[int]:
    """Anos que o seletor pode oferecer. Nao inclui 2028 em diante: o regime foi extinto, e
    oferecer o ano seria convidar a declarar opcao que a lei nao admite."""
    return list(range(ANO_MINIMO, ANO_EXTINCAO))


def tabela() -> list[dict]:
    """A transicao inteira, para a tela montar as colunas sem repetir a regra."""
    return [regra_do_ano(a) for a in anos_disponiveis()]
