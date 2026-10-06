# api/models/estabelecimento_enquadramento.py — SST ESOCIAL GOV
# Enquadramento APURADO do estabelecimento (Adendo 04, secao 7). RESULTADO do motor:
# uma linha por competencia (RN-21). O grau e consequencia da atividade preponderante
# (RN-20), lido no Anexo I vigente, convertido em aliquota x FAP. Recalculavel sem perder
# historico (guarda data da apuracao e versao das tabelas).
import uuid
from datetime import datetime, date
from sqlalchemy import String, SmallInteger, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoEnquadramento(Base):
    __tablename__ = "estabelecimento_enquadramento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)          # 1o dia do mes
    cnae_preponderante: Mapped[str | None] = mapped_column(String(7))
    criterio: Mapped[str | None] = mapped_column(String(24))                 # maior_quantitativo|desempate_grau|fila_conferencia
    grau_risco: Mapped[int | None] = mapped_column(SmallInteger)
    aliquota_devida: Mapped[float | None] = mapped_column(Numeric(4, 2))
    fap: Mapped[float | None] = mapped_column(Numeric(5, 4))
    aliquota_efetiva: Mapped[float | None] = mapped_column(Numeric(6, 4))
    aliquota_aplicada: Mapped[float | None] = mapped_column(Numeric(4, 2))
    em_fila: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo_fila: Mapped[str | None] = mapped_column(String(200))
    fund_dispositivo: Mapped[str | None] = mapped_column(String(200))
    fund_ato_normativo: Mapped[str | None] = mapped_column(String(200))
    fund_anexo: Mapped[str | None] = mapped_column(String(80))
    fund_vigencia: Mapped[str | None] = mapped_column(String(80))
    data_apuracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    versao_tabelas: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (UniqueConstraint("estabelecimento_id", "competencia"),)
