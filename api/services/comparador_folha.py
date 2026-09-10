# api/services/comparador_folha.py — SST ESOCIAL GOV
# Etapa 3 (v2) / fase 3A-3 — Comparador de folha: gera os achados.
from uuid import UUID
from datetime import date
from api.services.regua_prescricao import calcular_regua
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_fap import EstabelecimentoFAP
from api.models.rubrica_empresa import RubricaEmpresa
from api.models.dicionario_rubrica import DicionarioRubrica
from api.models.tabela_fpas import TabelaFPAS
from api.models.achado import Achado

COTA_PATRONAL = Decimal("0.20")
MESES_PRESCRICAO = 60


async def _aliquota_terceiros(empresa: Empresa, db: AsyncSession) -> Decimal:
    if not empresa.codigo_fpas:
        return Decimal("0")
    row = (await db.execute(
        select(TabelaFPAS).where(TabelaFPAS.codigo_fpas == empresa.codigo_fpas)
    )).scalar_one_or_none()
    if row is None or row.aliquota_terceiros is None:
        return Decimal("0")
    return Decimal(str(row.aliquota_terceiros)) / Decimal("100")


async def _rat_fap(estab: Estabelecimento, db: AsyncSession, ano: int) -> Decimal:
    if estab.aliquota_rat is None:
        return Decimal("0")
    fap_row = (await db.execute(
        select(EstabelecimentoFAP).where(
            EstabelecimentoFAP.estabelecimento_id == estab.id,
            EstabelecimentoFAP.ano_vigencia == ano,
        )
    )).scalar_one_or_none()
    fap = Decimal(str(fap_row.valor_fap)) if fap_row else Decimal("1")
    return (Decimal(str(estab.aliquota_rat)) / Decimal("100")) * fap


async def _conciliar(rubrica: RubricaEmpresa, db: AsyncSession) -> DicionarioRubrica | None:
    if rubrica.codigo_esocial:
        d = (await db.execute(
            select(DicionarioRubrica).where(
                DicionarioRubrica.codigo_esocial == rubrica.codigo_esocial,
                DicionarioRubrica.ativo == True,
            )
        )).scalar_one_or_none()
        if d:
            return d
    desc = (rubrica.descricao or "").lower()
    dics = (await db.execute(select(DicionarioRubrica).where(DicionarioRubrica.ativo == True))).scalars().all()
    for d in dics:
        chave = d.descricao.lower().split("(")[0].strip()
        if chave and (chave[:20] in desc or any(p in desc for p in chave.split()[:2] if len(p) > 4)):
            return d
    return None


async def comparar_estabelecimento(estab, empresa, db, ano) -> list[dict]:
    aliq_terceiros = await _aliquota_terceiros(empresa, db)
    rat_fap = await _rat_fap(estab, db, ano)
    aliquota_efetiva = COTA_PATRONAL + rat_fap + aliq_terceiros

    rubricas = (await db.execute(
        select(RubricaEmpresa).where(RubricaEmpresa.estabelecimento_id == estab.id)
    )).scalars().all()

    achados = []
    for r in rubricas:
        dic = await _conciliar(r, db)
        if dic is None:
            r.status_conciliacao = "pendente"
            continue
        r.dicionario_rubrica_id = dic.id
        r.status_conciliacao = "conciliada"

        divergente = r.incide_inss_praticado and dic.tratamento_correto == "nao_incide"
        if not divergente:
            continue

        valor = Decimal(str(r.valor_mensal or 0))
        credito_mensal = (valor * aliquota_efetiva).quantize(Decimal("0.01"))
        credito_retro = (credito_mensal * MESES_PRESCRICAO).quantize(Decimal("0.01"))

        if dic.grau_seguranca == "consolidado":
            tipo = "credito"
        elif dic.grau_seguranca == "provavel":
            tipo = "alerta"
        else:
            continue

        # Enriquecimento do alerta (v2 Alteração 4, seção 11.1): divergência de rubrica
        # consolidada = esfera consultivo; a régua de prescrição é o "prazo".
        tipo_valor = "recuperacao" if tipo == "credito" else "exposicao"
        data_limite = None
        if tipo == "credito":
            r_regua = calcular_regua(credito_mensal)
            data_limite = date.fromisoformat(r_regua["data_prescricao_proxima"])

        achados.append({
            "estabelecimento_id": estab.id,
            "tipo": tipo,
            "origem_id": r.id,
            "descricao": f"{dic.descricao} — INSS recolhido indevidamente",
            "valor_mensal": float(credito_mensal) if tipo == "credito" else None,
            "valor_retroativo": float(credito_retro) if tipo == "credito" else None,
            "aliquota_aplicada": float(aliquota_efetiva),
            "grau_seguranca": dic.grau_seguranca,
            "esfera": "consultivo",
            "tipo_valor": tipo_valor,
            "data_limite": data_limite,
            "acao_sugerida": "Solicitar análise jurídica",
        })
    return achados


async def rodar_comparador(empresa_id: UUID, db: AsyncSession, ano: int | None = None) -> dict:
    if ano is None:
        ano = date.today().year
    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()
    if empresa is None:
        return {"erro": "Empresa não encontrada", "achados": []}
    estabs = (await db.execute(
        select(Estabelecimento).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()

    todos = []
    for estab in estabs:
        await db.execute(delete(Achado).where(
            Achado.estabelecimento_id == estab.id,
            Achado.origem_tipo == "rubrica",
        ))
        achados = await comparar_estabelecimento(estab, empresa, db, ano)
        for a in achados:
            db.add(Achado(**a, origem_tipo="rubrica"))
        todos.extend(achados)
    await db.commit()

    total_credito = sum(a["valor_retroativo"] or 0 for a in todos if a["tipo"] == "credito")
    return {
        "empresa_id": str(empresa_id),
        "ano": ano,
        "total_achados": len(todos),
        "creditos": sum(1 for a in todos if a["tipo"] == "credito"),
        "alertas": sum(1 for a in todos if a["tipo"] == "alerta"),
        "total_credito_retroativo_estimado": round(total_credito, 2),
        "achados": todos,
    }
