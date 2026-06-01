# ==============================================================
# SST ESOCIAL GOV — Router: Radar Previdenciário
# Arquivo: api/routers/radar.py
# ==============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date

from api.database import get_db, set_tenant
from api.models.agente_nocivo import AgenteNocivo
from api.models.trabalhador import Trabalhador
from api.models.documento import DocumentoTecnico
from api.models.afastamento import Afastamento
from api.models.usuario import Usuario
from api.models.empresa import Empresa
from api.auth import get_current_user

router = APIRouter()


def calcular_risco_financeiro(grau_risco: int, num_trabalhadores: int, salario_medio: float = 3500.0) -> dict:
    """
    Calcula exposição financeira previdenciária.
    RAT (Risco Acidente Trabalho): Grau 1=1%, 2=2%, 3=3%
    FAP multiplica entre 0.5 e 2.0 (usamos 1.0 como base)
    """
    rat = {1: 0.01, 2: 0.02, 3: 0.03}.get(grau_risco, 0.02)
    folha_mensal = num_trabalhadores * salario_medio
    custo_rat_mensal = folha_mensal * rat
    custo_rat_anual = custo_rat_mensal * 12

    # Estimativa de passivo previdenciário por exposição
    # Baseado em: probabilidade de aposentadoria especial × tempo restante × benefício
    passivo_estimado = num_trabalhadores * salario_medio * 12 * 0.15

    return {
        "rat_percentual": rat * 100,
        "folha_mensal": round(folha_mensal, 2),
        "custo_rat_mensal": round(custo_rat_mensal, 2),
        "custo_rat_anual": round(custo_rat_anual, 2),
        "passivo_estimado": round(passivo_estimado, 2),
        "dinheiro_em_risco": round(custo_rat_anual + passivo_estimado, 2),
    }


@router.get("/dashboard")
async def dashboard_radar(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id

    # Buscar empresa
    emp_result = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = emp_result.scalar_one_or_none()
    grau_risco = getattr(empresa, 'grau_risco', 2) if empresa else 2

    # Total trabalhadores
    total_trab = await db.execute(
        select(func.count()).where(Trabalhador.empresa_id == empresa_id)
    )
    num_trabalhadores = total_trab.scalar() or 0

    # Agentes nocivos ativos
    agentes_result = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == empresa_id)
    )
    agentes = agentes_result.scalars().all()
    num_agentes = len(agentes)

    # Trabalhadores em áreas com risco (expostos a agentes nocivos)
    # Baseado nos GES com agentes cadastrados
    setores_com_risco = set()
    for a in agentes:
        desc = a.descricao_agente or ""
        for ges in ["GES3001","GES3002","GES3003","GES3004","GES3005",
                    "GES3006","GES3007","GES3008","GES3015","GES3016"]:
            if ges in desc:
                setores_com_risco.add(ges)

    # Documentos com problema (vencidos ou sem validação)
    docs_result = await db.execute(
        select(DocumentoTecnico).where(DocumentoTecnico.empresa_id == empresa_id)
    )
    docs = docs_result.scalars().all()
    docs_problema = [d for d in docs if (
        d.status not in ["ativo"] or
        (d.data_validade and d.data_validade < date.today())
    )]

    # Documentos sem validação IA
    docs_sem_validacao = [d for d in docs if not d.metadata_doc or
                          not d.metadata_doc.get("texto_extraido")]

    # Afastamentos ativos
    afast_result = await db.execute(
        select(func.count()).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    afastamentos_ativos = afast_result.scalar() or 0

    # Custo afastamentos
    custo_result = await db.execute(
        select(func.sum(Afastamento.custo_total_estimado)).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    custo_afastamentos = float(custo_result.scalar() or 0)

    # Cálculo financeiro
    financeiro = calcular_risco_financeiro(grau_risco, num_trabalhadores)

    # Score de risco geral (0-100)
    score_risco = 0
    if num_agentes > 0: score_risco += 30
    if len(docs_problema) > 0: score_risco += 25
    if afastamentos_ativos > 0: score_risco += 20
    if len(docs_sem_validacao) > 0: score_risco += 15
    if grau_risco >= 3: score_risco += 10

    # Alertas principais
    alertas = []
    if len(docs_problema) > 0:
        alertas.append({
            "tipo": "critico",
            "icone": "📄",
            "mensagem": f"{len(docs_problema)} documento(s) com problema ou vencido(s)",
            "acao": "Ver documentos"
        })
    if afastamentos_ativos > 0:
        alertas.append({
            "tipo": "atencao",
            "icone": "🏥",
            "mensagem": f"{afastamentos_ativos} afastamento(s) ativo(s) — custo R$ {custo_afastamentos:,.2f}",
            "acao": "Ver afastamentos"
        })
    if num_agentes > 0:
        agentes_especiais = [a for a in agentes if "01.01.001" in (a.codigo_tabela24 or "")]
        if agentes_especiais:
            alertas.append({
                "tipo": "atencao",
                "icone": "🔊",
                "mensagem": f"{len(agentes_especiais)} setor(es) com ruído acima do limite — risco aposentadoria especial",
                "acao": "Ver agentes nocivos"
            })
    if grau_risco >= 3:
        alertas.append({
            "tipo": "info",
            "icone": "⚠️",
            "mensagem": f"Empresa Grau de Risco {grau_risco} — alíquota RAT {financeiro['rat_percentual']}%",
            "acao": "Ver detalhes"
        })

    return {
        "empresa_nome": empresa.razao_social if empresa else "",
        "grau_risco": grau_risco,
        "score_risco": score_risco,
        "kpis": {
            "funcionarios_em_risco": num_trabalhadores,
            "setores_sem_base_tecnica": len(docs_sem_validacao),
            "documentos_com_problema": len(docs_problema),
            "dinheiro_em_risco": financeiro["dinheiro_em_risco"],
            "afastamentos_ativos": afastamentos_ativos,
            "custo_afastamentos": custo_afastamentos,
        },
        "financeiro": financeiro,
        "agentes": [
            {
                "id": str(a.id),
                "codigo": a.codigo_tabela24,
                "descricao": a.descricao_agente,
                "nivel": a.nivel_exposicao,
                "epi_eficaz": a.epi_eficaz,
            }
            for a in agentes
        ],
        "alertas": alertas,
        "documentos_problema": [
            {
                "id": str(d.id),
                "tipo": d.tipo,
                "titulo": d.titulo,
                "status": d.status,
                "vencido": bool(d.data_validade and d.data_validade < date.today()),
            }
            for d in docs_problema
        ],
    }


@router.get("/setores")
async def setores_risco(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id

    agentes_result = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == empresa_id)
    )
    agentes = agentes_result.scalars().all()

    # Agrupar por setor (extrair GES da descrição)
    setores = {}
    for a in agentes:
        desc = a.descricao_agente or ""
        import re
        ges_match = re.search(r'GES\d+', desc)
        setor_key = ges_match.group() if ges_match else "Outros"

        if setor_key not in setores:
            setor_nome = desc.split("(")[1].replace(")", "").strip() if "(" in desc else setor_key
            setores[setor_key] = {
                "codigo": setor_key,
                "nome": setor_nome,
                "agentes": [],
                "nivel_risco": "baixo",
                "atividade_especial": False,
            }

        setores[setor_key]["agentes"].append({
            "codigo_tabela24": a.codigo_tabela24,
            "descricao": a.descricao_agente,
            "nivel": a.nivel_exposicao,
            "epi_eficaz": a.epi_eficaz,
        })

        # Calcular nível de risco
        if not a.epi_eficaz:
            setores[setor_key]["nivel_risco"] = "alto"
            setores[setor_key]["atividade_especial"] = True
        elif setores[setor_key]["nivel_risco"] != "alto":
            setores[setor_key]["nivel_risco"] = "medio"

    return list(setores.values())
