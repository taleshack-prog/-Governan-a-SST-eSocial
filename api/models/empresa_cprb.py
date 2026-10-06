# api/models/empresa_cprb.py — SST ESOCIAL GOV
# CPRB por periodo (RF-0.157). A opcao e anual e a empresa entra e sai; um par unico de
# datas nao representa isso. Periodos limitados a ano-calendario, sem sobreposicao.
import uuid
from datetime import datetime, date
from sqlalchemy import Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EmpresaCprb(Base):
    __tablename__ = "empresa_cprb"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
