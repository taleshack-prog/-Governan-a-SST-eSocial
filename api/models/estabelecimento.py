# api/models/estabelecimento.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, UniqueConstraint, SmallInteger, Numeric, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Estabelecimento(Base):
    __tablename__ = "estabelecimentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id", ondelete="CASCADE"), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    nome: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14))
    cnae: Mapped[str | None] = mapped_column(String(7))
    endereco: Mapped[str | None] = mapped_column(String(500))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))

    # ---- Custeio por estabelecimento (Alteração 1 / TDD 7.1) ----
    posicao: Mapped[str] = mapped_column(String(10), nullable=False, default="filial")
    cnae_secundarios: Mapped[str | None] = mapped_column(String)
    grau_risco: Mapped[int | None] = mapped_column(SmallInteger)
    aliquota_rat: Mapped[float | None] = mapped_column(Numeric(4, 2))
    fpas: Mapped[str | None] = mapped_column(String(4))
    num_empregados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    folha_mensal: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # ---- Cadastro Módulo 0 / RF-0.03 (v2) ----
    tipo_estabelecimento: Mapped[str] = mapped_column(String(4), nullable=False, default="CNPJ")
    atividade_descrita: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="ativa")
    data_inicio: Mapped[date | None] = mapped_column(Date)
    data_prevista_conclusao: Mapped[date | None] = mapped_column(Date)
    identificador: Mapped[str | None] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("empresa_id", "codigo"),)

    empresa = relationship("Empresa", back_populates="estabelecimentos")
    faps = relationship("EstabelecimentoFAP", back_populates="estabelecimento", cascade="all, delete-orphan")
