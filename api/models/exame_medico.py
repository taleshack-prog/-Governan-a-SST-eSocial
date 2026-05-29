# api/models/exame_medico.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class ExameMedico(Base):
    __tablename__ = "exames_medicos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)
    vinculo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vinculos.id"))
    tipo_exame: Mapped[str] = mapped_column(String(30), nullable=False)
    data_exame: Mapped[date] = mapped_column(Date, nullable=False)
    data_validade: Mapped[date | None] = mapped_column(Date)
    medico_nome: Mapped[str | None] = mapped_column(String(300))
    medico_crm: Mapped[str | None] = mapped_column(String(20))
    resultado: Mapped[str | None] = mapped_column(String(20))
    observacoes: Mapped[str | None] = mapped_column(Text)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documentos_tecnicos.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    trabalhador = relationship("Trabalhador", back_populates="exames")
