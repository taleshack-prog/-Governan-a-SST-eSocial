# api/routers/relatorios.py — SST ESOCIAL GOV
# Etapa 5 (v2) / Módulo 6 — Endpoint do relatório executivo (PDF para download).
from datetime import date
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.empresa import Empresa
from api.models.estabelecimento import Estabelecimento
from api.models.achado import Achado
from api.models.usuario import Usuario
from api.auth import get_current_user
from api.services.motor_ratfap import calcular_ratfap
from api.services.regua_prescricao import calcular_regua
from api.services.relatorio_executivo import gerar_relatorio_executivo
from api.services.dossie_prova import gerar_dossie_prova
from api.models.memoria_prescricao import MemoriaCalculoPrescricao
from api.models.rubrica_empresa import RubricaEmpresa
from api.models.dicionario_rubrica import DicionarioRubrica

router = APIRouter()

_EXIBICAO = {"verde": "Conferido", "amarelo": "Pendência de informação", "vermelho": "Divergência identificada"}


@router.get("/executivo")
async def relatorio_executivo(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Gera o relatório executivo mensal em PDF para a empresa do usuário logado."""
    empresa_id = current_user.empresa_id

    empresa = (await db.execute(select(Empresa).where(Empresa.id == empresa_id))).scalar_one_or_none()

    # Blocos (RAT×FAP calculado + os demais pendentes)
    ratfap = await calcular_ratfap(empresa_id, db)
    ratfap["exibicao"] = _EXIBICAO.get(ratfap.get("semaforo"), "")
    blocos = [
        {"bloco": "Cota Patronal", "exibicao": "Pendência de informação"},
        ratfap,
        {"bloco": "Terceiros", "exibicao": "Pendência de informação"},
        {"bloco": "FGTS", "exibicao": "Pendência de informação"},
    ]

    # Achados da empresa
    estabs = (await db.execute(
        select(Estabelecimento.id).where(Estabelecimento.empresa_id == empresa_id)
    )).scalars().all()
    achados = []
    total_credito = 0.0
    total_prescreve_90 = 0.0
    if estabs:
        rows = (await db.execute(
            select(Achado).where(Achado.estabelecimento_id.in_(estabs))
            .order_by(Achado.valor_retroativo.desc().nullslast())
        )).scalars().all()
        for a in rows:
            achados.append({
                "descricao": a.descricao, "tipo": a.tipo, "esfera": a.esfera,
                "prazo_dias": a.prazo_dias, "valor_retroativo": float(a.valor_retroativo) if a.valor_retroativo else None,
            })
            if a.tipo == "credito" and a.valor_retroativo:
                total_credito += float(a.valor_retroativo)
                if a.valor_mensal:
                    total_prescreve_90 += calcular_regua(a.valor_mensal)["valor_prescreve_90dias"]

    dados = {
        "empresa": {"razao_social": empresa.razao_social if empresa else "—"},
        "competencia": date.today().strftime("%m/%Y"),
        "blocos": blocos,
        "creditos": {"total_credito": round(total_credito, 2), "total_prescreve_90dias": round(total_prescreve_90, 2)},
        "achados": achados,
    }

    pdf = gerar_relatorio_executivo(dados)
    filename = f"relatorio-executivo-{date.today().strftime('%Y-%m')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dossie/{achado_id}")
async def dossie_prova(
    achado_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Gera o dossiê de prova de um achado. Fundamento só para perfil admin/advogada
    (v2 linha 191)."""
    from uuid import UUID as _UUID
    aid = _UUID(achado_id)

    achado = (await db.execute(select(Achado).where(Achado.id == aid))).scalar_one_or_none()
    if achado is None:
        return Response(content=b"", status_code=404)

    # isolamento: o achado precisa ser de um estabelecimento da empresa do usuário
    estab = (await db.execute(
        select(Estabelecimento).where(Estabelecimento.id == achado.estabelecimento_id)
    )).scalar_one_or_none()
    if estab is None or estab.empresa_id != current_user.empresa_id:
        return Response(content=b"", status_code=403)

    empresa = (await db.execute(select(Empresa).where(Empresa.id == estab.empresa_id))).scalar_one_or_none()

    # memória de cálculo (a prova)
    mem_rows = (await db.execute(
        select(MemoriaCalculoPrescricao).where(MemoriaCalculoPrescricao.achado_id == aid)
    )).scalars().all()
    memoria = [{"competencia": m.competencia.isoformat(), "valor_competencia": float(m.valor_competencia)} for m in mem_rows]

    # fundamento (do dicionário, via a rubrica de origem) — só se perfil permite
    incluir_fund = current_user.perfil in ("admin", "advogada")
    fundamento = None
    if incluir_fund and achado.origem_id:
        rub = (await db.execute(select(RubricaEmpresa).where(RubricaEmpresa.id == achado.origem_id))).scalar_one_or_none()
        if rub and rub.dicionario_rubrica_id:
            dic = (await db.execute(select(DicionarioRubrica).where(DicionarioRubrica.id == rub.dicionario_rubrica_id))).scalar_one_or_none()
            if dic:
                fundamento = dic.fundamento

    # prescrição
    presc = calcular_regua(achado.valor_mensal) if achado.valor_mensal else {}

    dados = {
        "achado": {
            "descricao": achado.descricao, "grau_seguranca": achado.grau_seguranca,
            "esfera": achado.esfera, "tipo_valor": achado.tipo_valor, "tipo": achado.tipo,
            "valor_mensal": float(achado.valor_mensal) if achado.valor_mensal else None,
            "aliquota_aplicada": float(achado.aliquota_aplicada) if achado.aliquota_aplicada else None,
            "valor_retroativo": float(achado.valor_retroativo) if achado.valor_retroativo else None,
        },
        "empresa": {"razao_social": empresa.razao_social if empresa else "—"},
        "estabelecimento": {"nome": estab.nome, "codigo": estab.codigo},
        "memoria": memoria,
        "prescreve_90dias": presc.get("valor_prescreve_90dias"),
        "data_prescricao": achado.data_prescricao_proxima.strftime("%d/%m/%Y") if achado.data_prescricao_proxima else "—",
        "fundamento": fundamento,
    }

    pdf = gerar_dossie_prova(dados, incluir_fundamento=incluir_fund)
    filename = f"dossie-prova-{achado_id[:8]}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
