# api/models/empresa_cnae_secundario.py — SST ESOCIAL GOV
import uuid
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EmpresaCnaeSecundario(Base):
    """CNAEs secundários da empresa (RF-0.01). Lista 1:N."""
    __tablename__ = "empresa_cnae_secundario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False
    )
    cnae: Mapped[str] = mapped_column(String(7), nullable=False)

    __table_args__ = (UniqueConstraint("empresa_id", "cnae"),)

    empresa = relationship("Empresa", back_populates="cnaes_secundarios")
