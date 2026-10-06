# api/models/empresa_regime.py — SST ESOCIAL GOV
# Regime tributario por periodo (RF-0.156). A empresa pode migrar de regime dentro da
# janela de 5 anos; um valor unico produz calculo errado nas competencias anteriores.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EmpresaRegime(Base):
    __tablename__ = "empresa_regime"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    regime: Mapped[str] = mapped_column(String(30), nullable=False)  # lucro_real|lucro_presumido|simples
    anexo_simples: Mapped[str | None] = mapped_column(String(10))
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
