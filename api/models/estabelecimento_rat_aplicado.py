# api/models/estabelecimento_rat_aplicado.py — SST ESOCIAL GOV
# RAT que a empresa efetivamente aplicou, por periodo (Adendo 04 RF-0.179). Separado do
# devido (principio 1.1). Sem preenchimento automatico. A divergencia devido x aplicado e o achado.
import uuid
from datetime import datetime, date
from sqlalchemy import Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoRatAplicado(Base):
    __tablename__ = "estabelecimento_rat_aplicado"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    aliquota: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
