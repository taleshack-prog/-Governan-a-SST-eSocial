# api/models/cprb_transicao.py — SST ESOCIAL GOV
# Transicao da CPRB, VERSIONADA (RF-0.158 / RN-18). A partir de 01/2025 a CPRB coexiste
# com a cota patronal parcial (Lei 14.973/2024); ate 12/2024 substitui integralmente.
# RAT e Terceiros permanecem devidos em qualquer cenario. Seed na migration 027.
from sqlalchemy import String, SmallInteger, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class CprbTransicao(Base):
    __tablename__ = "cprb_transicao"

    ano_inicio: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ano_fim: Mapped[int | None] = mapped_column(SmallInteger)              # NULL = em diante
    cprb_receita_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))  # NULL em 2028 (extinta)
    patronal_folha_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    substitui_integral: Mapped[bool] = mapped_column(Boolean, nullable=False)  # true ate 2024
    fonte: Mapped[str] = mapped_column(String(120), nullable=False,
                                       default="Lei 12.546/2011; transicao Lei 14.973/2024")
