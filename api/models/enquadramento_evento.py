# api/models/enquadramento_evento.py — AJUSTAPREV
# Trilha de eventos do enquadramento (migration 047, especificacao da Carolina de 21/10).
#
# A competencia ja registrava que uma conferencia tinha sido revogada, mas nao SOBRE QUAL NUMERO
# a pessoa havia assinado. Conferir e assinar sobre um valor determinado: sem guardar esse valor,
# o rastro diz que algo mudou e nao diz o que foi validado.
#
# Cada linha aqui e IMUTAVEL por contrato: nasce, nunca e alterada. O que muda e a competencia;
# o evento e a fotografia do que ela era no instante em que alguem agiu sobre ela.
import uuid
from datetime import datetime, date

from sqlalchemy import String, SmallInteger, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base

# Vocabulario fechado, espelhando o CHECK da migration. Importar daqui em vez de escrever a
# string solta em cada ponto de gravacao: evento gravado com texto que o CHECK recusa so falha
# em tempo de execucao, e normalmente no caminho que menos se testa.
EVENTO_APURADO = "apurado"            # o motor calculou, ou recalculou com numero diferente
EVENTO_CONFERIDO = "conferido"        # uma PESSOA validou
EVENTO_DESCONFERIDO = "desconferido"  # uma PESSOA retirou a propria validacao
EVENTO_REVOGADO = "revogado"          # o numero mudou por baixo de uma conferencia

EVENTOS = (EVENTO_APURADO, EVENTO_CONFERIDO, EVENTO_DESCONFERIDO, EVENTO_REVOGADO)

ROTULO_EVENTO = {
    EVENTO_APURADO: "apurado pelo sistema",
    EVENTO_CONFERIDO: "conferido por pessoa",
    EVENTO_DESCONFERIDO: "validação retirada",
    EVENTO_REVOGADO: "conferência revogada: o cálculo mudou",
}


class EnquadramentoEvento(Base):
    __tablename__ = "enquadramento_evento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # escritorio_id NAO e mapeado aqui, como nas demais tabelas do projeto: quem preenche e o
    # trigger trg_fill_escritorio, a partir da GUC app.escritorio. Mapear no ORM abriria caminho
    # para o codigo informar um escritorio — e a chave de isolamento nao pode vir do cliente.
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    evento: Mapped[str] = mapped_column(String(24), nullable=False)

    autor: Mapped[str | None] = mapped_column(String(200))
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # O retrato do calculo no instante do evento. COPIA, nao referencia: recalcular a competencia
    # amanha nao pode apagar o numero sobre o qual se assinou ontem.
    grau_risco: Mapped[int | None] = mapped_column(SmallInteger)
    aliquota_devida: Mapped[float | None] = mapped_column(Numeric(4, 2))
    fap: Mapped[float | None] = mapped_column(Numeric(5, 4))
    aliquota_efetiva: Mapped[float | None] = mapped_column(Numeric(6, 4))
    aliquota_aplicada: Mapped[float | None] = mapped_column(Numeric(6, 4))
    rat_aplicavel: Mapped[bool | None] = mapped_column(Boolean)

    # Nas revogacoes: [{"campo": "fap", "de": "1.0000", "para": "1.1500"}, ...]
    # Lista e nao par de colunas porque mais de um campo muda na mesma reapuracao — tipicamente
    # grau e fator juntos —, e um par obrigaria a escolher um e descartar o resto.
    #
    # none_as_null=True NAO E DETALHE. Em coluna JSON/JSONB o None do Python e ambiguo: pode
    # significar "sem valor" (SQL NULL) ou "o valor JSON null". O SQLAlchemy grava o SEGUNDO por
    # padrao, e o estrago aparece longe daqui: count(alteracoes) passa a contar a linha como se
    # ela tivesse diff, e jsonb_array_length() recebe um escalar e derruba a consulta inteira
    # com "cannot get array length of a scalar". Visto na primeira apuracao de teste, 23/10.
    alteracoes: Mapped[list | None] = mapped_column(JSONB(none_as_null=True))
    motivo: Mapped[str | None] = mapped_column(String(300))
