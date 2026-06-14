# ==============================================================
# RADAR PREVIDENCIÁRIO — Importação Inteligente com IA
# Arquivo: api/routers/importacao.py
# ==============================================================
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import pandas as pd
import io
import json
import os
import uuid
from datetime import datetime, date

from api.database import get_db, set_tenant
from api.auth import get_current_user
from api.models.usuario import Usuario
from api.models.trabalhador import Trabalhador
from api.config import settings

router = APIRouter()

# Sessões de importação em memória (TTL implícito por restart)
_IMPORT_SESSIONS: dict = {}

# Campos do sistema com descrições para a IA mapear
CAMPOS_TRABALHADOR = {
    "nome":            "Nome completo do trabalhador",
    "cpf":             "CPF (11 dígitos, pode ter pontos e traços)",
    "data_nascimento": "Data de nascimento",
    "sexo":            "Sexo (M/F ou Masculino/Feminino)",
    "pis_pasep":       "PIS ou PASEP (número do trabalhador na previdência)",
    "cargo":           "Cargo ou função do trabalhador",
    "setor":           "Setor, departamento ou área",
    "matricula":       "Matrícula interna da empresa",
    "data_admissao":   "Data de admissão ou contratação",
    "ges":             "GES — Grupo de Exposição Similar",
}

# Campos sensíveis = não expostos no app do funcionário, mas SEMPRE importados
CAMPOS_SENSIVEIS_PADRAO = []  # Empresa decide — por padrão importa tudo


def limpar_cpf(cpf: str) -> str:
    if not cpf:
        return ""
    return "".join(c for c in str(cpf) if c.isdigit())


def limpar_data(valor: Any) -> Optional[date]:
    if not valor or pd.isna(valor):
        return None
    if isinstance(valor, (datetime, pd.Timestamp)):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return pd.to_datetime(str(valor), dayfirst=True).date()
    except:
        return None


def limpar_sexo(valor: Any) -> Optional[str]:
    if not valor or pd.isna(valor):
        return None
    v = str(valor).strip().upper()
    if v in ["M", "MASCULINO", "MASC", "H", "HOMEM", "1"]:
        return "M"
    if v in ["F", "FEMININO", "FEM", "MULHER", "2"]:
        return "F"
    return None


async def mapear_colunas_ia(colunas: List[str]) -> Dict[str, str]:
    """Usa IA para mapear colunas da planilha para campos do sistema."""
    prompt = f"""Você é um especialista em dados de RH brasileiro.

Mapeie as colunas da planilha abaixo para os campos do sistema.

COLUNAS DA PLANILHA:
{json.dumps(colunas, ensure_ascii=False)}

CAMPOS DO SISTEMA:
{json.dumps(CAMPOS_TRABALHADOR, ensure_ascii=False)}

Responda APENAS com um JSON no formato:
{{"coluna_planilha": "campo_sistema", ...}}

Regras:
- Use null se a coluna não corresponder a nenhum campo
- Cada campo do sistema pode ser mapeado apenas uma vez
- Priorize correspondências exatas ou semânticas claras
- Ignore colunas irrelevantes (ex: observações internas, códigos desconhecidos)

Responda SOMENTE o JSON, sem explicações."""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "anthropic/claude-haiku-4-5",
                "max_tokens": 800,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        resp.raise_for_status()
        result = resp.json()
        texto = result["choices"][0]["message"]["content"].strip()

    # Limpar e parsear JSON
    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return json.loads(texto.strip())


@router.post("/analisar")
async def analisar_arquivo(
    arquivo: UploadFile = File(...),
    campos_sensiveis: str = ",".join(CAMPOS_SENSIVEIS_PADRAO),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 1: Lê o arquivo, mapeia colunas com IA e retorna preview sem salvar."""
    await set_tenant(db, current_user.empresa_id)

    # Validar tipo de arquivo
    nome = arquivo.filename.lower()
    if not any(nome.endswith(ext) for ext in [".xlsx", ".xls", ".csv"]):
        raise HTTPException(400, "Formato não suportado. Use .xlsx, .xls ou .csv")

    # Ler arquivo
    conteudo = await arquivo.read()
    try:
        if nome.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(conteudo), dtype=str)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {str(e)}")

    # Remover linhas completamente vazias
    df = df.dropna(how="all")
    df = df.fillna("")

    total_linhas = len(df)
    if total_linhas == 0:
        raise HTTPException(400, "Arquivo vazio ou sem dados válidos")
    if total_linhas > 15000:
        raise HTTPException(400, "Arquivo muito grande. Máximo 15.000 linhas por importação")

    # Mapear colunas com IA
    colunas_originais = list(df.columns)
    mapeamento = await mapear_colunas_ia(colunas_originais)

    # Campos sensíveis a mascarar
    sensiveis = [s.strip() for s in campos_sensiveis.split(",") if s.strip()]

    # Gerar preview das primeiras 5 linhas
    preview_linhas = []
    for _, row in df.head(5).iterrows():
        linha = {}
        for col_orig, campo in mapeamento.items():
            if campo and campo != "null":
                valor = str(row.get(col_orig, "")).strip()
                if campo in sensiveis and valor:
                    valor = "*** (campo sensível)"
                linha[campo] = valor
        preview_linhas.append(linha)

    # Contar campos mapeados
    campos_mapeados = {k: v for k, v in mapeamento.items() if v and v != "null"}
    campos_nao_mapeados = [c for c in colunas_originais if c not in campos_mapeados]

    session_id = str(uuid.uuid4())
    _IMPORT_SESSIONS[session_id] = {"conteudo": conteudo, "nome": arquivo.filename}

    return {
        "total_linhas": total_linhas,
        "colunas_originais": colunas_originais,
        "mapeamento": mapeamento,
        "campos_mapeados": campos_mapeados,
        "campos_nao_mapeados": campos_nao_mapeados,
        "campos_sensiveis": sensiveis,
        "preview": preview_linhas,
        "session_id": session_id,
    }


class ConfirmarImportacao(BaseModel):
    session_id: str
    mapeamento: Dict[str, str]
    campos_sensiveis: List[str] = CAMPOS_SENSIVEIS_PADRAO
    sobrescrever_existentes: bool = False


@router.post("/confirmar")
async def confirmar_importacao(
    data: ConfirmarImportacao,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Etapa 2: Confirma e importa os dados para o banco."""
    await set_tenant(db, current_user.empresa_id)

    # Recuperar arquivo da sessão em memória
    cached_data = _IMPORT_SESSIONS.get(data.session_id)
    if not cached_data:
        raise HTTPException(400, "Sessão expirada. Faça o upload novamente.")
    conteudo = cached_data["conteudo"]
    nome = cached_data["nome"].lower()
    try:
        if nome.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(conteudo), dtype=str)
    except Exception as e:
        raise HTTPException(400, f"Erro ao reler arquivo: {str(e)}")

    df = df.dropna(how="all").fillna("")

    # Processar em chunks de 500
    CHUNK = 500
    importados = 0
    erros = []
    duplicados = 0

    for chunk_start in range(0, len(df), CHUNK):
        chunk = df.iloc[chunk_start:chunk_start + CHUNK]

        for idx, row in chunk.iterrows():
            try:
                # Montar dict com mapeamento
                registro = {}
                for col_orig, campo in data.mapeamento.items():
                    if campo and campo != "null" and campo not in data.campos_sensiveis:
                        registro[campo] = str(row.get(col_orig, "")).strip() or None

                # Campos obrigatórios
                nome_val = registro.get("nome")
                if not nome_val:
                    erros.append({"linha": idx + 2, "erro": "Nome obrigatório"})
                    continue

                # Verificar duplicado por CPF
                cpf_val = limpar_cpf(registro.get("cpf", ""))
                if cpf_val and not data.sobrescrever_existentes:
                    exist = await db.execute(
                        select(Trabalhador).where(
                            Trabalhador.empresa_id == current_user.empresa_id,
                            Trabalhador.cpf == cpf_val
                        )
                    )
                    if exist.scalar_one_or_none():
                        duplicados += 1
                        continue

                # Criar trabalhador
                trab = Trabalhador(
                    id=uuid.uuid4(),
                    empresa_id=current_user.empresa_id,
                    nome=nome_val,
                    cpf=cpf_val or None,
                    cargo=registro.get("cargo"),
                    setor=registro.get("setor"),
                    matricula=registro.get("matricula"),
                    ges=registro.get("ges"),
                    data_admissao=limpar_data(registro.get("data_admissao")),
                    data_nascimento=limpar_data(registro.get("data_nascimento")),
                    sexo=limpar_sexo(registro.get("sexo")),
                    pis_pasep=registro.get("pis_pasep"),
                )
                db.add(trab)
                importados += 1

            except Exception as e:
                erros.append({"linha": idx + 2, "erro": str(e)})

        await db.commit()

    return {
        "importados": importados,
        "duplicados": duplicados,
        "erros": erros[:20],  # Limitar erros exibidos
        "total_erros": len(erros),
        "sucesso": importados > 0,
        "mensagem": f"{importados} trabalhadores importados com sucesso." +
                    (f" {duplicados} duplicados ignorados." if duplicados else "") +
                    (f" {len(erros)} erros." if erros else ""),
    }
