# ==============================================================
# SST ESOCIAL GOV — Router: Atestados
# Arquivo: api/routers/atestados.py
# ==============================================================

import hashlib
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db, set_tenant
from api.models.afastamento import Atestado, Afastamento
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


def validar_checklist_atestmed(texto: str) -> dict:
    """
    Verifica os requisitos do Novo Atestmed (Portarias 13 e 14/2026).
    Retorna checklist com resultado de cada item.
    """
    import re
    texto_lower = texto.lower()

    checklist = {}

    # 1. Identificação do paciente
    checklist["tem_identificacao_paciente"] = any(
        p in texto_lower for p in ["paciente", "nome:", "sr.", "sra.", "cpf"]
    )

    # 2. Data de emissão
    checklist["tem_data_emissao"] = bool(
        re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', texto)
    )

    # 3. CID por extenso ou código
    checklist["tem_cid"] = bool(
        re.search(r'\b[A-Z]\d{2}\.?\d?\b', texto) or
        any(p in texto_lower for p in ["cid", "diagnóstico", "diagnostico", "patologia"])
    )

    # 4. Assinatura do profissional
    checklist["tem_assinatura"] = any(
        p in texto_lower for p in ["assinado", "assinatura", "crm", "cro", "médico", "medico", "dr.", "dra."]
    )

    # 5. CRM/CRO
    checklist["tem_crm"] = bool(
        re.search(r'crm\s*[\:\-]?\s*\d+', texto_lower) or
        re.search(r'cro\s*[\:\-]?\s*\d+', texto_lower)
    )

    # 6. Data de início do repouso
    checklist["tem_data_inicio_repouso"] = any(
        p in texto_lower for p in ["repouso", "afastamento", "início", "inicio", "data de início"]
    )

    # 7. Prazo em dias
    checklist["tem_prazo_dias"] = bool(
        re.search(r'\d+\s*dias?', texto_lower)
    )

    # 8. Legibilidade (texto extraído com conteúdo suficiente)
    checklist["legivel"] = len(texto.strip()) > 50

    # Score
    total = len(checklist)
    aprovados = sum(1 for v in checklist.values() if v)
    score = round(aprovados / total, 2)

    return {
        "items": checklist,
        "aprovados": aprovados,
        "total": total,
        "score": score,
        "status": "valido" if score >= 0.75 else "pendente_complemento" if score >= 0.5 else "invalido"
    }


async def validar_atestado_com_ia(texto: str, api_key: str) -> dict:
    """Usa OpenRouter para análise profunda do atestado."""
    import httpx, os, json, re

    if not api_key or api_key == "changeme":
        return {"alertas": ["Modo desenvolvimento — configure OPENROUTER_API_KEY"], "dados_extraidos": {}}

    prompt = f"""Você é um especialista em medicina do trabalho e direito previdenciário brasileiro.
Analise este atestado médico conforme as Portarias MPS/INSS nº 13 e 14 de 23/03/2026 (Novo Atestmed).

TEXTO DO ATESTADO:
{texto[:3000]}

Extraia os dados e avalie a conformidade. Retorne APENAS JSON:
{{
  "dados_extraidos": {{
    "paciente_nome": "...",
    "data_emissao": "DD/MM/AAAA ou null",
    "cid": "XXX.X ou null",
    "diagnostico": "...",
    "medico_nome": "...",
    "crm": "...",
    "data_inicio_repouso": "DD/MM/AAAA ou null",
    "prazo_dias": 0,
    "especialidade": "..."
  }},
  "conformidade_portaria_13_2026": {{
    "tem_identificacao_paciente": true/false,
    "tem_data_emissao": true/false,
    "tem_cid_ou_diagnostico": true/false,
    "tem_assinatura_valida": true/false,
    "tem_crm_cro": true/false,
    "tem_data_inicio_repouso": true/false,
    "tem_prazo_dias": true/false,
    "documento_legivel": true/false
  }},
  "alertas": ["lista de problemas encontrados"],
  "recomendacoes": ["lista de ações sugeridas"],
  "apto_atestmed": true/false,
  "score_conformidade": 0.0
}}"""

        import anthropic as _anth
        _cli = _anth.Anthropic(api_key=api_key)
        _msg = _cli.messages.create(model="claude-haiku-4-5", max_tokens=1500,
            messages=[{"role": "user", "content": prompt}])
        content = _msg.content[0].text
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
            content = data["choices"][0]["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        return {"alertas": [f"Erro IA: {str(e)[:200]}"], "dados_extraidos": {}}

    return {"alertas": ["Não foi possível analisar"], "dados_extraidos": {}}


@router.post("/{afastamento_id}/atestados/", status_code=status.HTTP_201_CREATED)
async def upload_atestado(
    afastamento_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)

    # Verificar afastamento
    result = await db.execute(
        select(Afastamento).where(
            Afastamento.id == afastamento_id,
            Afastamento.empresa_id == current_user.empresa_id,
        )
    )
    afastamento = result.scalar_one_or_none()
    if not afastamento:
        raise HTTPException(status_code=404, detail="Afastamento não encontrado")

    # Ler arquivo
    contents = await file.read()
    content_hash = hashlib.sha256(contents).hexdigest()

    # Extrair texto
    from api.services.pdf_extractor import extrair_texto
    texto = extrair_texto(contents, file.filename or "atestado.pdf")

    # Validação por regras (rápida)
    checklist_result = validar_checklist_atestmed(texto)

    # Validação por IA (profunda)
    import os
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    ia_result = await validar_atestado_com_ia(texto, api_key)

    # Score final
    score_final = ia_result.get("score_conformidade", checklist_result["score"])
    status_final = checklist_result["status"]
    if ia_result.get("apto_atestmed") is True:
        status_final = "valido"
    elif ia_result.get("apto_atestmed") is False:
        status_final = "invalido"

    # Criar registro
    atestado = Atestado(
        empresa_id=current_user.empresa_id,
        afastamento_id=afastamento_id,
        trabalhador_id=afastamento.trabalhador_id,
        status=status_final,
        checklist={
            "regras": checklist_result["items"],
            "ia": ia_result.get("conformidade_portaria_13_2026", {}),
            "dados_extraidos": ia_result.get("dados_extraidos", {}),
        },
        ai_score=score_final,
        ai_alertas=ia_result.get("alertas", []) + ia_result.get("recomendacoes", []),
        storage_path=f"atestados/{afastamento_id}/{file.filename}",
        content_hash=content_hash,
        reviewed_by=current_user.id,
        reviewed_at=datetime.now(timezone.utc),
    )

    # Preencher dados extraídos pela IA
    dados = ia_result.get("dados_extraidos", {})
    if dados.get("cid"):
        atestado.cid = dados["cid"]
        atestado.cid_descricao = dados.get("diagnostico", "")
    if dados.get("medico_nome"):
        atestado.medico_nome = dados["medico_nome"]
        atestado.medico_crm = dados.get("crm", "")
    if dados.get("prazo_dias"):
        atestado.dias_afastamento = dados["prazo_dias"]

    db.add(atestado)

    # Atualizar contador no afastamento
    afastamento.num_atestados = (afastamento.num_atestados or 0) + 1
    if dados.get("cid") and not afastamento.cid:
        afastamento.cid = dados["cid"]
        afastamento.cid_descricao = dados.get("diagnostico", "")

    await db.commit()
    await db.refresh(atestado)

    return {
        "id": str(atestado.id),
        "status": atestado.status,
        "score": float(atestado.ai_score or 0),
        "checklist": atestado.checklist,
        "alertas": atestado.ai_alertas,
        "dados_extraidos": dados,
        "apto_atestmed": ia_result.get("apto_atestmed"),
    }


@router.get("/{afastamento_id}/atestados/")
async def listar_atestados(
    afastamento_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Atestado).where(
            Atestado.afastamento_id == afastamento_id,
            Atestado.empresa_id == current_user.empresa_id,
        ).order_by(Atestado.created_at.desc())
    )
    atestados = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "status": a.status,
            "cid": a.cid,
            "cid_descricao": a.cid_descricao,
            "medico_nome": a.medico_nome,
            "medico_crm": a.medico_crm,
            "dias_afastamento": a.dias_afastamento,
            "ai_score": float(a.ai_score or 0),
            "ai_alertas": a.ai_alertas or [],
            "checklist": a.checklist or {},
            "created_at": str(a.created_at),
        }
        for a in atestados
    ]
