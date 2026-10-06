# api/models/estabelecimento_atividade.py — SST ESOCIAL GOV
# Atividades declaradas do estabelecimento (Adendo 04, secao 2.1 / RF-0.173). INPUT do motor.
# Cada linha: subclasse CNAE, descricao, quantitativo de segurados EMPREGADOS + AVULSOS
# (RN-22: nao entram contribuintes individuais, socios/diretores, estagiarios, terceirizados),
# por periodo de vigencia, com autoria da declaracao (RN-23). Nova linha so quando a composicao muda.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoAtividade(Base):
    __tablename__ = "estabelecimento_atividade"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    cnae: Mapped[str] = mapped_column(String(7), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    quantitativo: Mapped[int | None] = mapped_column(Integer)      # NULL = nao declarado
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)        # NULL = em aberto
    declarado_por: Mapped[str | None] = mapped_column(String(160))
    declarado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
