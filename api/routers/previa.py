# ==============================================================
# RADAR PREVIDENCIÁRIO — PrevIA: Assistente Contextual
# Arquivo: api/routers/previa.py
# ==============================================================
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
import httpx
from datetime import date

from api.database import get_db, set_tenant
from api.auth import get_current_user
from api.models.usuario import Usuario
from api.models.afastamento import Afastamento
from api.models.trabalhador import Trabalhador
# base_normativa não tem modelo — usando texto fixo
from api.config import settings

router = APIRouter()

TELAS = {
    "dashboard":        "Dashboard principal com KPIs e alertas",
    "afastamentos":     "Gestão de afastamentos — lista, status, atestados e chat",
    "trabalhadores":    "Cadastro de trabalhadores da empresa",
    "documentos":       "Documentos técnicos — LTCAT, PCMSO, PGR",
    "agentes":          "Agentes nocivos S-2240 por trabalhador",
    "radar":            "Radar Previdenciário — score de risco por trabalhador",
    "ppp":              "PPP Digital — Perfil Profissiográfico Previdenciário",
    "radar-financeiro": "Radar Financeiro — perdas evitáveis, recomendações e score",
    "inconsistencias":  "Motor de Inconsistências e Checklist pré-eSocial",
    "tendencias":       "Tendências de custo, ranking de casos e impacto setorial",
    "painel-financeiro":"Painel Financeiro — custos do mês",
    "painel-gestor":    "Painel do Gestor — visão da equipe e retornos",
    "afastamentos-rh":  "Afastamentos RH — fila de atendimento",
    "cat":              "CAT — Comunicação de Acidente de Trabalho",
    "exames":           "Exames médicos periódicos",
    "auditoria":        "Log de auditoria SHA-256",
}

SYSTEM_PROMPT = """Você é a PrevIA, assistente inteligente do Radar Previdenciário.

Sua missão é ajudar o usuário a:
1. Entender a tela atual
2. Navegar no sistema
3. Executar tarefas corretamente
4. Identificar pendências
5. Resumir dados e casos
6. Priorizar ações
7. Entender normas do eSocial e INSS

REGRAS IMPORTANTES:
- Responda sempre em português brasileiro
- Seja direto e prático — o usuário está trabalhando
- Use linguagem simples, evite jargões desnecessários
- Nunca invente regras ou dados que não existam
- Não substitua médico, advogado ou responsável humano
- Quando não souber, diga claramente
- Mantenha respostas curtas e objetivas (máximo 200 palavras)
- Use bullet points quando listar passos ou itens

CONTEXTO DO USUÁRIO:
Perfil: {perfil}
Tela atual: {tela_atual}
Empresa: {empresa}

DADOS ATUAIS DO SISTEMA:
{dados_sistema}

BASE NORMATIVA RELEVANTE:
{base_normativa}

Responda a pergunta do usuário com base neste contexto."""


class MensagemPrevIA(BaseModel):
    mensagem: str
    tela_atual: str = "dashboard"
    historico: Optional[List[dict]] = []


@router.post("/chat")
async def chat_previa(
    data: MensagemPrevIA,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    hoje = date.today()

    # Buscar dados do sistema
    afas_r = await db.execute(
        select(Afastamento).where(
            Afastamento.empresa_id == current_user.empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    afastamentos = afas_r.scalars().all()

    trab_r = await db.execute(
        select(func.count(Trabalhador.id)).where(
            Trabalhador.empresa_id == current_user.empresa_id
        )
    )
    total_trab = trab_r.scalar() or 0

    # Montar resumo dos dados
    dados_sistema = f"""
- Total de trabalhadores: {total_trab}
- Afastamentos ativos: {len(afastamentos)}
- Em limbo/judicial: {sum(1 for a in afastamentos if a.status == 'limbo')}
- Retornos atrasados: {sum(1 for a in afastamentos if a.data_prevista_retorno and a.data_prevista_retorno < hoje)}
- Sem previsão de retorno: {sum(1 for a in afastamentos if not a.data_prevista_retorno)}
- Custo diário estimado: R$ {sum(float(a.salario_base or 3000)/30 for a in afastamentos):.0f}
"""

    # Base normativa fixa contextual
    tela = data.tela_atual.lower()
    msg = data.mensagem.lower()
    if "s-2230" in msg or "afastamento" in msg:
        base_norm = "eSocial S-2230: evento de afastamento temporário. Prazo: até 5 dias úteis após o afastamento."
    elif "s-2240" in msg or "agente" in msg:
        base_norm = "eSocial S-2240: condições ambientais de trabalho. Deve ser enviado quando há exposição a agentes nocivos."
    elif "ppp" in msg:
        base_norm = "PPP (Perfil Profissiográfico Previdenciário): documento obrigatório na rescisão ou concessão de benefício. Base: Lei 8.213/91 art. 58."
    elif "inss" in msg or "benefício" in msg:
        base_norm = "Benefício por incapacidade: primeiros 15 dias custeados pela empresa, a partir do 16º dia o INSS assume. Prazo de carência: 12 contribuições."
    elif "atestado" in msg:
        base_norm = "Portarias MPS/INSS 13 e 14/2026 (Novo Atestmed): atestado deve conter CID, prazo, CRM e assinatura do médico para ser válido."
    elif "ltcat" in msg:
        base_norm = "LTCAT (Laudo Técnico das Condições Ambientais do Trabalho): obrigatório para empresas com agentes nocivos. Validade: sem prazo fixo mas deve ser atualizado quando houver mudança."
    else:
        base_norm = "Normas disponíveis: eSocial S-2230, S-2240, S-2220, PPP (Lei 8.213/91), Portarias INSS 13 e 14/2026."

    tela_desc = TELAS.get(tela, f"Tela: {tela}")
    system = SYSTEM_PROMPT.format(
        perfil=current_user.perfil or "RH",
        tela_atual=tela_desc,
        empresa=current_user.empresa_id,
        dados_sistema=dados_sistema.strip(),
        base_normativa=base_norm,
    )

    # Montar histórico com system prompt embutido
    messages = [{"role": "user", "content": "[CONTEXTO DO SISTEMA]\n" + system + "\n[FIM DO CONTEXTO]"}]
    messages.append({"role": "assistant", "content": "Entendido. Estou pronto para ajudar como PrevIA."})
    for h in (data.historico or [])[-6:]:
        if h.get("role") in ["user", "assistant"]:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": data.mensagem})

    # Chamar OpenRouter
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "max_tokens": 400,
                "messages": messages,
            }
        )
        resp.raise_for_status()
        result = resp.json()
        resposta = result["choices"][0]["message"]["content"]

    return {
        "resposta": resposta,
        "tela": tela_desc,
        "perfil": current_user.perfil,
    }
