# api/models/fundamentacao_campo.py — SST ESOCIAL GOV
# Fundamentacao normativa dos campos derivados, VERSIONADA (item 3 da revisao da Carolina).
#
# Uma linha por (campo, vigencia). A interface pergunta campo + data e recebe o dispositivo em
# vigor naquela data — nunca texto escrito no codigo da tela. Quando a lei muda, acrescenta-se
# linha nova e fecha-se a antiga; documento gerado para competencia antiga segue citando o que
# valia na epoca.
#
# Tabela de REFERENCIA (RN-26): global, sem escritorio_id e sem RLS. Nao contem dado de cliente.
#
# Grau de risco e RAT devido nao estao aqui: a fundamentacao deles ja e gravada na linha apurada
# (estabelecimento_enquadramento.fund_*), que e a tabela que produziu o valor.
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class FundamentacaoCampo(Base):
    __tablename__ = "fundamentacao_campo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campo: Mapped[str] = mapped_column(String(40), nullable=False)
    dispositivo: Mapped[str] = mapped_column(String(300), nullable=False)
    ato_normativo: Mapped[str | None] = mapped_column(String(300))
    anexo: Mapped[str | None] = mapped_column(String(120))
    observacao: Mapped[str | None] = mapped_column(String(500))
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
