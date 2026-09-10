# api/services/alerta_documentos.py — SST ESOCIAL GOV
# Etapa 5 (v2) / Módulo 5 — Alerta de vencimento de documentos de SST.
# v2 seção 11.1: "Documento vencido ou a vencer em 60 dias → Consultivo → Perda da base de defesa".
from uuid import UUID
from datetime import date, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.estabelecimento import Estabelecimento
from api.models.documento import DocumentoTecnico
from api.models.achado import Achado

DIAS_ANTECEDENCIA = 60


async def gerar_alertas_documentos(empresa_id: UUID, db: AsyncSession) -> dict:
    hoje = date.today()
    limite = hoje + timedelta(days=DIAS_ANTECEDENCIA)

    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()
    if not estabs:
        return {"gerados": 0, "alertas": []}

    await db.execute(delete(Achado).where(
        Achado.estabelecimento_id.in_(estabs),
        Achado.origem_tipo == "documento_sst",
    ))

    docs = (await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.estabelecimento_id.in_(estabs),
            DocumentoTecnico.data_validade.isnot(None),
            DocumentoTecnico.data_validade <= limite,
        )
    )).scalars().all()

    gerados = []
    for doc in docs:
        dias = (doc.data_validade - hoje).days
        tipo_doc = (doc.tipo or "Documento").upper()
        if dias < 0:
            descricao = f"{tipo_doc} vencido há {-dias} dias — perda da base de defesa"
        elif dias == 0:
            descricao = f"{tipo_doc} vence hoje — perda da base de defesa"
        else:
            descricao = f"{tipo_doc} vence em {dias} dias — perda da base de defesa"

        db.add(Achado(
            estabelecimento_id=doc.estabelecimento_id,
            tipo="alerta",
            origem_tipo="documento_sst",
            origem_id=doc.id,
            descricao=descricao,
            grau_seguranca="consolidado",
            esfera="consultivo",
            tipo_valor=None,
            data_limite=doc.data_validade,
            prazo_dias=max(dias, 0),
            acao_sugerida="Renovar documento de SST",
            status="aberto",
        ))
        gerados.append({"documento": tipo_doc, "vence_em_dias": dias})

    await db.commit()
    return {"gerados": len(gerados), "alertas": gerados}
