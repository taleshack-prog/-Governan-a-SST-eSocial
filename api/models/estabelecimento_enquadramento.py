# api/models/estabelecimento_enquadramento.py — SST ESOCIAL GOV
# Enquadramento APURADO do estabelecimento (Adendo 04, secao 7). RESULTADO do motor:
# uma linha por competencia (RN-21). O grau e consequencia da atividade preponderante
# (RN-20), lido no Anexo I vigente, convertido em aliquota x FAP. Recalculavel sem perder
# historico (guarda data da apuracao e versao das tabelas).
import uuid
from datetime import datetime, date
from sqlalchemy import String, SmallInteger, Numeric, Boolean, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class EstabelecimentoEnquadramento(Base):
    __tablename__ = "estabelecimento_enquadramento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estabelecimento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)          # 1o dia do mes
    cnae_preponderante: Mapped[str | None] = mapped_column(String(7))
    criterio: Mapped[str | None] = mapped_column(String(24))                 # maior_quantitativo|desempate_grau|fila_conferencia
    grau_risco: Mapped[int | None] = mapped_column(SmallInteger)
    aliquota_devida: Mapped[float | None] = mapped_column(Numeric(4, 2))
    fap: Mapped[float | None] = mapped_column(Numeric(5, 4))
    aliquota_efetiva: Mapped[float | None] = mapped_column(Numeric(6, 4))
    # Efetiva aplicada na competencia. Quatro casas (migration 036): o produto RAT x FAP, com
    # FAP de quatro casas, era truncado em duas.
    aliquota_aplicada: Mapped[float | None] = mapped_column(Numeric(6, 4))
    # As DUAS origens aplicadas, propagadas do rat_aplicado (migration 036). Sem elas o painel
    # e a memoria sabem que divergiu e nao sabem de onde — e e a origem que decide a defesa.
    rat_aplicado: Mapped[float | None] = mapped_column(Numeric(4, 2))
    fap_aplicado: Mapped[float | None] = mapped_column(Numeric(5, 4))
    processo_rat: Mapped[str | None] = mapped_column(String(120))
    processo_fap: Mapped[str | None] = mapped_column(String(120))
    # ATO HUMANO (migration 040). O motor NUNCA preenche estas duas: conferir e ato profissional,
    # nao resultado de calculo, e e aqui que fica registrada a assinatura de quem valida.
    conferido_por: Mapped[str | None] = mapped_column(String(200))
    conferido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Rastro da revogacao: conferir e assinar sobre um numero determinado; se o numero mudou,
    # a assinatura nao corresponde mais a nada, mas o historico de que existiu permanece.
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revogado_por: Mapped[str | None] = mapped_column(String(200))
    revogado_de: Mapped[str | None] = mapped_column(String(200))
    em_fila: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    motivo_fila: Mapped[str | None] = mapped_column(String(200))
    # APLICABILIDADE DO MODULO (migration 046). No Simples fora do Anexo IV a patronal — e o RAT
    # com ela — esta dentro do documento unico de arrecadacao, entao NAO HA RAT a apurar. Isso
    # nao e divergencia zero: e ausencia de aliquota devida a comparar com a aplicada.
    # em_fila e PENDENCIA (falta dado); rat_aplicavel=False e AUSENCIA DE OBJETO. Nao confundir.
    rat_aplicavel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Regime e anexo congelados na linha: a peca precisa dizer o fato E a fonte, e nao teria o
    # que afirmar se a competencia so soubesse que nao foi auditada.
    regime_competencia: Mapped[str | None] = mapped_column(String(30))
    anexo_competencia: Mapped[str | None] = mapped_column(String(10))
    # consultado | declarado — decide o tempo verbal da peca. Preenchida quando a procedencia
    # do regime existir; ate la, toda declaracao de regime e do contribuinte.
    regime_origem: Mapped[str | None] = mapped_column(String(16))
    motivo_inaplicavel: Mapped[str | None] = mapped_column(String(300))
    # LEGADO — APOSENTADAS (decisao da Carolina, 21/10). A citacao normativa nao e dado da
    # competencia: e resolvida na tabela versionada (fundamentacao_campo) pela DATA da competencia.
    # Estas quatro congelavam o texto no momento da apuracao e divergiam da tabela com o tempo;
    # fund_vigencia guardava a versao das TABELAS DE CALCULO e era impressa como se fosse a
    # vigencia da norma. Ninguem mais escreve nem le estas colunas.
    # Nao apagar aqui: as colunas saem na limpeza de colunas aposentadas, DEPOIS que este codigo
    # estiver em producao. Derrubar coluna que a versao anterior da API ainda le quebraria a API
    # no intervalo entre a migration e o deploy — a ordem e inversa a de quando se acrescenta.
    fund_dispositivo: Mapped[str | None] = mapped_column(String(200))
    fund_ato_normativo: Mapped[str | None] = mapped_column(String(200))
    fund_anexo: Mapped[str | None] = mapped_column(String(80))
    fund_vigencia: Mapped[str | None] = mapped_column(String(80))
    data_apuracao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    versao_tabelas: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (UniqueConstraint("estabelecimento_id", "competencia"),)
