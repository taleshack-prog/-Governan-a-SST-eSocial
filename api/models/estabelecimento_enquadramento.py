# api/models/estabelecimento_enquadramento.py — SST ESOCIAL GOV
# Enquadramento do ESTABELECIMENTO por vigencia (RN-17 / Adendo 03). O enquadramento
# (CNAE, atividade preponderante, grau, RAT, FPAS) nao e da empresa: e do estabelecimento,
# e muda no tempo. v1 grava uma linha (inicio=abertura, fim em aberto); Adendo 04 habilita periodos.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, SmallInteger, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoEnquadramento(Base):
    __tablename__ = "estabelecimento_enquadramento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)            # NULL = em aberto
    cnae: Mapped[str | None] = mapped_column(String(7))
    atividade_preponderante: Mapped[str | None] = mapped_column(Text)
    grau_risco: Mapped[int | None] = mapped_column(SmallInteger)
    aliquota_rat: Mapped[float | None] = mapped_column(Numeric(3, 2))
    codigo_fpas: Mapped[str | None] = mapped_column(String(4))
    codigo_terceiros: Mapped[str | None] = mapped_column(String(4))
    # fundamentacao propagada (RN-18)
    fund_dispositivo: Mapped[str | None] = mapped_column(String(200))
    fund_ato_normativo: Mapped[str | None] = mapped_column(String(200))
    fund_anexo: Mapped[str | None] = mapped_column(String(80))
    fund_vigencia: Mapped[str | None] = mapped_column(String(80))
    origem: Mapped[str] = mapped_column(String(16), nullable=False, default="declarado")  # consultado|declarado|manual
    confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
