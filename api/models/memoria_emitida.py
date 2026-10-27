# api/models/memoria_emitida.py — AJUSTA
# A memoria de calculo como ela SAIU, guardada no ato da emissao (migration 054).
#
# Carolina, 27/10: "alem de registrar autor e data da emissao, guarda uma copia do PDF emitido, ou
# pelo menos o hash dele. Os dados mudam e a memoria gerada depois sai diferente. Se um dia
# questionarem o que constava numa memoria que foi para uma peca, o registro precisa conseguir
# mostrar o documento exatamente como saiu."
#
# Registrar que houve emissao e metade da prova; a outra metade e o conteudo. Basta alguem alterar
# um FAP para que a mesma memoria, gerada de novo, saia diferente da que foi protocolada.
#
# POR QUE O PDF, E NAO SO O HASH. O hash confere um arquivo que alguem ja tenha em maos; quando o
# arquivo se perdeu, ele nao devolve nada. A copia e que responde "o que constava". O SHA-256 vai
# junto por outro motivo: e ele que permite demonstrar que a copia guardada nao foi trocada.
#
# Esta tabela e uma das duas condicoes que impedem a exclusao da empresa — a outra e haver
# competencia conferida.
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, LargeBinary, CHAR, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base

# Teto para guardar o arquivo inline. A memoria tem tres paginas e fica na casa das dezenas de
# kilobytes; o teto existe para o caso anomalo, e acima dele grava-se o registro com o hash e sem
# a copia, dizendo isso de forma explicita em vez de silenciar.
LIMITE_PDF_BYTES = 8 * 1024 * 1024


class MemoriaEmitida(Base):
    __tablename__ = "memoria_emitida"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # escritorio_id fica a cargo do trigger, como nas demais tabelas.

    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )

    # sha256         — do ARQUIVO guardado: prova de que a copia nao foi trocada.
    # sha256_conteudo — do CONTEUDO, sem a hora de geracao: chave de deduplicacao.
    # Sao dois porque o documento imprime "gerado em ... às ...", e o arquivo muda a cada emissao
    # mesmo sem mudanca nos dados. Deduplicar pelo arquivo contaria cada abertura da tela como uma
    # memoria nova — numero que a tela mostra e que trava a exclusao.
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    sha256_conteudo: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    pdf: Mapped[bytes | None] = mapped_column(LargeBinary)      # nulo acima de LIMITE_PDF_BYTES
    bytes_: Mapped[int] = mapped_column("bytes", Integer, nullable=False)

    competencia_inicio: Mapped[date | None] = mapped_column(Date)
    competencia_fim: Mapped[date | None] = mapped_column(Date)

    # Primeira e ultima emissao DESTE conteudo. Reemitir identico nao cria registro novo: a
    # unicidade e (estabelecimento_id, sha256), e so um documento diferente vira linha nova — que
    # e justamente o fato a provar, de que a memoria de uma data nao era a de outra.
    emitida_por: Mapped[str] = mapped_column(String(200), nullable=False)
    emitida_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ultima_emissao_por: Mapped[str | None] = mapped_column(String(200))
    ultima_emissao_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vezes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
