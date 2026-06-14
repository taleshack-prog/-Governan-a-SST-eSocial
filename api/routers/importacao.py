# ==============================================================
# RADAR PREVIDENCIÁRIO — Importação Inteligente Completa
# Arquivo: api/routers/importacao.py
# ==============================================================
import os
import io
import json
import uuid
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import httpx

from api.database import get_db, set_tenant
from api.auth import get_current_user
from api.models.usuario import Usuario
from api.models.trabalhador import Trabalhador
from api.models.vinculo import Vinculo
from api.config import settings

router = APIRouter()
_IMPORT_SESSIONS: dict = {}

CAMPOS_TRABALHADOR = {
    "nome":            "Nome completo do trabalhador",
    "cpf":             "CPF (11 dígitos)",
    "data_nascimento": "Data de nascimento",
    "sexo":            "Sexo (M/F)",
    "pis_pasep":       "PIS ou PASEP",
    "cargo":           "Cargo ou função",
    "setor":           "Setor ou departamento",
    "matricula":       "Matrícula interna",
    "data_admissao":   "Data de admissão",
    "ges":             "GES — Grupo de Exposição Similar",
    "salario":         "Salário base",
    "tipo_contrato":   "Tipo de contrato (CLT, PJ, etc)",
    "cbo":             "CBO — Classificação Brasileira de Ocupações",
    "email":           "E-mail do funcionário",
    "telefone":        "Telefone do funcionário",
    "turno":           "Turno de trabalho",
    "centro_custo":    "Centro de custo",
}

def limpar_cpf(cpf: Any) -> str:
    if not cpf: return ""
    return "".join(c for c in str(cpf) if c.isdigit())

def limpar_data(valor: Any) -> Optional[date]:
    if not valor or (isinstance(valor, float)): return None
    if isinstance(valor, (datetime, pd.Timestamp)): return valor.date()
    if isinstance(valor, date): return valor
    try: return pd.to_datetime(str(valor), dayfirst=True).date()
    except: return None

def limpar_sexo(valor: Any) -> Optional[str]:
    if not valor: return None
    v = str(valor).strip().upper()
    if v in ["M","MASCULINO","MASC","H","HOMEM","1"]: return "M"
    if v in ["F","FEMININO","FEM","MULHER","2"]: return "F"
    return None

def limpar_salario(valor: Any) -> Optional[float]:
    if not valor: return None
    try:
        s = str(valor).replace("R$","").replace(".","").replace(",",".").strip()
        return float(s)
    except: return None

async def mapear_colunas_ia(colunas: List[str]) -> Dict[str, str]:
    prompt = f"""Você é especialista em dados de RH brasileiro.

Mapeie as colunas da planilha para os campos do sistema.

COLUNAS DA PLANILHA:
{json.dumps(colunas, ensure_ascii=False)}

CAMPOS DO SISTEMA:
{json.dumps(CAMPOS_TRABALHADOR, ensure_ascii=False)}

Responda APENAS com JSON:
{{"coluna_planilha": "campo_sistema"}}

Use null se não corresponder. Cada campo mapeado apenas uma vez.
Responda SOMENTE o JSON."""

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"},
            json={"model": "anthropic/claude-haiku-4-5", "max_tokens": 800,
                  "messages": [{"role": "user", "content": prompt}]}
        )
        resp.raise_for_status()
        texto = resp.json()["choices"][0]["message"]["content"].strip()

    if "```" in texto:
        texto = texto.split("```")[1]
        if texto.startswith("json"): texto = texto[4:]
    return json.loads(texto.strip())


def processar_registro(row: Any, mapeamento: Dict, idx: int) -> Dict:
    registro = {}
    for col_orig, campo in mapeamento.items():
        if campo and campo != "null":
            val = str(row.get(col_orig, "") or "").strip()
            registro[campo] = val if val else None
    return registro


async def importar_registros(df, mapeamento, empresa_id, sobrescrever, db):
    importados = 0
    erros = []
    duplicados = 0
    CHUNK = 500

    for chunk_start in range(0, len(df), CHUNK):
        chunk = df.iloc[chunk_start:chunk_start + CHUNK]
        for idx, row in chunk.iterrows():
            try:
                reg = processar_registro(row, mapeamento, idx)
                nome_val = reg.get("nome")
                if not nome_val:
                    erros.append({"linha": idx + 2, "erro": "Nome obrigatório"})
                    continue

                cpf_val = limpar_cpf(reg.get("cpf", ""))
                data_admissao = limpar_data(reg.get("data_admissao"))

                # Verificar duplicado
                if cpf_val and not sobrescrever:
                    exist = await db.execute(
                        select(Trabalhador).where(
                            Trabalhador.empresa_id == empresa_id,
                            Trabalhador.cpf == cpf_val
                        )
                    )
                    if exist.scalar_one_or_none():
                        duplicados += 1
                        continue

                # Criar trabalhador
                trab_id = uuid.uuid4()
                trab = Trabalhador(
                    id=trab_id,
                    empresa_id=empresa_id,
                    nome=nome_val,
                    cpf=cpf_val or None,
                    cargo=reg.get("cargo"),
                    setor=reg.get("setor") or reg.get("centro_custo"),
                    matricula=reg.get("matricula"),
                    ges=reg.get("ges"),
                    data_admissao=data_admissao,
                    data_nascimento=limpar_data(reg.get("data_nascimento")),
                    sexo=limpar_sexo(reg.get("sexo")),
                    pis_pasep=reg.get("pis_pasep"),
                    salario_base=limpar_salario(reg.get("salario")),
                )
                db.add(trab)

                # Criar vínculo automaticamente se tiver data de admissão
                if data_admissao:
                    vinculo = Vinculo(
                        id=uuid.uuid4(),
                        trabalhador_id=trab_id,
                        empresa_id=empresa_id,
                        matricula=reg.get("matricula"),
                        cargo=reg.get("cargo"),
                        cbo=reg.get("cbo"),
                        data_admissao=data_admissao,
                        tipo_contrato=reg.get("tipo_contrato") or "CLT",
                        status="ativo",
                    )
                    db.add(vinculo)

                importados += 1
            except Exception as e:
                erros.append({"linha": idx + 2, "erro": str(e)})

        await db.commit()

    return importados, duplicados, erros


@router.post("/analisar")
async def analisar_arquivo(
    arquivo: UploadFile = File(...),
    campos_sensiveis: str = "",
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_tenant(db, current_user.empresa_id)
    nome = arquivo.filename.lower()
    if not any(nome.endswith(ext) for ext in [".xlsx", ".xls", ".csv"]):
        raise HTTPException(400, "Use .xlsx, .xls ou .csv")

    conteudo = await arquivo.read()
    try:
        df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", dtype=str) if nome.endswith(".csv") \
             else pd.read_excel(io.BytesIO(conteudo), dtype=str)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {str(e)}")

    df = df.dropna(how="all").fillna("")
    total_linhas = len(df)
    if total_linhas == 0: raise HTTPException(400, "Arquivo vazio")
    if total_linhas > 15000: raise HTTPException(400, "Máximo 15.000 linhas")

    colunas_originais = list(df.columns)
    mapeamento = await mapear_colunas_ia(colunas_originais)
    sensiveis = [s.strip() for s in campos_sensiveis.split(",") if s.strip()]

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
        "cria_vinculo": any(v == "data_admissao" for v in mapeamento.values()),
    }


@router.post("/confirmar-direto")
async def confirmar_direto(
    arquivo: UploadFile = File(...),
    mapeamento: str = Form("{}"),
    campos_sensiveis: str = Form("[]"),
    sobrescrever_existentes: str = Form("false"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await set_tenant(db, current_user.empresa_id)

    mapeamento_dict = json.loads(mapeamento) if mapeamento else {}
    sobrescrever = sobrescrever_existentes.lower() == "true"

    conteudo = await arquivo.read()
    nome = arquivo.filename.lower()
    try:
        df = pd.read_csv(io.BytesIO(conteudo), encoding="utf-8", dtype=str) if nome.endswith(".csv") \
             else pd.read_excel(io.BytesIO(conteudo), dtype=str)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {str(e)}")

    df = df.dropna(how="all").fillna("")
    importados, duplicados, erros = await importar_registros(
        df, mapeamento_dict, current_user.empresa_id, sobrescrever, db
    )

    cria_vinculo = any(v == "data_admissao" for v in mapeamento_dict.values())

    return {
        "importados": importados,
        "duplicados": duplicados,
        "erros": erros[:20],
        "total_erros": len(erros),
        "sucesso": importados > 0,
        "vinculos_criados": importados if cria_vinculo else 0,
        "mensagem": f"{importados} trabalhadores importados." +
                    (f" {importados} vínculos criados." if cria_vinculo else "") +
                    (f" {duplicados} duplicados ignorados." if duplicados else "") +
                    (f" {len(erros)} erros." if erros else ""),
    }
