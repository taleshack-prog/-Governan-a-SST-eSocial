# api/models/escritorio.py — SST ESOCIAL GOV
# Adendo 05: o ESCRITORIO e o tenant/limite de isolamento (RN-24). Quem contrata o Radar.
# Modalidade define o modo de operacao do MESMO produto: 'oaas' (operacao propria da advogada)
# ou 'saas' (contador/advogado contratante). Um unico codigo, dois modos — nao ha fork.
import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Escritorio(Base):
    __tablename__ = "escritorios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razao_social: Mapped[str] = mapped_column(String(300), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14))
    modalidade: Mapped[str] = mapped_column(String(10), nullable=False, default="oaas")  # saas | oaas
    plano: Mapped[str] = mapped_column(String(30), nullable=False, default="trial")
    data_contratacao: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ativo")  # ativo|suspenso|encerrado
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
