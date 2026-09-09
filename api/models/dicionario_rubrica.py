# api/models/dicionario_rubrica.py — SST ESOCIAL GOV
# Etapa 3 (v2) / seção 8 — Dicionário de rubricas: o "cérebro" do Módulo de Folha.
# O campo `fundamento` é visível apenas no perfil da advogada — endpoints do cliente
# comum NÃO devem retorná-lo.
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class DicionarioRubrica(Base):
    __tablename__ = "dicionario_rubrica"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(60), nullable=False)
    codigo_esocial: Mapped[str | None] = mapped_column(String(20))
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    natureza_juridica: Mapped[str] = mapped_column(String(20), nullable=False)
    tratamento_correto: Mapped[str] = mapped_column(String(15), nullable=False)
    grau_seguranca: Mapped[str] = mapped_column(String(15), nullable=False)
    fundamento: Mapped[str | None] = mapped_column(Text)
    condicao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("slug"),)
