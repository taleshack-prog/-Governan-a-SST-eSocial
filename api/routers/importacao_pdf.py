# ==============================================================
# RADAR PREVIDENCIÁRIO — Importação de LTCAT via PDF com IA
# Arquivo: api/routers/importacao_pdf.py
# ==============================================================
import io
import json
import uuid
import fitz  # PyMuPDF
import httpx
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db, set_tenant
from api.auth import get_current_user
from api.models.usuario import Usuario
from api.models.documento import DocumentoTecnico
from api.models.agente_nocivo import AgenteNocivo
from api.models.trabalhador import Trabalhador
from api.config import settings

router = APIRouter()


def extrair_texto_pdf(conteudo: bytes) -> str:
    """Extrai texto de PDF usando PyMuPDF."""
    doc = fitz.open(stream=conteudo, filetype="pdf")
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    doc.close()
    return texto[:30000]

def extrair_chunks_pdf(conteudo: bytes) -> list:
    """Extrai texto do PDF em chunks de páginas para processar LTCATs longos."""
    doc = fitz.open(stream=conteudo, filetype="pdf")
    chunks = []
    chunk_atual = ""
    for i, pagina in enumerate(doc):
        texto_pag = pagina.get_text()
        if len(chunk_atual) + len(texto_pag) > 12000:
            if chunk_atual:
                chunks.append(chunk_atual)
            chunk_atual = texto_pag
        else:
            chunk_atual += texto_pag
    if chunk_atual:
        chunks.append(chunk_atual)
    doc.close()
    return chunks


async def analisar_ltcat_ia_chunk(texto: str) -> dict:
    """Usa IA para extrair dados estruturados do LTCAT."""
    prompt = f"""Você é especialista em SST e eSocial brasileiro.

Analise este texto de LTCAT (Laudo Técnico das Condições Ambientais do Trabalho) e extraia as informações em JSON.

TEXTO DO LTCAT:
{texto}

Extraia APENAS o que estiver explicitamente no texto. Responda com JSON no formato:

{{
  "titulo": "título do documento",
  "empresa": "nome da empresa",
  "cnpj": "CNPJ da empresa",
  "data_emissao": "YYYY-MM-DD ou null",
  "data_validade": "YYYY-MM-DD ou null",
  "responsavel_tecnico": {{
    "nome": "nome do responsável",
    "registro": "número CRQ/CRC/CREA/etc",
    "conselho": "CRQ/CREA/CRM/etc"
  }},
  "setores": ["lista de setores/GES identificados"],
  "agentes_nocivos": [
    {{
      "codigo_tabela24": "código do eSocial tabela 24",
      "descricao": "descrição do agente nocivo",
      "setor": "setor onde ocorre",
      "nivel_exposicao": "nível de exposição se informado",
      "unidade_medida": "unidade de medida se informada",
      "epc_eficaz": true/false/null,
      "epi_eficaz": true/false/null,
      "epi_ca": "número CA se informado"
    }}
  ],
  "observacoes": "observações gerais relevantes"
}}

IMPORTANTE:
- Para codigo_tabela24, use os códigos da Tabela 24 do eSocial (ex: 01.01.001 para ruído)
- Se não encontrar o código exato, coloque o mais próximo ou null
- Não invente dados que não estejam no texto
- Responda SOMENTE o JSON"""

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        resp.raise_for_status()
        texto_resp = resp.json()["choices"][0]["message"]["content"].strip()

    if "```" in texto_resp:
        texto_resp = texto_resp.split("```")[1]
        if texto_resp.startswith("json"):
            texto_resp = texto_resp[4:]

    return json.loads(texto_resp.strip())


def parse_data(valor: str) -> Optional[date]:
    if not valor: return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except:
        return None




async def analisar_ltcat_ia(texto: str) -> dict:
    """Analisa LTCAT — usa chunk único."""
    return await analisar_ltcat_ia_chunk(texto)


async def analisar_ltcat_ia_completo(conteudo: bytes) -> dict:
    """Analisa LTCAT longo processando em múltiplos chunks e agregando agentes."""
    chunks = extrair_chunks_pdf(conteudo)
    
    # Primeiro chunk — extrair metadados gerais
    dados_base = await analisar_ltcat_ia_chunk(chunks[0] if chunks else "")
    todos_agentes = list(dados_base.get("agentes_nocivos", []))
    todos_setores = list(dados_base.get("setores", []))
    
    # Chunks seguintes — extrair apenas agentes nocivos
    for chunk in chunks[1:]:
        if not any(kw in chunk.lower() for kw in ["agente", "ges", "nocivo", "ruído", "calor", "vibração", "químico"]):
            continue
        try:
            dados_chunk = await analisar_ltcat_ia_chunk(chunk)
            agentes_chunk = dados_chunk.get("agentes_nocivos", [])
            setores_chunk = dados_chunk.get("setores", [])
            todos_agentes.extend(agentes_chunk)
            todos_setores.extend(setores_chunk)
        except:
            continue
    
    # Remover duplicatas por descrição
    vistos = set()
    agentes_unicos = []
    for ag in todos_agentes:
        key = ag.get("descricao", "")[:50].lower()
        if key not in vistos:
            vistos.add(key)
            agentes_unicos.append(ag)
    
    dados_base["agentes_nocivos"] = agentes_unicos
    dados_base["setores"] = list(set(todos_setores))
    return dados_base

@router.post("/ltcat/analisar")
async def analisar_ltcat(
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 1: Lê o PDF do LTCAT e extrai dados com IA."""
    await set_tenant(db, current_user.empresa_id)

    nome = arquivo.filename.lower()
    if not nome.endswith(".pdf"):
        raise HTTPException(400, "Apenas arquivos PDF são aceitos")

    conteudo = await arquivo.read()
    if len(conteudo) > 20 * 1024 * 1024:
        raise HTTPException(400, "Arquivo muito grande. Máximo 20MB")

    # Extrair texto do PDF
    try:
        texto = extrair_texto_pdf(conteudo)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler PDF: {str(e)}")

    if len(texto.strip()) < 100:
        raise HTTPException(400, "PDF sem texto extraível. Pode ser digitalizado — use OCR antes.")

    # Analisar com IA
    try:
        dados = await analisar_ltcat_ia_completo(conteudo)
    except Exception as e:
        raise HTTPException(500, f"Erro na análise IA: {str(e)}")

    # Buscar trabalhadores para cruzamento
    trab_r = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == current_user.empresa_id)
    )
    trabalhadores = trab_r.scalars().all()
    setores_empresa = list({t.setor for t in trabalhadores if t.setor})

    # Contar agentes encontrados
    agentes = dados.get("agentes_nocivos", [])

    return {
        "dados_extraidos": dados,
        "total_agentes": len(agentes),
        "setores_encontrados": dados.get("setores", []),
        "setores_empresa": setores_empresa,
        "texto_extraido_chars": len(texto),
        "arquivo_nome": arquivo.filename,
        "preview_agentes": agentes[:5],
    }


@router.post("/ltcat/confirmar")
async def confirmar_ltcat(
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 2: Confirma e salva LTCAT + agentes nocivos no banco."""
    await set_tenant(db, current_user.empresa_id)

    conteudo = await arquivo.read()
    texto = extrair_texto_pdf(conteudo)
    dados = await analisar_ltcat_ia_completo(conteudo)

    # Criar documento técnico
    # Reler texto para salvar no documento
    doc_texto = extrair_texto_pdf(conteudo)

    doc = DocumentoTecnico(
        id=uuid.uuid4(),
        empresa_id=current_user.empresa_id,
        tipo="LTCAT",
        titulo=dados.get("titulo") or f"LTCAT — {dados.get('empresa', 'Empresa')}",
        descricao=doc_texto,  # Salvar texto completo para validação IA
        data_emissao=parse_data(dados.get("data_emissao")) or date.today(),
        data_validade=parse_data(dados.get("data_validade")),
        responsavel_tecnico_nome=dados.get("responsavel_tecnico", {}).get("nome"),
        responsavel_tecnico_registro=dados.get("responsavel_tecnico", {}).get("registro"),
        responsavel_tecnico_conselho=dados.get("responsavel_tecnico", {}).get("conselho"),
        status="ativo",
        metadata_doc={"cnpj": dados.get("cnpj"), "setores": dados.get("setores", [])},
    )
    db.add(doc)
    await db.flush()

    # Buscar trabalhadores por setor para vincular agentes
    trab_r = await db.execute(
        select(Trabalhador).where(Trabalhador.empresa_id == current_user.empresa_id)
    )
    trabalhadores = trab_r.scalars().all()
    setor_para_trab = {}
    for t in trabalhadores:
        if t.setor:
            setor_key = t.setor.lower()
            if setor_key not in setor_para_trab:
                setor_para_trab[setor_key] = []
            setor_para_trab[setor_key].append(t.id)

    # Criar agentes nocivos
    agentes_criados = 0
    agentes_data = dados.get("agentes_nocivos", [])

    for agente in agentes_data:
        codigo = agente.get("codigo_tabela24") or "00.00.000"
        descricao = agente.get("descricao", "Agente não identificado")
        setor_agente = agente.get("setor", "")

        # Encontrar trabalhadores do setor
        trabs_setor = []
        for setor_key, trabs in setor_para_trab.items():
            if setor_agente.lower() in setor_key or setor_key in setor_agente.lower():
                trabs_setor.extend(trabs)

        if trabs_setor:
            # Criar agente para cada trabalhador do setor
            for trab_id in trabs_setor:
                ag = AgenteNocivo(
                    id=uuid.uuid4(),
                    empresa_id=current_user.empresa_id,
                    trabalhador_id=trab_id,
                    documento_origem_id=doc.id,
                    codigo_tabela24=codigo,
                    descricao_agente=descricao,
                    nivel_exposicao=agente.get("nivel_exposicao"),
                    unidade_medida=agente.get("unidade_medida"),
                    epc_eficaz=agente.get("epc_eficaz"),
                    epi_eficaz=agente.get("epi_eficaz"),
                    epi_ca=agente.get("epi_ca"),
                    data_inicio=parse_data(dados.get("data_emissao")) or date.today(),
                    created_by_ai=True,
                    confidence_score=0.85,
                    needs_review=True,
                    trecho_original=descricao,
                )
                db.add(ag)
                agentes_criados += 1
        else:
            # Criar agente sem vínculo de trabalhador (setor não mapeado)
            ag = AgenteNocivo(
                id=uuid.uuid4(),
                empresa_id=current_user.empresa_id,
                trabalhador_id=None,
                documento_origem_id=doc.id,
                codigo_tabela24=codigo,
                descricao_agente=descricao,
                nivel_exposicao=agente.get("nivel_exposicao"),
                unidade_medida=agente.get("unidade_medida"),
                epc_eficaz=agente.get("epc_eficaz"),
                epi_eficaz=agente.get("epi_eficaz"),
                epi_ca=agente.get("epi_ca"),
                data_inicio=parse_data(dados.get("data_emissao")) or date.today(),
                created_by_ai=True,
                confidence_score=0.7,
                needs_review=True,
                trecho_original=f"Setor: {setor_agente} — {descricao}",
            )
            db.add(ag)
            agentes_criados += 1

    await db.commit()

    return {
        "sucesso": True,
        "documento_id": str(doc.id),
        "documento_titulo": doc.titulo,
        "agentes_criados": agentes_criados,
        "setores_processados": list(setor_para_trab.keys()),
        "mensagem": f"LTCAT importado. {agentes_criados} agentes nocivos criados e vinculados.",
        "requer_revisao": True,
        "aviso": "Agentes criados por IA — recomendamos revisão técnica antes do envio ao eSocial.",
    }
