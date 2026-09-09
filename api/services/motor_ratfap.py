# api/services/motor_ratfap.py — SST ESOCIAL GOV
# Etapa 2 (v2) / bloco RAT×FAP do diagnóstico.
# Calcula, POR ESTABELECIMENTO, o RAT efetivo (aliquota_rat × FAP do ano) e compara
# com o que a empresa declara pagar. Reporta crédito (paga a mais) E passivo (paga a
# menos) — os dois sentidos são obrigatórios (v2): omitir o passivo expõe juridicamente.
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.estabelecimento_fap import EstabelecimentoFAP

TOLERANCIA = Decimal("0.01")


async def calcular_ratfap(empresa_id: UUID, db: AsyncSession, ano: int | None = None) -> dict:
    if ano is None:
        ano = date.today().year

    empresa = (await db.execute(
        select(Empresa).where(Empresa.id == empresa_id)
    )).scalar_one_or_none()
    if empresa is None:
        return {"bloco": "RAT×FAP", "semaforo": "amarelo",
                "motivo": "Empresa não encontrada", "estabelecimentos": []}

    estabs = (await db.execute(
        select(Estabelecimento).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()

    if not estabs:
        return {"bloco": "RAT×FAP", "semaforo": "amarelo",
                "motivo": "Nenhum estabelecimento cadastrado", "estabelecimentos": []}

    rat_declarado = empresa.rat_aplicado

    total_pago = Decimal("0")
    total_esperado = Decimal("0")
    detalhe = []
    houve_pendencia = False

    for e in estabs:
        item = {"codigo": e.codigo, "nome": e.nome,
                "aliquota_rat": float(e.aliquota_rat) if e.aliquota_rat is not None else None,
                "folha_mensal": float(e.folha_mensal or 0)}

        fap_row = (await db.execute(
            select(EstabelecimentoFAP).where(
                EstabelecimentoFAP.estabelecimento_id == e.id,
                EstabelecimentoFAP.ano_vigencia == ano,
            )
        )).scalar_one_or_none()

        if e.aliquota_rat is None or fap_row is None or not e.folha_mensal or rat_declarado is None:
            item["semaforo"] = "amarelo"
            faltando = []
            if e.aliquota_rat is None: faltando.append("RAT do estabelecimento")
            if fap_row is None: faltando.append(f"FAP {ano}")
            if not e.folha_mensal: faltando.append("folha mensal")
            if rat_declarado is None: faltando.append("RAT declarado pela empresa")
            item["motivo"] = "Pendência: " + ", ".join(faltando)
            houve_pendencia = True
            detalhe.append(item)
            continue

        folha = Decimal(str(e.folha_mensal))
        fap = Decimal(str(fap_row.valor_fap))
        rat_base = Decimal(str(e.aliquota_rat)) / Decimal("100")
        rat_efetivo = rat_base * fap
        esperado = (folha * rat_efetivo).quantize(Decimal("0.01"))
        pago = (folha * (Decimal(str(rat_declarado)) / Decimal("100"))).quantize(Decimal("0.01"))
        diff = (pago - esperado).quantize(Decimal("0.01"))

        item["fap"] = float(fap)
        item["rat_efetivo_pct"] = float((rat_efetivo * 100).quantize(Decimal("0.01")))
        item["valor_esperado"] = float(esperado)
        item["valor_pago"] = float(pago)
        item["diferenca"] = float(diff)

        if esperado > 0 and abs(diff) / esperado <= TOLERANCIA:
            item["semaforo"] = "verde"; item["natureza"] = "conferido"
        elif diff > 0:
            item["semaforo"] = "vermelho"; item["natureza"] = "credito"
        else:
            item["semaforo"] = "vermelho"; item["natureza"] = "passivo"

        total_pago += pago
        total_esperado += esperado
        detalhe.append(item)

    diff_total = (total_pago - total_esperado).quantize(Decimal("0.01"))
    if houve_pendencia and total_esperado == 0:
        semaforo = "amarelo"; natureza = "pendencia"
    elif total_esperado > 0 and abs(diff_total) / total_esperado <= TOLERANCIA:
        semaforo = "verde"; natureza = "conferido"
    elif diff_total > 0:
        semaforo = "vermelho"; natureza = "credito"
    elif diff_total < 0:
        semaforo = "vermelho"; natureza = "passivo"
    else:
        semaforo = "amarelo"; natureza = "pendencia"

    return {
        "bloco": "RAT×FAP",
        "ano": ano,
        "semaforo": semaforo,
        "natureza": natureza,
        "valor_pago_mensal": float(total_pago.quantize(Decimal("0.01"))),
        "valor_esperado_mensal": float(total_esperado.quantize(Decimal("0.01"))),
        "diferenca_mensal": float(diff_total),
        "impacto_anual_estimado": float((abs(diff_total) * 12).quantize(Decimal("0.01"))),
        "tem_pendencia": houve_pendencia,
        "estabelecimentos": detalhe,
    }
