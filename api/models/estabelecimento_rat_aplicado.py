# api/models/estabelecimento_rat_aplicado.py — SST ESOCIAL GOV
# RAT que a empresa efetivamente aplicou, por periodo (Adendo 04 RF-0.179). Separado do
# devido (principio 1.1). Sem preenchimento automatico. A divergencia e o achado.
#
# DESDOBRADO EM DUAS ORIGENS (migration 036). No eSocial, evento S-1005, a empresa declara
# aliqRat, fap e aliqRatAjust, e o proprio eSocial valida que a terceira e o produto das duas.
# Logo o erro nunca esta no ajustado: esta no GRAU ou no FATOR. E a resposta decide a defesa —
# grau errado se corrige com reenquadramento e memoria de atividade preponderante; FAP errado,
# com a portaria e o extrato do FAPWeb.
#
# Os campos de processo existem porque o leiaute do eSocial so aceita aliquota divergente da
# prevista se houver processo informado: sem eles o sistema apontaria divergencia onde existe
# decisao amparando.
import uuid
from datetime import datetime, date
from sqlalchemy import Numeric, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoRatAplicado(Base):
    __tablename__ = "estabelecimento_rat_aplicado"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    # Efetiva aplicada (S-1005 aliqRatAjust). DERIVADA do par abaixo quando ele existe; nas
    # linhas antigas, o valor informado isolado. Quatro casas: FAP tem quatro.
    aliquota: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    aliquota_rat: Mapped[float | None] = mapped_column(Numeric(4, 2))   # 1 | 2 | 3 (aliqRat)
    fap_aplicado: Mapped[float | None] = mapped_column(Numeric(5, 4))   # 0,5000 a 2,0000 (fap)
    processo_rat: Mapped[str | None] = mapped_column(String(120))
    processo_fap: Mapped[str | None] = mapped_column(String(120))
    inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
