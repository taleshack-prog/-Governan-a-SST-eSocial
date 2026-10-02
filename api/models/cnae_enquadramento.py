# api/models/cnae_enquadramento.py — SST ESOCIAL GOV
# Enquadramento CNAE -> grau de risco -> aliquota RAT (Modulo 4, Frente 1).
# Fonte: Anexo V do Decreto 3.048/99, redacao do Decreto 10.410/2020 (vigente), CNAE 2.3.
# Deterministico: grau 1=leve(1%), 2=medio(2%), 3=grave(3%). Seed na migration 022.
from datetime import datetime
from sqlalchemy import String, Text, SmallInteger, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class CnaeEnquadramento(Base):
    __tablename__ = "cnae_enquadramento"

    cnae: Mapped[str] = mapped_column(String(7), primary_key=True)          # 7 digitos, sem pontuacao
    cnae_fmt: Mapped[str] = mapped_column(String(10), nullable=False)       # ####-#/##
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    grau_risco: Mapped[int] = mapped_column(SmallInteger, nullable=False)   # 1 leve, 2 medio, 3 grave
    aliquota_rat: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 1.00 / 2.00 / 3.00
    fonte: Mapped[str] = mapped_column(
        String(160), nullable=False,
        default="Anexo V Decreto 3.048/99 (red. Decreto 10.410/2020), CNAE 2.3",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
