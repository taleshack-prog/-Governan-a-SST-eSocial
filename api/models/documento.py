# api/models/documento.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Date, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from api.database import Base


class DocumentoTecnico(Base):
    __tablename__ = "documentos_tecnicos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    estabelecimento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estabelecimentos.id"))
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    data_emissao: Mapped[date] = mapped_column(Date, nullable=False)
    data_validade: Mapped[date | None] = mapped_column(Date)
    responsavel_tecnico_nome: Mapped[str | None] = mapped_column(String(300))
    responsavel_tecnico_registro: Mapped[str | None] = mapped_column(String(50))
    responsavel_tecnico_conselho: Mapped[str | None] = mapped_column(String(20))
    versao: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="rascunho")
    storage_path: Mapped[str | None] = mapped_column(Text)
    storage_bucket: Mapped[str | None] = mapped_column(String(100))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_doc: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    empresa = relationship("Empresa", back_populates="documentos")
    agentes = relationship("AgenteNocivo", back_populates="documento_origem")
    validacoes = relationship("AiValidacao", back_populates="documento")
