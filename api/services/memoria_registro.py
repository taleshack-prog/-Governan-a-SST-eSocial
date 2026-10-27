# api/services/memoria_registro.py — AJUSTA
# Registro das memorias de calculo emitidas (Carolina, 27/10).
#
# "Alem de registrar autor e data da emissao, guarda uma copia do PDF emitido, ou pelo menos o
# hash dele. Os dados mudam e a memoria gerada depois sai diferente. Se um dia questionarem o que
# constava numa memoria que foi para uma peca, o registro precisa conseguir mostrar o documento
# exatamente como saiu."
#
# A REEMISSAO IDENTICA NAO CRIA REGISTRO NOVO. O endpoint da memoria e um GET: abrir a tela duas
# vezes, recarregar, ou o navegador reaproveitar o pedido geraria linhas repetidas e uma contagem
# de "memorias emitidas" sem sentido — e e essa contagem que a tela mostra e que trava a exclusao.
# A unicidade por (estabelecimento, sha256) resolve: conteudo igual atualiza a ultima emissao,
# conteudo DIFERENTE vira registro novo. O que se guarda e cada VERSAO do documento, que e
# exatamente o que ela quer poder provar.
#
# ESTE REGISTRO NUNCA DERRUBA A EMISSAO. Se gravar falhar, o PDF ainda tem de chegar a quem pediu:
# recusar o documento porque o arquivamento falhou seria trocar um problema por um pior. A falha
# sobe como aviso de log e quem chama decide.
import hashlib
import json
from datetime import date, datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.memoria_emitida import MemoriaEmitida, LIMITE_PDF_BYTES


def sha256_do(pdf: bytes) -> str:
    """Impressao digital do arquivo exatamente como ele saiu."""
    return hashlib.sha256(pdf).hexdigest()


# Campos que mudam a cada emissao sem que nada tenha mudado no caso. Ficam de fora da chave de
# conteudo, senao abrir a mesma tela duas vezes produz dois "documentos diferentes".
_VOLATEIS = ("gerado_em",)


def sha256_do_conteudo(dados: dict) -> str:
    """Impressao digital do CONTEUDO que gerou o documento, sem a hora de geracao.

    POR QUE NAO SERVE O HASH DO PDF AQUI. A memoria imprime "Documento gerado em 27/10/2026 às
    15:40": os bytes mudam a cada clique ainda que o caso esteja idêntico. Com o arquivo como
    chave, cinco aberturas da tela virariam cinco memorias emitidas — e esse numero aparece na
    tela e participa da trava da exclusao.

    Serializacao canonica (chaves ordenadas) para que o mesmo caso produza sempre a mesma chave.
    'default=str' cobre date e Decimal, que e o que o payload da memoria carrega.
    """
    limpo = {k: v for k, v in dados.items() if k not in _VOLATEIS}
    canonico = json.dumps(limpo, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


async def registrar_emissao(
    db: AsyncSession, *,
    empresa_id, estabelecimento_id,
    pdf: bytes,
    chave_conteudo: str,
    autor: str,
    competencia_inicio: date | None = None,
    competencia_fim: date | None = None,
) -> MemoriaEmitida:
    """Grava a emissao, com o documento. Devolve a linha (nova ou a atualizada).

    Nao faz commit: quem chama decide o momento, para que o registro entre na mesma transacao do
    resto do pedido.
    """
    digest = sha256_do(pdf)
    agora = datetime.now(timezone.utc)

    ja = (await db.execute(
        select(MemoriaEmitida).where(
            MemoriaEmitida.estabelecimento_id == estabelecimento_id,
            MemoriaEmitida.sha256_conteudo == chave_conteudo,
        )
    )).scalars().first()

    if ja is not None:
        # Mesmo conteudo, de novo. A copia guardada continua sendo a da PRIMEIRA emissao, e nao a
        # deste clique: e aquela que pode ter ido para a peca. A reemissao so acrescenta que
        # alguem viu o documento outra vez.
        ja.ultima_emissao_por = autor
        ja.ultima_emissao_em = agora
        ja.vezes = (ja.vezes or 1) + 1
        return ja

    registro = MemoriaEmitida(
        empresa_id=empresa_id,
        estabelecimento_id=estabelecimento_id,
        sha256=digest,
        sha256_conteudo=chave_conteudo,
        # Acima do teto grava-se o registro SEM a copia, e o tamanho real fica legivel na linha.
        # Dizer "nao guardei a copia, aqui esta a impressao digital" e melhor do que silenciar.
        pdf=pdf if len(pdf) <= LIMITE_PDF_BYTES else None,
        bytes_=len(pdf),
        competencia_inicio=competencia_inicio,
        competencia_fim=competencia_fim,
        emitida_por=autor,
        emitida_em=agora,
    )
    db.add(registro)
    return registro


async def quantas_emitidas(db: AsyncSession, empresa_id) -> int:
    """Quantas VERSOES distintas de memoria existem para a empresa.

    Conta documentos, nao cliques: reemitir o mesmo PDF nao soma. E o numero que a tela mostra
    ("2 memorias de cálculo emitidas") e que participa da trava da exclusao.
    """
    return int((await db.execute(
        select(func.count(MemoriaEmitida.id)).where(MemoriaEmitida.empresa_id == empresa_id)
    )).scalar() or 0)


async def listar_emitidas(db: AsyncSession, empresa_id) -> list[dict]:
    """As memorias guardadas, da mais recente para a mais antiga, SEM o PDF.

    O binario fica de fora de proposito: esta lista alimenta uma tela, e carregar o arquivo
    inteiro de cada linha para exibir uma data e desperdicio. O documento sai pelo endpoint que
    devolve um registro por vez.
    """
    linhas = (await db.execute(
        select(MemoriaEmitida).where(MemoriaEmitida.empresa_id == empresa_id)
        .order_by(MemoriaEmitida.emitida_em.desc())
    )).scalars().all()
    return [{
        "id": str(m.id),
        "estabelecimento_id": str(m.estabelecimento_id),
        "sha256": m.sha256,
        "sha256_conteudo": m.sha256_conteudo,
        "bytes": m.bytes_,
        "copia_guardada": m.pdf is not None,
        "competencia_inicio": m.competencia_inicio.isoformat() if m.competencia_inicio else None,
        "competencia_fim": m.competencia_fim.isoformat() if m.competencia_fim else None,
        "emitida_por": m.emitida_por,
        "emitida_em": m.emitida_em.isoformat() if m.emitida_em else None,
        "ultima_emissao_por": m.ultima_emissao_por,
        "ultima_emissao_em": m.ultima_emissao_em.isoformat() if m.ultima_emissao_em else None,
        "vezes": m.vezes,
    } for m in linhas]
