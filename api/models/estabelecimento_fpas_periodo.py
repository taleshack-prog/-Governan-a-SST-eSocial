# api/models/estabelecimento_fpas_periodo.py — SST ESOCIAL GOV
# FPAS do estabelecimento COM VIGENCIA (revisao da Carolina, item 4). O FPAS determina a
# composicao de Terceiros, que muda dentro da janela de apuracao — por isso periodo, nao campo
# unico. Valor sempre declarado: a tabela do Anexo III so oferece as opcoes, nunca escolhe.
#
# NAO CONFUNDIR com EstabelecimentoFAP (api/models/estabelecimento_fap.py): FAP e o multiplicador
# do RAT, por ano; FPAS e o codigo da contribuicao a Terceiros, por periodo.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoFpasPeriodo(Base):
    __tablename__ = "estabelecimento_fpas_periodo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    codigo_fpas: Mapped[str] = mapped_column(String(4), nullable=False)
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date | None] = mapped_column(Date)
    declarado_por: Mapped[str | None] = mapped_column(String(200))
    declarado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
