# api/services/estabelecimento_ciclo_vida.py — AJUSTA
# Excluir estabelecimento: as travas e a trilha (decisao da Carolina, 01/11).
#
# POR QUE ESTE MODULO ESPELHA empresa_ciclo_vida.py E NAO O REAPROVEITA. As regras sao as mesmas
# em espirito e diferentes em objeto: la a trava protege o enquadramento de uma empresa inteira,
# aqui a de um estabelecimento. Uma funcao generica precisaria receber "qual tabela, qual coluna,
# qual mensagem" e produziria frases montadas por parametro — e as frases sao da Carolina, nao
# minhas. Dois modulos curtos e explicitos custam menos do que um abstrato.
#
# O QUE ELA DECIDIU, e vale registrar porque a assimetria com empresa e deliberada:
#
#   "Estabelecimento que fechou de verdade e encerrado pela data, nao excluido. Excluir fica para
#    cadastro feito por engano, com as mesmas travas da empresa. Nao precisa de 'arquivar' para
#    estabelecimento."
#
# NAO HA ARQUIVAR AQUI. O fechamento real ja tem caminho proprio — a data de encerramento, de que
# o status passou a derivar em 29/10. Um "arquivar" seria um segundo jeito de dizer a mesma coisa,
# que e exatamente o defeito que ela apontou quando status e data podiam se contradizer.
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.escritorio_evento import EscritorioEvento, EVENTO_ESTAB_EXCLUIDO
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_enquadramento import EstabelecimentoEnquadramento
from api.models.memoria_emitida import MemoriaEmitida

# O que o usuario digita para confirmar. Para CNPJ e o CNPJ; para obra e CAEPF, o identificador —
# pedir "o CNPJ" de uma obra seria pedir algo que ela nao tem.
ROTULO_IDENTIFICADOR = {"CNPJ": "o CNPJ", "CNO": "a matrícula CNO", "CAEPF": "o identificador CAEPF"}


def identificador_de(estab) -> str:
    """O numero que identifica o estabelecimento, qualquer que seja a natureza dele."""
    if (estab.tipo_estabelecimento or "CNPJ") == "CNPJ":
        return (estab.cnpj or "").strip()
    return (estab.identificador or "").strip()


def so_digitos(v: str | None) -> str:
    return "".join(c for c in (v or "") if c.isdigit())


async def competencias_conferidas(db: AsyncSession, estab_id) -> int:
    """Quantas competencias DESTE estabelecimento carregam assinatura de pessoa.

    Mesma regra da empresa, restrita a um estabelecimento: basta UMA competencia assinada para que
    apagar o cadastro destrua o registro que sustenta aquela assinatura.
    """
    return int((await db.execute(
        select(func.count(EstabelecimentoEnquadramento.id))
        .where(EstabelecimentoEnquadramento.estabelecimento_id == estab_id,
               EstabelecimentoEnquadramento.conferido_por.isnot(None))
    )).scalar() or 0)


async def memorias_emitidas(db: AsyncSession, estab_id) -> int:
    """Quantas VERSOES distintas de memoria sairam deste estabelecimento.

    Conta documentos, nao cliques — a unicidade por conteudo ja foi resolvida na gravacao
    (memoria_registro). Reemitir identico nao soma.
    """
    return int((await db.execute(
        select(func.count(MemoriaEmitida.id))
        .where(MemoriaEmitida.estabelecimento_id == estab_id)
    )).scalar() or 0)


async def dependentes_da_matriz(db: AsyncSession, estab) -> int:
    """Quantos OUTROS estabelecimentos existem na empresa, quando este e a matriz.

    Ela: "a matriz nao pode ser excluida enquanto houver filial ou obra cadastrada."
    O motivo e concreto: a raiz do CNPJ que toda filial precisa repetir sai da matriz, e o grau de
    risco de cada estabelecimento se apura contra o enquadramento dela. Apagar a matriz deixaria
    as filiais sem a referencia que as valida.

    Zero quando o estabelecimento nao e matriz — a pergunta nao se aplica.
    """
    if (estab.posicao or "") != "matriz":
        return 0
    return int((await db.execute(
        select(func.count(Estabelecimento.id))
        .where(Estabelecimento.empresa_id == estab.empresa_id,
               Estabelecimento.id != estab.id)
    )).scalar() or 0)


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


async def situacao_exclusao(db: AsyncSession, estab) -> dict:
    """Se o estabelecimento pode ser excluido, e por que nao, quando nao pode.

    Devolve as contagens mesmo quando a exclusao e possivel: a tela mostra os numeros, e um "nao
    pode" sem dizer quanto nem do que nao se confere.

    A ordem das razoes na mensagem nao e arbitraria. A da matriz vem primeiro porque e a unica que
    o usuario resolve mexendo em OUTRO cadastro; as outras duas sao definitivas e a saida delas e
    encerrar, nao excluir.
    """
    conferidas = await competencias_conferidas(db, estab.id)
    memorias = await memorias_emitidas(db, estab.id)
    dependentes = await dependentes_da_matriz(db, estab)
    pode = conferidas == 0 and memorias == 0 and dependentes == 0

    motivo = None
    if dependentes:
        motivo = (
            f"Esta é a matriz, e a empresa tem {_plural(dependentes, 'outro estabelecimento', 'outros estabelecimentos')} "
            "cadastrado. Exclua ou encerre os demais antes — a raiz do CNPJ das filiais vem da matriz."
        )
    elif not pode:
        partes = []
        if conferidas:
            partes.append(_plural(conferidas, "competência conferida", "competências conferidas"))
        if memorias:
            partes.append(_plural(memorias, "memória de cálculo emitida", "memórias de cálculo emitidas"))
        motivo = (
            f"Este estabelecimento tem {' e '.join(partes)}. "
            "Excluir apagaria o registro que sustenta esses documentos. "
            "Informe a data de encerramento em vez de excluir."
        )

    return {
        "pode_excluir": pode,
        "motivo": motivo,
        "competencias_conferidas": conferidas,
        "memorias_emitidas": memorias,
        "outros_estabelecimentos": dependentes,
        # A tela precisa saber O QUE pedir na confirmacao: CNPJ, matrícula CNO ou CAEPF.
        "confirmar_com": identificador_de(estab),
        "rotulo_confirmacao": ROTULO_IDENTIFICADOR.get(estab.tipo_estabelecimento or "CNPJ", "o identificador"),
    }


async def registrar_exclusao(
    db: AsyncSession, *, empresa, estab, autor: str, detalhe: str | None = None,
) -> EscritorioEvento:
    """Grava a exclusao na trilha do escritorio. NAO faz commit.

    Tudo e COPIA, lido agora: depois do delete nao ha de onde ler nada, e e justamente ai que a
    linha precisa continuar dizendo o que foi apagado e de quem era.

    A trilha nao tem chave estrangeira para empresas nem para estabelecimentos, de proposito — por
    isso a linha sobrevive ao delete. Gravar e apagar na MESMA transacao e o que garante que a
    trilha nunca afirme uma exclusao que nao aconteceu.
    """
    ev = EscritorioEvento(
        evento=EVENTO_ESTAB_EXCLUIDO,
        empresa_id=getattr(empresa, "id", None),
        razao_social=(getattr(empresa, "razao_social", None) or "").strip() or "(sem razão social)",
        cnpj=getattr(empresa, "cnpj", None),
        estabelecimento_nome=(getattr(estab, "nome", None) or "").strip() or "(sem nome)",
        estabelecimento_cnpj=identificador_de(estab) or None,
        autor=autor,
        ocorrido_em=datetime.now(timezone.utc),
        detalhe=detalhe,
    )
    db.add(ev)
    return ev


__all__ = [
    "identificador_de", "so_digitos", "competencias_conferidas", "memorias_emitidas",
    "dependentes_da_matriz", "situacao_exclusao", "registrar_exclusao",
]
