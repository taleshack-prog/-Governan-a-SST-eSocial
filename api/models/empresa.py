# api/models/empresa.py — SST ESOCIAL GOV
import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, SmallInteger, Boolean, DateTime, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from api.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razao_social: Mapped[str] = mapped_column(String(300), nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String(300))
    cnpj: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    cnae_principal: Mapped[str | None] = mapped_column(String(7))  # DEPRECADO: enquadramento migra p/ estabelecimento (RN-17)
    regime_tributario: Mapped[str | None] = mapped_column(String(50))  # DEPRECADO: regime vira lista (empresa_regime)
    grau_risco: Mapped[int | None] = mapped_column(Integer)  # DEPRECADO (RN-17)

    # ---- Adendo 03 (RF-0.150/0.151) ----
    periodo_apuracao_inicio: Mapped[date | None] = mapped_column(Date)
    periodo_apuracao_fim: Mapped[date | None] = mapped_column(Date)
    origem_cadastro: Mapped[str | None] = mapped_column(String(16))  # consultado | declarado
    data_abertura: Mapped[date | None] = mapped_column(Date)       # excecao ano-calendario CPRB (RF-0.164)
    data_encerramento: Mapped[date | None] = mapped_column(Date)

    # ---- CPRB: estado explicito de verificacao (RF-0.163) ----
    # nao_informado (padrao) = ninguem verificou -> conferencia; nao_optante = marcado, patronal
    # cheia; optante = com a lista de periodos (empresa_cprb).
    cprb_status: Mapped[str] = mapped_column(String(16), nullable=False, default="nao_informado")
    cprb_verificado_por: Mapped[str | None] = mapped_column(String(200))
    cprb_verificado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ---- Endereco da matriz (migration 023/025) — espelha o estabelecimento ----
    endereco: Mapped[str | None] = mapped_column(String(500))   # logradouro
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(120))
    bairro: Mapped[str | None] = mapped_column(String(120))
    cidade: Mapped[str | None] = mapped_column(String(100))
    uf: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(9))

    # ---- Cadastro completo Módulo 0 / RF-0.01 (v2) ----
    codigo_fpas: Mapped[str | None] = mapped_column(String(4))
    anexo_simples: Mapped[str | None] = mapped_column(String(10))
    apura_cprb: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qtd_estabelecimentos: Mapped[int | None] = mapped_column(Integer)
    grau_risco_declarado: Mapped[int | None] = mapped_column(SmallInteger)
    rat_aplicado: Mapped[float | None] = mapped_column(Numeric(4, 2))
    possui_sesmt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    possui_cipa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relacionamentos
    estabelecimentos = relationship("Estabelecimento", back_populates="empresa", cascade="all, delete")
    trabalhadores = relationship("Trabalhador", back_populates="empresa", cascade="all, delete")
    cnaes_secundarios = relationship("EmpresaCnaeSecundario", back_populates="empresa", cascade="all, delete-orphan")
    plano: Mapped[str] = mapped_column(String(20), default="trial")
    plano_expira_em: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_trabalhadores: Mapped[int] = mapped_column(Integer, default=10)
    contato_nome: Mapped[str | None] = mapped_column(String(200))
    contato_email: Mapped[str | None] = mapped_column(String(200))
    contato_telefone: Mapped[str | None] = mapped_column(String(20))
    documentos = relationship("DocumentoTecnico", back_populates="empresa")
    usuarios = relationship("Usuario", back_populates="empresa")
