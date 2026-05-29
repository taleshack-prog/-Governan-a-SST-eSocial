# api/models/ai_validacao.py — SST ESOCIAL GOV
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from api.database import Base


class AiValidacao(Base):
    __tablename__ = "ai_validacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    documento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documentos_tecnicos.id"))
    tipo_validacao: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    confidence_score: Mapped[float | None] = mapped_column(Float)
    grade_label: Mapped[str | None] = mapped_column(String(10))
    resultado: Mapped[dict] = mapped_column(JSONB, default=dict)
    erros: Mapped[list] = mapped_column(JSONB, default=list)
    alertas: Mapped[list] = mapped_column(JSONB, default=list)
    sugestoes: Mapped[list] = mapped_column(JSONB, default=list)
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    documento = relationship("DocumentoTecnico", back_populates="validacoes")
