# api/models/vinculo.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Vinculo(Base):
    __tablename__ = "vinculos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    estabelecimento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estabelecimentos.id"))
    matricula: Mapped[str | None] = mapped_column(String(50))
    cargo: Mapped[str | None] = mapped_column(String(200))
    cbo: Mapped[str | None] = mapped_column(String(6))
    data_admissao: Mapped[date] = mapped_column(Date, nullable=False)
    data_demissao: Mapped[date | None] = mapped_column(Date)
    tipo_contrato: Mapped[str] = mapped_column(String(30), default="CLT")
    status: Mapped[str] = mapped_column(String(20), default="ativo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    trabalhador = relationship("Trabalhador", back_populates="vinculos")
