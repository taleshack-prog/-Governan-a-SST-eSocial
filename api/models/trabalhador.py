# api/models/trabalhador.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Trabalhador(Base):
    __tablename__ = "trabalhadores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), nullable=False)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    sexo: Mapped[str | None] = mapped_column(String(1))
    pis_pasep: Mapped[str | None] = mapped_column(String(11))
    cargo: Mapped[str | None] = mapped_column(String(200))
    setor: Mapped[str | None] = mapped_column(String(200))
    matricula: Mapped[str | None] = mapped_column(String(50))
    data_admissao: Mapped[date | None] = mapped_column(Date)
    ges: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="trabalhadores")
    vinculos = relationship("Vinculo", back_populates="trabalhador")
    exames = relationship("ExameMedico", back_populates="trabalhador")
    agentes = relationship("AgenteNocivo", back_populates="trabalhador")
