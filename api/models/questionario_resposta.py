# api/models/questionario_resposta.py — SST ESOCIAL GOV
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class QuestionarioResposta(Base):
    """Respostas do questionário de configuração (RF-0.06).
    Imutável e versionado (RN-03): nova resposta cria novo registro, a anterior
    é mantida. A resposta vigente de uma pergunta é o registro mais recente
    por (empresa_id, pergunta_codigo). Nunca fazer UPDATE."""
    __tablename__ = "questionario_resposta"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    pergunta_codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    resposta: Mapped[str] = mapped_column(Text, nullable=False)
    respondido_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id")
    )
    respondido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
