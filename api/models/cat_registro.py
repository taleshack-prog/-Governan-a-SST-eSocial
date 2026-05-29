# api/models/cat_registro.py — SST ESOCIAL GOV
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class CatRegistro(Base):
    __tablename__ = "cat_registros"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)
    numero_cat: Mapped[str | None] = mapped_column(String(30))
    tipo_cat: Mapped[str | None] = mapped_column(String(20))
    data_acidente: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_acidente: Mapped[str | None] = mapped_column(Text)
    tipo_acidente: Mapped[str | None] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text)
    cid_principal: Mapped[str | None] = mapped_column(String(10))
    parte_corpo: Mapped[str | None] = mapped_column(String(100))
    agente_causador: Mapped[str | None] = mapped_column(String(200))
    afastamento: Mapped[bool] = mapped_column(Boolean, default=False)
    dias_afastamento: Mapped[int | None] = mapped_column(Integer)
    status_esocial: Mapped[str] = mapped_column(String(30), default="pendente")
    protocolo_esocial: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
