# api/models/indice_selic.py — SST ESOCIAL GOV
# Etapa precisão (roteiro Módulo 2) — Índice SELIC mensal (BCB série 4390).
from datetime import date, datetime
from sqlalchemy import Numeric, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class IndiceSelic(Base):
    __tablename__ = "indice_selic"

    competencia: Mapped[date] = mapped_column(Date, primary_key=True)
    taxa_mensal: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    fonte: Mapped[str] = mapped_column(String(50), default="BCB SGS 4390")
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
