# ==============================================================
# RADAR PREVIDENCIÁRIO — Importação Universal com IA
# Arquivo: api/routers/importacao_universal.py
# ==============================================================
import io
import json
import uuid
import fitz
import pandas as pd
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic

from api.database import get_db, set_tenant
from api.auth import get_current_user
from api.models.usuario import Usuario
from api.config import settings

router = APIRouter()


def get_claude():
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def extrair_texto_pdf(conteudo: bytes, max_chars: int = 40000) -> str:
    doc = fitz.open(stream=conteudo, filetype="pdf")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
        if len(texto) > max_chars:
            break
    doc.close()
    return texto[:max_chars]


def extrair_texto_excel(conteudo: bytes, nome: str) -> str:
    if nome.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(conteudo), dtype=str, encoding="utf-8")
    else:
        df = pd.read_excel(io.BytesIO(conteudo), dtype=str)
    df = df.fillna("").head(20)
    return f"Colunas: {list(df.columns)}\n\nPrimeiras linhas:\n{df.to_string()}"


async def detectar_e_extrair(texto: str, nome_arquivo: str, tipo_mime: str) -> dict:
    """IA detecta o tipo do documento e extrai dados estruturados."""
    
    cliente = get_claude()
    
    prompt = f"""Você é especialista em SST, RH e previdenciário brasileiro.

Analise este documento e:
1. Identifique o tipo de documento
2. Extraia os dados relevantes em JSON estruturado

NOME DO ARQUIVO: {nome_arquivo}
TIPO: {tipo_mime}

CONTEÚDO:
{texto[:15000]}

Responda APENAS com JSON no formato:
{{
  "tipo_documento": "LTCAT|PPP|ATESTADO|TRABALHADORES|AFASTAMENTOS|CAT|PCMSO|OUTRO",
  "confianca": 0.0-1.0,
  "resumo": "breve descrição do que foi encontrado",
  "dados": {{
    // Para LTCAT:
    // "empresa", "cnpj", "data_emissao", "responsavel_tecnico": {{"nome", "registro", "conselho"}},
    // "agentes_nocivos": [{{"codigo_tabela24", "descricao", "setor", "nivel_exposicao", "unidade_medida", "epc_eficaz", "epi_eficaz", "epi_ca"}}]
    
    // Para TRABALHADORES:
    // "trabalhadores": [{{"nome", "cpf", "cargo", "setor", "data_admissao", "sexo", "matricula", "pis_pasep"}}]
    
    // Para PPP:
    // "trabalhador": {{"nome", "cpf"}}, "empresa", "periodos": [{{"cargo", "setor", "data_inicio", "data_fim", "agentes"}}]
    
    // Para ATESTADO:
    // "paciente": {{"nome", "cpf"}}, "medico": {{"nome", "crm"}}, "cid", "dias_afastamento", "data_emissao"
    
    // Para AFASTAMENTOS:
    // "afastamentos": [{{"nome", "cpf", "data_inicio", "data_fim", "cid", "motivo"}}]
    
    // Para CAT:
    // "acidentado": {{"nome", "cpf"}}, "data_acidente", "descricao", "cid", "parte_corpo"
  }}
}}

IMPORTANTE: Responda SOMENTE o JSON, sem explicações."""

    msg = cliente.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    texto_resp = msg.content[0].text.strip()
    if "```" in texto_resp:
        texto_resp = texto_resp.split("```")[1]
        if texto_resp.startswith("json"):
            texto_resp = texto_resp[4:]
    
    return json.loads(texto_resp.strip())


@router.post("/analisar")
async def analisar_universal(
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analisa qualquer documento e detecta o tipo automaticamente."""
    await set_tenant(db, current_user.empresa_id)

    nome = arquivo.filename.lower()
    conteudo = await arquivo.read()

    if len(conteudo) > 25 * 1024 * 1024:
        raise HTTPException(400, "Arquivo muito grande. Máximo 25MB")

    # Extrair texto conforme tipo
    try:
        if nome.endswith(".pdf"):
            texto = extrair_texto_pdf(conteudo)
            tipo_mime = "PDF"
        elif nome.endswith((".xlsx", ".xls", ".csv")):
            texto = extrair_texto_excel(conteudo, nome)
            tipo_mime = "PLANILHA"
        elif nome.endswith(".xml"):
            texto = conteudo.decode("utf-8", errors="ignore")[:20000]
            tipo_mime = "XML"
        else:
            raise HTTPException(400, "Formato não suportado. Use PDF, Excel, CSV ou XML")
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {str(e)}")

    if len(texto.strip()) < 50:
        raise HTTPException(400, "Arquivo vazio ou sem conteúdo extraível")

    # Disparar task Celery
    from api.tasks.importacao_task import processar_documento_universal
    task = processar_documento_universal.delay(
        conteudo.hex(),
        arquivo.filename,
        tipo_mime,
        str(current_user.empresa_id),
        texto[:15000],
    )

    return {
        "job_id": task.id,
        "status": "processando",
        "arquivo": arquivo.filename,
        "tipo_detectado_preview": tipo_mime,
        "mensagem": "Documento enviado para análise. A IA irá detectar o tipo e posicionar os dados automaticamente.",
    }


@router.get("/status/{job_id}")
async def status_universal(
    job_id: str,
    current_user: Usuario = Depends(get_current_user),
):
    from api.tasks.celery_app import app as celery_app
    from celery.result import AsyncResult
    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        return {"status": "processando", "mensagem": "IA analisando documento..."}
    elif result.state == "SUCCESS":
        return {"status": "concluido", **result.result}
    elif result.state == "FAILURE":
        return {"status": "erro", "erro": str(result.result)}
    else:
        return {"status": result.state.lower()}
