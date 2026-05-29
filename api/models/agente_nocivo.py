# api/models/agente_nocivo.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class AgenteNocivo(Base):
    __tablename__ = "agentes_nocivos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"))
    vinculo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("vinculos.id"))
    codigo_tabela24: Mapped[str] = mapped_column(String(10), nullable=False)
    descricao_agente: Mapped[str] = mapped_column(Text, nullable=False)
    nivel_exposicao: Mapped[str | None] = mapped_column(String(100))
    unidade_medida: Mapped[str | None] = mapped_column(String(30))
    epc_eficaz: Mapped[bool | None] = mapped_column(Boolean)
    epi_eficaz: Mapped[bool | None] = mapped_column(Boolean)
    epi_ca: Mapped[str | None] = mapped_column(String(20))
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date)
    documento_origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documentos_tecnicos.id"))
    trecho_original: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    trabalhador = relationship("Trabalhador", back_populates="agentes")
    documento_origem = relationship("DocumentoTecnico", back_populates="agentes")
