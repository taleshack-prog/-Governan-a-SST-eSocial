# api/models/tabela_fpas.py — SST ESOCIAL GOV
# Aliquotas de Terceiros por codigo FPAS, VERSIONADAS (migration 038).
#
# A chave e codigo_fpas + vigencia_inicio, nunca o codigo sozinho: o Radar analisa sessenta
# competencias, e uma tabela sem vigencia aplica a aliquota de hoje a todo o passado — errando
# sem emitir erro, porque o calculo conclui e devolve um numero.
#
# Os codigos vem do ANEXO II; as aliquotas, do ANEXO III. Sao anexos distintos da IN RFB
# 2.110/2022, e a citacao correta menciona os dois.
#
# Tres vigencias na janela de apuracao:
#   IN RFB 971/2009              ate a vigencia da IN RFB 2.110/2022
#   IN RFB 2.110/2022, Anexo III ate 31/03/2026
#   IN RFB 2.321/2026            de 01/04/2026 em diante (corte em 1º de ABRIL, nao na
#                                publicacao, que foi em 14/04/2026)
#
# Ler sempre por api/services/terceiros.py, que escolhe a linha pela competencia e devolve a
# fonte junto — o laudo cita o fundamento, e o fundamento muda.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Numeric, Boolean, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class TabelaFPAS(Base):
    __tablename__ = "tabela_fpas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_fpas: Mapped[str] = mapped_column(String(4), nullable=False)
    descricao: Mapped[str] = mapped_column(String(300), nullable=False)
    aliquota_terceiros: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    codigo_terceiros: Mapped[str | None] = mapped_column(String(4))
    # Ato normativo que fixou a aliquota. E a CHAVE DO BLOCO para o loader, que substitui um
    # ato inteiro de uma vez (scripts/carregar_tabela_fpas.py).
    fonte: Mapped[str] = mapped_column(String(120), nullable=False, default="IN RFB 971/2009 Anexo II")
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)     # NULL = em vigor
    confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Duas vigencias do mesmo codigo precisam coexistir, inclusive quando o valor nao muda:
    # o laudo cita o fundamento, e o fundamento muda.
    __table_args__ = (UniqueConstraint("codigo_fpas", "vigencia_inicio"),)
