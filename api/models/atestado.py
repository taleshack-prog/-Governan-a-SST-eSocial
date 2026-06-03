# ==============================================================
# SST ESOCIAL GOV — Model: AtestadoMedico
# Arquivo: api/models/atestado.py
# ==============================================================
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base

class AtestadoMedico(Base):
    __tablename__ = "atestados_medicos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    afastamento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("afastamentos.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)
    nome_arquivo: Mapped[str | None] = mapped_column(String(300))
    conteudo_base64: Mapped[str | None] = mapped_column(Text)
    status_validacao: Mapped[str] = mapped_column(String(20), default="pendente")
    score_validacao: Mapped[float | None] = mapped_column(Float)
    cid_extraido: Mapped[str | None] = mapped_column(String(20))
    dias_extraidos: Mapped[int | None] = mapped_column(Integer)
    medico_nome: Mapped[str | None] = mapped_column(String(200))
    medico_crm: Mapped[str | None] = mapped_column(String(50))
    alertas: Mapped[list] = mapped_column(JSON, default=list)
    enviado_por: Mapped[str] = mapped_column(String(20), default="funcionario")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
