# api/models/empresa.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, Boolean, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razao_social: Mapped[str] = mapped_column(String(300), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(300))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    cnae_principal: Mapped[str] = mapped_column(String(7), nullable=False)
    regime_tributario: Mapped[str | None] = mapped_column(String(50))
    grau_risco: Mapped[int | None] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relacionamentos
    estabelecimentos = relationship("Estabelecimento", back_populates="empresa", cascade="all, delete")
    trabalhadores = relationship("Trabalhador", back_populates="empresa", cascade="all, delete")
    plano: Mapped[str] = mapped_column(String(20), default="trial")
    plano_expira_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_trabalhadores: Mapped[int] = mapped_column(Integer, default=10)
    contato_nome: Mapped[str | None] = mapped_column(String(200))
    contato_email: Mapped[str | None] = mapped_column(String(200))
    contato_telefone: Mapped[str | None] = mapped_column(String(20))
    documentos = relationship("DocumentoTecnico", back_populates="empresa")
    usuarios = relationship("Usuario", back_populates="empresa")
