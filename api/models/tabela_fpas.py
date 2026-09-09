# api/models/tabela_fpas.py — SST ESOCIAL GOV
# Etapa 3 (v2) / fase 3A-2b — Alíquotas de Terceiros por código FPAS.
# Fonte oficial: IN RFB 971/2009, Anexo II.
import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class TabelaFPAS(Base):
    __tablename__ = "tabela_fpas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_fpas: Mapped[str] = mapped_column(String(4), nullable=False)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    aliquota_terceiros: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    codigo_terceiros: Mapped[str | None] = mapped_column(String(4))
    fonte: Mapped[str] = mapped_column(String(120), nullable=False, default="IN RFB 971/2009 Anexo II")
    confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("codigo_fpas"),)
