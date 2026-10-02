# api/models/cnae_fpas_sugestao.py — SST ESOCIAL GOV
# Sugestao de FPAS por SECAO do CNAE (heuristica por setor — NAO e lei, requer
# validacao juridica). Usada so para PRE-SELECIONAR o FPAS na tela ("sugerido — confirmar").
# Seed na migration 024.
from sqlalchemy import String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class CnaeFpasSugestao(Base):
    __tablename__ = "cnae_fpas_sugestao"

    secao: Mapped[str] = mapped_column(String(1), primary_key=True)   # A..U
    divisao_ini: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    divisao_fim: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    setor: Mapped[str] = mapped_column(String(120), nullable=False)
    fpas_sugerido: Mapped[str] = mapped_column(String(4), nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(220))
    fonte: Mapped[str] = mapped_column(
        String(160), nullable=False,
        default="Heuristica por secao CNAE — requer validacao juridica",
    )
