# api/models/fundamentacao_dispositivo.py — SST ESOCIAL GOV
# Um dispositivo de uma citacao, em campos separados (migration 045).
#
# POR QUE NAO E STRING. "Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3o e 4o" e
# UMA string com DOIS dispositivos de atos diferentes, e o sistema nao tinha como saber disso.
# Em texto corrido, o art. 202 do Decreto 3.048/99 — que e o nosso — e o art. 202 da IN RFB
# 2.110/2022, que trata de outra coisa, sao indistinguiveis. Em campos, nunca se confundem.
#
# A string exibida e montada na LEITURA, por api/services/fundamentacao.py. O banco guarda as
# partes; quem escreve string de volta no banco esta desfazendo o que esta tabela existe para
# resolver.
#
# Tabela de REFERENCIA, como a mae: global, sem escritorio_id e sem RLS. Nao contem dado de
# cliente.
import uuid
from datetime import datetime
from sqlalchemy import String, SmallInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class FundamentacaoDispositivo(Base):
    __tablename__ = "fundamentacao_dispositivo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fundamentacao_campo.id", ondelete="CASCADE"), nullable=False
    )
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    ato: Mapped[str] = mapped_column(String(120), nullable=False)      # "Lei 8.212/1991"
    artigo: Mapped[str | None] = mapped_column(String(20))             # "22", "202", "13"
    paragrafo: Mapped[str | None] = mapped_column(String(20))          # "3o", "5o-C", "unico"
    inciso: Mapped[str | None] = mapped_column(String(20))             # "II", "VI"
    alinea: Mapped[str | None] = mapped_column(String(10))             # "a", "b"
    anexo: Mapped[str | None] = mapped_column(String(60))              # "Anexo I"
    nota: Mapped[str | None] = mapped_column(String(200))              # "red. 10.410/2020"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
