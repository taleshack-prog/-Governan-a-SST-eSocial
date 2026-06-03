# ==============================================================
# SST ESOCIAL GOV — Model: FuncionarioUsuario
# Arquivo: api/models/funcionario_usuario.py
# ==============================================================
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, UUID
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base

class FuncionarioUsuario(Base):
    __tablename__ = "funcionario_usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"))
    cpf: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200))
    telefone: Mapped[str | None] = mapped_column(String(20))
    senha_hash: Mapped[str | None] = mapped_column(String(200))
    senha_provisoria: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    primeiro_acesso: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
