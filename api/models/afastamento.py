# ==============================================================
# SST ESOCIAL GOV — Models: Afastamentos
# Arquivo: api/models/afastamento.py
# ==============================================================

import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Date, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from api.database import Base


class Afastamento(Base):
    __tablename__ = "afastamentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)

    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    cid: Mapped[Optional[str]] = mapped_column(String(10))
    cid_descricao: Mapped[Optional[str]] = mapped_column(String(255))
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_prevista_retorno: Mapped[Optional[date]] = mapped_column(Date)
    data_retorno_real: Mapped[Optional[date]] = mapped_column(Date)
    dias_afastamento: Mapped[Optional[int]] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(50), default="recebido")

    num_atestados: Mapped[int] = mapped_column(Integer, default=0)
    num_indeferimentos: Mapped[int] = mapped_column(Integer, default=0)
    nexo_acidentario: Mapped[bool] = mapped_column(Boolean, default=False)
    cat_emitida: Mapped[bool] = mapped_column(Boolean, default=False)
    beneficio_inss: Mapped[Optional[str]] = mapped_column(String(10))

    salario_base: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    custo_primeiros_15dias: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    custo_total_estimado: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    responsavel_rh_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    motivo_informado: Mapped[Optional[str]] = mapped_column(Text)
    observacoes: Mapped[Optional[str]] = mapped_column(Text)
    historico: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))


class Atestado(Base):
    __tablename__ = "atestados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    afastamento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("afastamentos.id"), nullable=False)
    trabalhador_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trabalhadores.id"), nullable=False)

    data_emissao: Mapped[Optional[date]] = mapped_column(Date)
    data_inicio_repouso: Mapped[Optional[date]] = mapped_column(Date)
    dias_afastamento: Mapped[Optional[int]] = mapped_column(Integer)
    cid: Mapped[Optional[str]] = mapped_column(String(10))
    cid_descricao: Mapped[Optional[str]] = mapped_column(String(255))

    medico_nome: Mapped[Optional[str]] = mapped_column(String(255))
    medico_crm: Mapped[Optional[str]] = mapped_column(String(50))
    medico_especialidade: Mapped[Optional[str]] = mapped_column(String(100))

    status: Mapped[str] = mapped_column(String(50), default="pendente")
    checklist: Mapped[dict] = mapped_column(JSONB, default=dict)

    ai_validacao_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("ai_validacoes.id"))
    ai_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    ai_alertas: Mapped[list] = mapped_column(JSONB, default=list)

    storage_path: Mapped[Optional[str]] = mapped_column(String(500))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))


class AfastamentoMensagem(Base):
    __tablename__ = "afastamento_mensagens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    afastamento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("afastamentos.id"), nullable=False)
    remetente_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    remetente_tipo: Mapped[Optional[str]] = mapped_column(String(20))
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    lida: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AfastamentoNotificacao(Base):
    __tablename__ = "afastamento_notificacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    afastamento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("afastamentos.id"), nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(50))
    dias_antes: Mapped[Optional[int]] = mapped_column(Integer)
    data_programada: Mapped[Optional[date]] = mapped_column(Date)
    enviada: Mapped[bool] = mapped_column(Boolean, default=False)
    enviada_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
