# api/models/estabelecimento_fap.py — SST ESOCIAL GOV
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, SmallInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoFAP(Base):
    """FAP por ano de vigência (0.5 a 2.0). Histórico imutável: um registro por
    estabelecimento por ano, nunca sobrescrito (TDD 7.2)."""
    __tablename__ = "estabelecimento_fap"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    ano_vigencia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    valor_fap: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 0.50 a 2.00
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("estabelecimento_id", "ano_vigencia"),)

    estabelecimento = relationship("Estabelecimento", back_populates="faps")
