# api/services/fundamentacao.py — SST ESOCIAL GOV
# Resolvedor UNICO de citacao normativa (decisao da Carolina, 21/10).
#
# Recebe CAMPO + DATA e devolve o que a norma dizia NAQUELA data. Tela, apuracao, relatorio e
# memoria passam a ler daqui e de nenhum outro lugar.
#
# O QUE ISTO SUBSTITUI. Havia tres fontes para a mesma citacao, e elas divergiam com o tempo:
#   1) a tabela versionada, consultada SEM data — devolvia o dispositivo de hoje mesmo sobre
#      competencia antiga;
#   2) os campos congelados na linha apurada (estabelecimento_enquadramento.fund_*);
#   3) literais escritos no codigo Python, inclusive dentro do gerador da memoria — o documento
#      que vai assinado.
# A regra agora: a tabela versionada e a unica fonte do sistema. A citacao congelada deixa de
# ser campo da competencia e passa a ser parte do documento EMITIDO — a peca leva a propria
# copia do que citou, dentro dela.
#
# A DATA NAO TEM PADRAO SILENCIOSO. Quem chama informa a competencia. Era justamente o
# 'default: hoje' que fazia uma peca de 2021 citar a redacao de 2026 sem ninguem notar.
from datetime import date, timedelta

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.fundamentacao_campo import FundamentacaoCampo
from api.models.fundamentacao_dispositivo import FundamentacaoDispositivo


def _mais_de_um(valor: str) -> bool:
    """O campo traz mais de um dispositivo: '7º e 8º', '3º, 4º', '3º e 4º'.

    A praxe forense dobra o sinal no plural — "arts. 7º e 8º", "§§ 3º e 4º" —, e o montador
    escrevia sempre no singular, produzindo "art. 7º e 8º". O projeto ja tinha "§§ 3º e 4º"
    escrito a mao dentro das strings legadas; quando aquelas linhas forem decompostas, sairiam
    com o sinal errado sem este teste.
    """
    v = valor.strip()
    return " e " in v or "," in v


def _texto_dispositivo(d: FundamentacaoDispositivo) -> str:
    """Monta UM dispositivo a partir das partes separadas.

    A montagem vive aqui, na leitura, e nunca no banco: e a string montada que faz os dois
    'art. 202' do projeto colidirem — o do Decreto 3.048/99, que e o nosso, e o da IN RFB
    2.110/2022, que trata de outra coisa.
    """
    partes = [d.ato]
    if d.artigo:
        partes.append(f"{'arts.' if _mais_de_um(d.artigo) else 'art.'} {d.artigo.strip()}")
    if d.paragrafo:
        p = d.paragrafo.strip()
        # "unico" nao leva o sinal: escreve-se "parágrafo único".
        if p.lower().rstrip(".") in ("unico", "único"):
            partes.append("parágrafo único")
        else:
            partes.append(f"{'§§' if _mais_de_um(p) else '§'} {p}")
    if d.inciso:
        partes.append(d.inciso)                      # numeral romano, como na praxe: "art. 22, II"
    if d.alinea:
        partes.append(f'alínea "{d.alinea}"')
    if d.anexo:
        partes.append(d.anexo)
    texto = ", ".join(partes)
    return f"{texto} ({d.nota})" if d.nota else texto


async def citacao_de(campo: str, em: date, db: AsyncSession) -> dict | None:
    """Citacao vigente para o campo NA data informada. None quando nao ha linha cadastrada.

    None e resposta legitima e significa "nao ha fundamentacao cadastrada" — nunca se completa
    com texto de reserva. Documento sem citacao nao emite; tela sem citacao nao exibe icone.
    """
    f = (await db.execute(
        select(FundamentacaoCampo).where(
            FundamentacaoCampo.campo == campo,
            FundamentacaoCampo.vigencia_inicio <= em,
            or_(FundamentacaoCampo.vigencia_fim.is_(None), FundamentacaoCampo.vigencia_fim >= em),
        ).order_by(FundamentacaoCampo.vigencia_inicio.desc()).limit(1)
    )).scalars().first()
    if f is None:
        return None

    disp = (await db.execute(
        select(FundamentacaoDispositivo)
        .where(FundamentacaoDispositivo.campo_id == f.id)
        .order_by(FundamentacaoDispositivo.ordem, FundamentacaoDispositivo.created_at)
    )).scalars().all()

    # Estruturado quando houver; legado enquanto a decomposicao juridica nao tiver sido feita.
    # Nenhuma das duas formas e inventada aqui: ou veio decomposta, ou veio como foi cadastrada.
    if disp:
        montado = "; ".join(_texto_dispositivo(d) for d in disp)
        estruturado = True
    else:
        montado = (f.dispositivo or "").strip() or None
        estruturado = False

    if not montado:
        return None     # linha existe mas nao diz nada: equivale a nao haver citacao

    return {
        "campo": f.campo,
        "dispositivo": montado,
        "estruturado": estruturado,
        "dispositivos": [
            {"ordem": d.ordem, "ato": d.ato, "artigo": d.artigo, "paragrafo": d.paragrafo,
             "inciso": d.inciso, "alinea": d.alinea, "anexo": d.anexo, "nota": d.nota,
             "texto": _texto_dispositivo(d)}
            for d in disp
        ],
        "ato_normativo": f.ato_normativo,
        "anexo": f.anexo,
        "observacao": f.observacao,
        "vigencia_inicio": f.vigencia_inicio.isoformat(),
        "vigencia_fim": f.vigencia_fim.isoformat() if f.vigencia_fim else None,
        "em": em.isoformat(),      # a data consultada viaja junto: e o que torna a citacao auditavel
    }


# CRITERIO DO CORTE ENTRE VIGENCIAS (decisao da Carolina, 25/10, item 7).
#
# O DEFEITO. A competencia e guardada como o primeiro dia do mes, e era por ele que a citacao se
# resolvia. Quando uma norma passa a valer no MEIO do mes — a IN RFB 2.110/2022 comeca em
# 17/10/2022 —, a competencia 10/2022 caia na redacao anterior, e o documento imprimia
# "Competencias 11/2021 a 10/2022 ... Redacao vigente desde 01/07/2020 ate 16/10/2022": o proprio
# bloco dizia que aquela redacao tinha acabado no dia 16 e, ainda assim, fundamentava outubro
# inteiro com ela. Nenhum numero mudava — o criterio das duas INs e identico —, mas e
# inconsistencia visivel dentro de peca assinada, e e o tipo de coisa que a fiscalizacao usa para
# questionar o resto.
#
# O CRITERIO. A competencia segue a norma vigente no seu FECHAMENTO. 10/2022 passa para o bloco
# novo, e os blocos ficam 11/2021 a 09/2022 e 10/2022 em diante.
#
# Nas palavras dela: "o criterio precisa estar escrito no documento, nao so no codigo" — por isso
# a constante abaixo, que a memoria imprime junto da fundamentacao.
TEXTO_CRITERIO_VIGENCIA = (
    "Quando uma norma passa a vigorar no curso de um mês, a competência inteira é fundamentada "
    "pela redação vigente no seu <b>fechamento</b>. É o critério adotado em todos os cortes de "
    "vigência deste documento."
)


def fechamento_da_competencia(comp: date) -> date:
    """Ultimo dia do mes da competencia — a data pela qual a citacao se resolve.

    Ver TEXTO_CRITERIO_VIGENCIA acima para o porque.
    """
    if comp.month == 12:
        return comp.replace(day=31)
    return comp.replace(month=comp.month + 1, day=1) - timedelta(days=1)


async def citacoes_do_periodo(campo: str, competencias: list[date], db: AsyncSession) -> list[dict]:
    """A citacao de cada competencia, colapsada em blocos de redacao igual.

    Uma memoria cobre dezenas de competencias. Se a norma mudou no meio do periodo, imprimir UMA
    citacao para a serie inteira e afirmar sobre meses que ela nao governa — era o que a citacao
    congelada na primeira linha fazia. Aqui cada competencia e resolvida na sua propria data e
    meses consecutivos com a MESMA redacao viram um bloco com o intervalo que ele governa.

    Resolve competencia por competencia de proposito, sem atalho. O atalho obvio — "enquanto a
    competencia couber na vigencia do bloco anterior, repete" — erra quando uma redacao mais nova
    comeca dentro da janela da anterior: as duas cobrem o mes, e a vigente e a mais recente.

    Bloco com citacao None e LACUNA: competencia sem fundamentacao cadastrada. Vem explicita para
    quem chama recusar a emissao, nunca para ser preenchida com texto de reserva.
    """
    blocos: list[dict] = []
    for comp in competencias:
        c = await citacao_de(campo, fechamento_da_competencia(comp), db)
        chave = (c or {}).get("vigencia_inicio")      # None agrupa lacunas consecutivas
        if blocos and blocos[-1]["chave"] == chave:
            blocos[-1]["ate"] = comp
            continue
        blocos.append({"chave": chave, "citacao": c, "de": comp, "ate": comp})
    return blocos


async def historico_de(campo: str, db: AsyncSession) -> list[dict]:
    """Todas as vigencias do campo, da mais antiga para a mais nova, ja montadas."""
    linhas = (await db.execute(
        select(FundamentacaoCampo).where(FundamentacaoCampo.campo == campo)
        .order_by(FundamentacaoCampo.vigencia_inicio)
    )).scalars().all()
    saida = []
    for f in linhas:
        # Resolve cada vigencia no seu proprio inicio: e a data em que aquela redacao valia.
        c = await citacao_de(campo, f.vigencia_inicio, db)
        if c:
            saida.append(c)
    return saida
