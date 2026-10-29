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
# FONTE UNICA (decisao da Carolina, 21/10). Esta tabela e a unica fonte do sistema: tela,
# apuracao e calculo leem so dela, pela data da competencia. O comentario anterior aqui dizia o
# oposto — que grau de risco e RAT devido viviam congelados na linha apurada — e isso produziu
# DUAS fontes para a mesma citacao, que divergiam com o tempo. A citacao congelada deixa de ser
# campo da competencia; quando houver emissao de documento, a peca levara a propria copia do que
# citou, dentro dela. Enquanto nao houver, ela simplesmente sai.
#
# 'dispositivo' e LEGADO desde a migration 045: a citacao estruturada vive em
# fundamentacao_dispositivo, uma linha por dispositivo, em campos separados. A leitura usa o
# estruturado quando existe e cai no legado enquanto nao existe.
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
    dispositivo: Mapped[str | None] = mapped_column(String(300))   # LEGADO (045): ver cabeçalho
    ato_normativo: Mapped[str | None] = mapped_column(String(300))
    # 200 desde a migration 062: a citacao do RAT devido vigente passou a trazer os DOIS anexos —
    # o Anexo V do Decreto, que e a fonte normativa do grau, e o Anexo I da IN, que e a tabela com
    # que a Receita o aplica — com o nome oficial completo, e isso da 151 caracteres. O limite
    # antigo eram 120, e o UPDATE nao truncaria: falharia.
    anexo: Mapped[str | None] = mapped_column(String(200))
    observacao: Mapped[str | None] = mapped_column(String(500))
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
