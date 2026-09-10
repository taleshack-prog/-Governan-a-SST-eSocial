# api/models/memoria_prescricao.py — SST ESOCIAL GOV
# Etapa 4 (v2) / seção 10 — Memória de cálculo da prescrição (composição por competência).
import uuid
from datetime import datetime, date
from sqlalchemy import Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class MemoriaCalculoPrescricao(Base):
    __tablename__ = "memoria_calculo_prescricao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    achado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("achado.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor_competencia: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    dentro_janela: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)
    calculado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("achado_id", "competencia", "data_referencia"),)
