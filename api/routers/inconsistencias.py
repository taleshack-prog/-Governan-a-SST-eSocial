# ==============================================================
# RADAR PREVIDENCIÁRIO — Sprint 2: Motor de Inconsistências
# Arquivo: api/routers/inconsistencias.py
# ==============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta

from api.database import get_db, set_tenant
from api.models.trabalhador import Trabalhador
from api.models.afastamento import Afastamento
from api.models.agente_nocivo import AgenteNocivo
from api.models.vinculo import Vinculo
from api.models.documento import DocumentoTecnico
from api.models.exame_medico import ExameMedico
from api.auth import get_current_user
from api.models.usuario import Usuario

router = APIRouter()


@router.get("/verificar")
async def verificar_inconsistencias(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id
    hoje = date.today()
    inconsistencias = []
    alertas_checklist = []

    # ── Buscar dados base ──────────────────────────────────────
    trab_r = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == empresa_id)
    )
    trabalhadores = trab_r.scalars().all()

    afas_r = await db.execute(
        select(Afastamento).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    afastamentos_ativos = afas_r.scalars().all()

    agentes_r = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == empresa_id)
    )
    agentes = agentes_r.scalars().all()

    vinculos_r = await db.execute(
        select(Vinculo).where(
            Vinculo.empresa_id == empresa_id,
            Vinculo.status == "ativo"
        )
    )
    vinculos = vinculos_r.scalars().all()

    docs_r = await db.execute(
        select(DocumentoTecnico).where(DocumentoTecnico.empresa_id == empresa_id)
    )
    documentos = docs_r.scalars().all()

    exames_r = await db.execute(
        select(ExameMedico).where(ExameMedico.empresa_id == empresa_id)
    )
    exames = exames_r.scalars().all()

    # ── INCONSISTÊNCIA 1: Trabalhador sem setor ────────────────
    for t in trabalhadores:
        if not t.setor:
            inconsistencias.append({
                "tipo": "trabalhador_sem_setor",
                "gravidade": "media",
                "titulo": f"{t.nome} sem setor definido",
                "detalhe": "Trabalhador não está vinculado a nenhum setor. Necessário para o eSocial.",
                "trabalhador": t.nome,
                "acao": "Editar trabalhador e definir setor",
                "icone": "👤",
            })

    # ── INCONSISTÊNCIA 2: Trabalhador sem vínculo ativo ────────
    trab_ids_com_vinculo = {v.trabalhador_id for v in vinculos}
    for t in trabalhadores:
        if t.id not in trab_ids_com_vinculo:
            inconsistencias.append({
                "tipo": "sem_vinculo",
                "gravidade": "alta",
                "titulo": f"{t.nome} sem vínculo empregatício ativo",
                "detalhe": "Trabalhador não possui vínculo ativo. PPP e eSocial S-2230 não podem ser gerados.",
                "trabalhador": t.nome,
                "acao": "Cadastrar vínculo empregatício",
                "icone": "📋",
            })

    # ── INCONSISTÊNCIA 3: Afastado sem agente nocivo ───────────
    trab_ids_com_agente = {a.trabalhador_id for a in agentes}
    for af in afastamentos_ativos:
        trab = next((t for t in trabalhadores if t.id == af.trabalhador_id), None)
        if trab and af.trabalhador_id not in trab_ids_com_agente:
            inconsistencias.append({
                "tipo": "afastado_sem_agente_nocivo",
                "gravidade": "alta",
                "titulo": f"{trab.nome} afastado sem agentes nocivos cadastrados",
                "detalhe": "Trabalhador afastado sem mapeamento de agentes nocivos. PPP incompleto e eSocial S-2240 pendente.",
                "trabalhador": trab.nome,
                "acao": "Cadastrar agentes nocivos S-2240",
                "icone": "⚗️",
            })

    # ── INCONSISTÊNCIA 4: Documento técnico vencido ────────────
    for doc in documentos:
        if doc.data_validade and doc.data_validade < hoje:
            dias_vencido = (hoje - doc.data_validade).days
            inconsistencias.append({
                "tipo": "documento_vencido",
                "gravidade": "alta" if dias_vencido > 90 else "media",
                "titulo": f"{doc.tipo.upper()} vencido há {dias_vencido} dias",
                "detalhe": f"Documento '{doc.titulo}' venceu em {doc.data_validade.strftime('%d/%m/%Y')}. Base técnica inválida para eSocial.",
                "trabalhador": None,
                "acao": "Renovar documento técnico",
                "icone": "📄",
            })
        elif doc.data_validade and (doc.data_validade - hoje).days <= 30:
            dias_restantes = (doc.data_validade - hoje).days
            inconsistencias.append({
                "tipo": "documento_vencendo",
                "gravidade": "media",
                "titulo": f"{doc.tipo.upper()} vence em {dias_restantes} dias",
                "detalhe": f"Documento '{doc.titulo}' vence em {doc.data_validade.strftime('%d/%m/%Y')}. Providencie renovação.",
                "trabalhador": None,
                "acao": "Agendar renovação do documento",
                "icone": "⚠️",
            })

    # ── INCONSISTÊNCIA 5: Exame médico vencido ─────────────────
    for ex in exames:
        if ex.data_exame:
            dias_desde = (hoje - ex.data_exame).days
            if dias_desde > 365:
                trab = next((t for t in trabalhadores if t.id == ex.trabalhador_id), None)
                nome = trab.nome if trab else "Trabalhador"
                inconsistencias.append({
                    "tipo": "exame_vencido",
                    "gravidade": "media",
                    "titulo": f"Exame de {nome} desatualizado ({dias_desde} dias)",
                    "detalhe": f"Último exame realizado em {ex.data_exame.strftime('%d/%m/%Y')}. Periodicidade anual recomendada.",
                    "trabalhador": nome,
                    "acao": "Agendar exame periódico",
                    "icone": "🏥",
                })

    # ── INCONSISTÊNCIA 6: Afastamento sem CID ──────────────────
    for af in afastamentos_ativos:
        if not af.cid:
            trab = next((t for t in trabalhadores if t.id == af.trabalhador_id), None)
            nome = trab.nome if trab else "Trabalhador"
            inconsistencias.append({
                "tipo": "afastamento_sem_cid",
                "gravidade": "media",
                "titulo": f"Afastamento de {nome} sem CID",
                "detalhe": "CID não informado. Necessário para eSocial S-2230 e análise previdenciária.",
                "trabalhador": nome,
                "acao": "Informar CID do afastamento",
                "icone": "🔴",
            })

    # ── CHECKLIST PRÉ-eSocial ──────────────────────────────────
    total_trab = len(trabalhadores)
    trab_sem_setor = sum(1 for t in trabalhadores if not t.setor)
    trab_sem_vinculo = sum(1 for t in trabalhadores if t.id not in trab_ids_com_vinculo)
    docs_validos = sum(1 for d in documentos if not d.data_validade or d.data_validade >= hoje)
    afas_sem_cid = sum(1 for a in afastamentos_ativos if not a.cid)

    checklist = [
        {
            "item": "Trabalhadores com setor definido",
            "ok": trab_sem_setor == 0,
            "total": total_trab,
            "pendente": trab_sem_setor,
            "icone": "👥",
        },
        {
            "item": "Vínculos empregatícios ativos",
            "ok": trab_sem_vinculo == 0,
            "total": total_trab,
            "pendente": trab_sem_vinculo,
            "icone": "📋",
        },
        {
            "item": "Documentos técnicos válidos",
            "ok": len(documentos) > 0 and docs_validos == len(documentos),
            "total": len(documentos),
            "pendente": len(documentos) - docs_validos,
            "icone": "📄",
        },
        {
            "item": "Agentes nocivos mapeados (S-2240)",
            "ok": len(agentes) > 0,
            "total": total_trab,
            "pendente": total_trab - len(trab_ids_com_agente),
            "icone": "⚗️",
        },
        {
            "item": "Afastamentos com CID informado",
            "ok": afas_sem_cid == 0,
            "total": len(afastamentos_ativos),
            "pendente": afas_sem_cid,
            "icone": "🏥",
        },
    ]

    pronto_para_esocial = all(c["ok"] for c in checklist)
    score_checklist = int(sum(1 for c in checklist if c["ok"]) / len(checklist) * 100)

    # Ordenar inconsistências por gravidade
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    inconsistencias.sort(key=lambda x: ordem.get(x["gravidade"], 2))

    return {
        "inconsistencias": inconsistencias,
        "total_inconsistencias": len(inconsistencias),
        "criticas": sum(1 for i in inconsistencias if i["gravidade"] == "alta"),
        "checklist": checklist,
        "pronto_para_esocial": pronto_para_esocial,
        "score_checklist": score_checklist,
    }
