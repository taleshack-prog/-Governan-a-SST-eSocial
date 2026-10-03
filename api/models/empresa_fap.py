# api/models/empresa_fap.py — SST ESOCIAL GOV
# FAP por ano da empresa (RF-0.135). Multiplicador 0,5 a 2,0 que multiplica o RAT.
# Uma linha por ano; o calculo retroativo usa o FAP de cada competencia, nunca o atual.
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, SmallInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EmpresaFAP(Base):
    __tablename__ = "empresa_fap"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    indice: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)  # 0.5000 a 2.0000
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("empresa_id", "ano"),)
