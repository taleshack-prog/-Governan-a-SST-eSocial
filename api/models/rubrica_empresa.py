# api/models/rubrica_empresa.py — SST ESOCIAL GOV
# Etapa 3 (v2) / seção 7 — Rubricas como a empresa parametrizou a folha.
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class RubricaEmpresa(Base):
    __tablename__ = "rubrica_empresa"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    codigo_esocial: Mapped[str | None] = mapped_column(String(20))
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    natureza_declarada: Mapped[str | None] = mapped_column(String(30))
    incide_inss_praticado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    incide_fgts_praticado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valor_mensal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    dicionario_rubrica_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dicionario_rubrica.id")
    )
    status_conciliacao: Mapped[str] = mapped_column(String(12), nullable=False, default="pendente")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
