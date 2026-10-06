# api/models/estabelecimento_fap.py — SST ESOCIAL GOV
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, SmallInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoFAP(Base):
    """FAP por ano, por estabelecimento (Adendo 04 RF-0.177). 0,5000 a 2,0000, 4 casas.
    Campo vazio NÃO é 1,0000 — vai à fila de conferência. Com origem e data."""
    __tablename__ = "estabelecimento_fap"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    ano_vigencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    valor_fap: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)  # 0.5000 a 2.0000
    origem: Mapped[str | None] = mapped_column(String(16))
    declarado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("estabelecimento_id", "ano_vigencia"),)

    estabelecimento = relationship("Estabelecimento", back_populates="faps")
