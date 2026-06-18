# ==============================================================
# SST ESOCIAL GOV — Router: PPP Digital
# Arquivo: api/routers/ppp.py
# ==============================================================

from uuid import UUID
from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from api.database import get_db, set_tenant
from api.models.trabalhador import Trabalhador
from api.models.empresa import Empresa
from api.models.agente_nocivo import AgenteNocivo
from api.models.documento import DocumentoTecnico
from api.models.usuario import Usuario
from api.auth import get_current_user
from fastapi.responses import Response

router = APIRouter()


def calcular_completude(ppp: dict) -> dict:
    """Verifica completude do PPP conforme IN INSS 128/2022 art. 276."""
    campos_obrigatorios = {
        "empresa_cnpj":          ("Dados da empresa — CNPJ",          bool(ppp.get("empresa", {}).get("cnpj"))),
        "empresa_razao":         ("Dados da empresa — Razão Social",   bool(ppp.get("empresa", {}).get("razao_social"))),
        "empresa_cnae":          ("Dados da empresa — CNAE",           bool(ppp.get("empresa", {}).get("cnae"))),
        "empresa_grau_risco":    ("Dados da empresa — Grau de Risco",  bool(ppp.get("empresa", {}).get("grau_risco"))),
        "trab_nome":             ("Trabalhador — Nome",                bool(ppp.get("trabalhador", {}).get("nome"))),
        "trab_cpf":              ("Trabalhador — CPF",                 bool(ppp.get("trabalhador", {}).get("cpf"))),
        "trab_cargo":            ("Trabalhador — Cargo",               bool(ppp.get("trabalhador", {}).get("cargo"))),
        "trab_setor":            ("Trabalhador — Setor/GES",           bool(ppp.get("trabalhador", {}).get("setor"))),
        "trab_data_admissao":    ("Trabalhador — Data Admissão",       bool(ppp.get("trabalhador", {}).get("data_admissao"))),
        "agentes_nocivos":       ("Agentes Nocivos — mínimo 1",        len(ppp.get("agentes_nocivos", [])) > 0),
        "ltcat_referencia":      ("LTCAT — Documento de referência",   bool(ppp.get("ltcat", {}).get("titulo"))),
        "resp_tecnico_nome":     ("Responsável Técnico — Nome",        bool(ppp.get("responsavel_tecnico", {}).get("nome"))),
        "resp_tecnico_registro": ("Responsável Técnico — Registro",    bool(ppp.get("responsavel_tecnico", {}).get("registro"))),
    }

    pendencias = []
    aprovados = 0
    for key, (descricao, ok) in campos_obrigatorios.items():
        if ok:
            aprovados += 1
        else:
            pendencias.append(descricao)

    total = len(campos_obrigatorios)
    percentual = round((aprovados / total) * 100)

    return {
        "percentual": percentual,
        "aprovados": aprovados,
        "total": total,
        "pendencias": pendencias,
        "status": "completo" if percentual == 100 else "incompleto" if percentual >= 70 else "critico",
    }


@router.get("/")
async def listar_ppps(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista PPP de todos os trabalhadores da empresa."""
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id

    # Buscar empresa
    emp = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = emp.scalar_one_or_none()

    # Buscar trabalhadores
    trab_result = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == empresa_id)
    )
    trabalhadores = trab_result.scalars().all()

    # Buscar agentes nocivos
    ag_result = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == empresa_id)
    )
    agentes = ag_result.scalars().all()

    # Buscar LTCAT
    doc_result = await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.empresa_id == empresa_id,
            DocumentoTecnico.tipo == "LTCAT",
            DocumentoTecnico.status == "ativo",
        )
    )
    ltcat = doc_result.scalar_one_or_none()

    ppps = []
    for t in trabalhadores:
        ppp = montar_ppp(t, empresa, agentes, ltcat)
        completude = calcular_completude(ppp)
        ppps.append({
            "trabalhador_id": str(t.id),
            "trabalhador_nome": t.nome,
            "trabalhador_cpf": t.cpf,
            "cargo": t.cargo,
            "setor": t.setor,
            "completude": completude,
        })

    return ppps


@router.get("/{trabalhador_id}")
async def obter_ppp(
    trabalhador_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Gera o PPP completo de um trabalhador."""
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id

    # Buscar trabalhador
    trab_result = await db.execute(
        select(Trabalhador).where(
            Trabalhador.id == trabalhador_id,
            Trabalhador.empresa_id == empresa_id,
        )
    )
    trabalhador = trab_result.scalar_one_or_none()
    if not trabalhador:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")

    # Buscar empresa
    emp = await db.execute(select(Empresa).where(Empresa.id == empresa_id))
    empresa = emp.scalar_one_or_none()

    # Buscar agentes nocivos
    ag_result = await db.execute(
        select(AgenteNocivo).where(AgenteNocivo.empresa_id == empresa_id)
    )
    agentes = ag_result.scalars().all()

    # Buscar LTCAT
    doc_result = await db.execute(
        select(DocumentoTecnico).where(
            DocumentoTecnico.empresa_id == empresa_id,
            DocumentoTecnico.tipo == "LTCAT",
            DocumentoTecnico.status == "ativo",
        )
    )
    ltcat = doc_result.scalar_one_or_none()

    ppp = montar_ppp(trabalhador, empresa, agentes, ltcat)
    ppp["completude"] = calcular_completude(ppp)

    return ppp


def montar_ppp(trabalhador, empresa, agentes, ltcat) -> dict:
    """Monta a estrutura do PPP conforme modelo INSS."""
    return {
        "gerado_em": str(datetime.utcnow()),
        "versao": "2.0",
        "base_legal": "Lei 8.213/1991 art. 58 | Decreto 3.048/1999 art. 68 | IN INSS 128/2022",

        "empresa": {
            "razao_social": empresa.razao_social if empresa else "",
            "cnpj": empresa.cnpj if empresa else "",
            "cnae": empresa.cnae_principal if empresa else "",
            "grau_risco": empresa.grau_risco if empresa else "",
            "endereco": getattr(empresa, "endereco", ""),
            "responsavel_nome": getattr(empresa, "responsavel_nome", ""),
        },

        "trabalhador": {
            "nome": trabalhador.nome,
            "cpf": trabalhador.cpf,
            "cargo": getattr(trabalhador, "cargo", "") or "",
            "setor": getattr(trabalhador, "setor", "") or "",
            "matricula": getattr(trabalhador, "matricula", "") or "",
            "data_admissao": str(getattr(trabalhador, "data_admissao", "")) or "",
            "data_nascimento": str(getattr(trabalhador, "data_nascimento", "")) or "",
            "sexo": getattr(trabalhador, "sexo", "") or "",
        },

        "agentes_nocivos": [
            {
                "codigo_tabela24": a.codigo_tabela24,
                "descricao": a.descricao_agente,
                "nivel_exposicao": a.nivel_exposicao,
                "unidade": a.unidade_medida,
                "tecnica_avaliacao": "NHO 01" if "01.01" in (a.codigo_tabela24 or "") else "Qualitativa",
                "epi_eficaz": a.epi_eficaz,
                "data_inicio": str(a.data_inicio) if a.data_inicio else "",
                "enquadramento_especial": not a.epi_eficaz,
            }
            for a in agentes
        ],

        "ltcat": {
            "titulo": ltcat.titulo if ltcat else "",
            "data_emissao": str(ltcat.data_emissao) if ltcat else "",
            "responsavel": ltcat.responsavel_tecnico_nome if ltcat else "",
            "registro": ltcat.responsavel_tecnico_registro if ltcat else "",
        } if ltcat else {},

        "responsavel_tecnico": {
            "nome": ltcat.responsavel_tecnico_nome if ltcat else "",
            "registro": ltcat.responsavel_tecnico_registro if ltcat else "",
            "conselho": ltcat.responsavel_tecnico_conselho if ltcat else "",
            "funcao": "Engenheiro de Segurança do Trabalho",
        } if ltcat else {},

        "periodos_laborais": [
            {
                "data_inicio": str(getattr(trabalhador, "data_admissao", "")) or str(date.today()),
                "data_fim": "",
                "cargo": getattr(trabalhador, "cargo", "") or "",
                "setor": getattr(trabalhador, "setor", "") or "",
                "atividade_especial": any(not a.epi_eficaz for a in agentes),
                "codigo_enquadramento": "01" if any("01.01" in (a.codigo_tabela24 or "") for a in agentes) else "00",
            }
        ],

        "observacoes": "PPP gerado automaticamente pelo sistema SST eSocial Gov com base nos dados cadastrados.",
    }


@router.get("/{trabalhador_id}/validar")
async def validar_ppp_com_ia(
    trabalhador_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Valida o PPP usando IA e retorna recomendações."""
    import os, httpx, json, re

    await set_tenant(db, current_user.empresa_id)

    # Buscar PPP
    ppp_data = await obter_ppp(trabalhador_id, db, current_user)
    completude = ppp_data.get("completude", {})

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or api_key == "changeme":
        return {
            "status": "mock",
            "alertas": ["Configure OPENROUTER_API_KEY para validação IA real"],
            "recomendacoes": [],
            "score": completude.get("percentual", 0),
        }

    prompt = f"""Você é especialista em PPP (Perfil Profissiográfico Previdenciário) conforme IN INSS 128/2022.

Analise este PPP e identifique problemas e recomendações:

DADOS DO PPP:
- Trabalhador: {ppp_data['trabalhador']['nome']}
- Cargo: {ppp_data['trabalhador']['cargo']}
- Empresa: {ppp_data['empresa']['razao_social']} — CNAE {ppp_data['empresa']['cnae']} — GR {ppp_data['empresa']['grau_risco']}
- Agentes nocivos: {len(ppp_data['agentes_nocivos'])} cadastrados
- LTCAT: {'Presente' if ppp_data.get('ltcat') else 'AUSENTE'}
- Completude: {completude.get('percentual', 0)}%
- Pendências: {completude.get('pendencias', [])}

Retorne APENAS JSON:
{{
  "alertas": ["lista de problemas críticos"],
  "recomendacoes": ["lista de ações recomendadas"],
  "score_conformidade": 0.0,
  "apto_esocial": true/false,
  "campos_faltantes": ["lista de campos obrigatórios ausentes"]
}}"""

    try:
        import anthropic as _anth
        _cli = _anth.Anthropic(api_key=api_key)
        _msg = _cli.messages.create(model="claude-haiku-4-5", max_tokens=1000,
            messages=[{"role": "user", "content": prompt}])
        content = _msg.content[0].text
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["completude"] = completude
            return result
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["completude"] = completude
                return result
    except Exception as e:
        pass

    return {
        "alertas": ["Erro na validação IA"],
        "recomendacoes": [],
        "score_conformidade": completude.get("percentual", 0) / 100,
        "completude": completude,
    }


@router.get("/{trabalhador_id}/pdf")
async def exportar_ppp_pdf(
    trabalhador_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Exporta o PPP em PDF conforme modelo INSS."""
    from api.services.ppp_pdf import gerar_ppp_pdf

    ppp = await obter_ppp(trabalhador_id, db, current_user)
    pdf_bytes = gerar_ppp_pdf(ppp)

    nome = ppp.get("trabalhador", {}).get("nome", "trabalhador").replace(" ", "_")
    filename = f"PPP_{nome}_{date.today().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
