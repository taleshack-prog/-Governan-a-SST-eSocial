# api/models/achado.py — SST ESOCIAL GOV
# Etapa 3 (v2) / seção 7 — Achado: unifica crédito e passivo.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Numeric, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Achado(Base):
    __tablename__ = "achado"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    origem_tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="rubrica")
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    valor_mensal: Mapped[float | None] = mapped_column(Numeric(14, 2))
    valor_retroativo: Mapped[float | None] = mapped_column(Numeric(14, 2))
    aliquota_aplicada: Mapped[float | None] = mapped_column(Numeric(6, 4))
    grau_seguranca: Mapped[str | None] = mapped_column(String(15))
    data_prescricao_proxima: Mapped[date | None] = mapped_column(Date)
    esfera: Mapped[str | None] = mapped_column(String(20))
    prazo_dias: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="aberto")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
