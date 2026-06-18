# ==============================================================
# SST ESOCIAL GOV — Router: Afastamentos
# Arquivo: api/routers/afastamentos.py
# ==============================================================

from uuid import UUID
from datetime import date, datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from api.database import get_db, set_tenant
from api.models.afastamento import Afastamento, Atestado, AfastamentoMensagem
from api.models.trabalhador import Trabalhador
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────

class AfastamentoCreate(BaseModel):
    trabalhador_id: UUID
    tipo: str
    data_inicio: date
    cid: Optional[str] = None
    cid_descricao: Optional[str] = None
    motivo_informado: Optional[str] = None
    salario_base: Optional[float] = None


class AfastamentoUpdate(BaseModel):
    status: Optional[str] = None
    data_prevista_retorno: Optional[date] = None
    data_retorno_real: Optional[date] = None
    cid: Optional[str] = None
    cid_descricao: Optional[str] = None
    observacoes: Optional[str] = None
    responsavel_rh_id: Optional[UUID] = None
    nexo_acidentario: Optional[bool] = None
    cat_emitida: Optional[bool] = None
    beneficio_inss: Optional[str] = None


class MensagemCreate(BaseModel):
    mensagem: str
    remetente_tipo: str = "rh"


# ── Helpers ───────────────────────────────────────────────────

def calcular_custo(salario: float, dias: int) -> dict:
    """Calcula custos do afastamento conforme legislação."""
    custo_dia = salario / 30
    primeiros_15 = min(dias, 15) * custo_dia
    inss = max(0, (dias - 15)) * custo_dia
    horas_extras_est = primeiros_15 * 0.15
    substituicao_est = primeiros_15 * 0.20
    return {
        "custo_primeiros_15dias": round(primeiros_15, 2),
        "custo_inss": round(inss, 2),
        "horas_extras_estimado": round(horas_extras_est, 2),
        "substituicao_estimado": round(substituicao_est, 2),
        "custo_total": round(primeiros_15 + horas_extras_est + substituicao_est, 2),
    }


def afastamento_to_dict(a: Afastamento, trabalhador_nome: str = "") -> dict:
    return {
        "id": str(a.id),
        "trabalhador_id": str(a.trabalhador_id),
        "trabalhador_nome": trabalhador_nome,
        "tipo": a.tipo,
        "cid": a.cid,
        "cid_descricao": a.cid_descricao,
        "data_inicio": str(a.data_inicio),
        "data_prevista_retorno": str(a.data_prevista_retorno) if a.data_prevista_retorno else None,
        "data_retorno_real": str(a.data_retorno_real) if a.data_retorno_real else None,
        "dias_afastamento": a.dias_afastamento,
        "status": a.status,
        "num_atestados": a.num_atestados,
        "num_indeferimentos": a.num_indeferimentos,
        "nexo_acidentario": a.nexo_acidentario,
        "cat_emitida": a.cat_emitida,
        "beneficio_inss": a.beneficio_inss,
        "salario_base": float(a.salario_base) if a.salario_base else None,
        "custo_primeiros_15dias": float(a.custo_primeiros_15dias) if a.custo_primeiros_15dias else None,
        "custo_total_estimado": float(a.custo_total_estimado) if a.custo_total_estimado else None,
        "motivo_informado": a.motivo_informado,
        "observacoes": a.observacoes,
        "historico": a.historico or [],
        "created_at": str(a.created_at),
    }


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/")
async def listar_afastamentos(
    status: Optional[str] = None,
    trabalhador_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    query = select(Afastamento, Trabalhador).join(
        Trabalhador, Afastamento.trabalhador_id == Trabalhador.id
    ).where(Afastamento.empresa_id == current_user.empresa_id)

    if status:
        query = query.where(Afastamento.status == status)
    if trabalhador_id:
        query = query.where(Afastamento.trabalhador_id == trabalhador_id)

    query = query.order_by(Afastamento.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    return [afastamento_to_dict(a, t.nome) for a, t in rows]


@router.get("/kpis")
async def kpis_afastamentos(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    empresa_id = current_user.empresa_id

    total = await db.execute(
        select(func.count()).where(Afastamento.empresa_id == empresa_id)
    )
    ativos = await db.execute(
        select(func.count()).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )
    pendentes = await db.execute(
        select(func.count()).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.in_(["recebido", "pendente"])
        )
    )
    retorno_proximo = await db.execute(
        select(func.count()).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.data_prevista_retorno <= date.today(),
            Afastamento.status.notin_(["encerrado"])
        )
    )
    custo_total = await db.execute(
        select(func.sum(Afastamento.custo_total_estimado)).where(
            Afastamento.empresa_id == empresa_id,
            Afastamento.status.notin_(["encerrado"])
        )
    )

    return {
        "total": total.scalar() or 0,
        "ativos": ativos.scalar() or 0,
        "pendentes": pendentes.scalar() or 0,
        "retorno_proximo": retorno_proximo.scalar() or 0,
        "custo_total_estimado": float(custo_total.scalar() or 0),
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def criar_afastamento(
    data: AfastamentoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)

    # Verificar trabalhador
    trab = await db.execute(
        select(Trabalhador).where(
            Trabalhador.id == data.trabalhador_id,
            Trabalhador.empresa_id == current_user.empresa_id
        )
    )
    trabalhador = trab.scalar_one_or_none()
    if not trabalhador:
        raise HTTPException(status_code=404, detail="Trabalhador não encontrado")

    # Calcular custo se salário informado
    custo = {}
    if data.salario_base:
        custo = calcular_custo(data.salario_base, 30)

    afastamento = Afastamento(
        empresa_id=current_user.empresa_id,
        trabalhador_id=data.trabalhador_id,
        tipo=data.tipo,
        data_inicio=data.data_inicio,
        cid=data.cid,
        cid_descricao=data.cid_descricao,
        motivo_informado=data.motivo_informado,
        salario_base=data.salario_base,
        custo_primeiros_15dias=custo.get("custo_primeiros_15dias"),
        custo_total_estimado=custo.get("custo_total"),
        status="recebido",
        historico=[{
            "data": str(datetime.now(timezone.utc)),
            "acao": "Afastamento registrado",
            "usuario": current_user.nome,
        }],
        created_by=current_user.id,
    )
    db.add(afastamento)
    await db.commit()
    await db.refresh(afastamento)

    return afastamento_to_dict(afastamento, trabalhador.nome)


@router.get("/{afastamento_id}")
async def obter_afastamento(
    afastamento_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Afastamento, Trabalhador).join(
            Trabalhador, Afastamento.trabalhador_id == Trabalhador.id
        ).where(
            Afastamento.id == afastamento_id,
            Afastamento.empresa_id == current_user.empresa_id,
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Afastamento não encontrado")
    a, t = row
    return afastamento_to_dict(a, t.nome)


@router.patch("/{afastamento_id}")
async def atualizar_afastamento(
    afastamento_id: UUID,
    data: AfastamentoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(Afastamento).where(
            Afastamento.id == afastamento_id,
            Afastamento.empresa_id == current_user.empresa_id,
        )
    )
    af = result.scalar_one_or_none()
    if not af:
        raise HTTPException(status_code=404, detail="Afastamento não encontrado")

    changes = []
    for field, value in data.model_dump(exclude_none=True).items():
        old = getattr(af, field)
        if old != value:
            setattr(af, field, value)
            changes.append(f"{field}: {old} → {value}")

    if changes:
        historico = af.historico or []
        historico.append({
            "data": str(datetime.now(timezone.utc)),
            "acao": f"Atualizado: {', '.join(changes)}",
            "usuario": current_user.nome,
        })
        af.historico = historico
        af.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(af)
    return afastamento_to_dict(af)


@router.get("/{afastamento_id}/mensagens")
async def listar_mensagens(
    afastamento_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(AfastamentoMensagem).where(
            AfastamentoMensagem.afastamento_id == afastamento_id,
            AfastamentoMensagem.empresa_id == current_user.empresa_id,
        ).order_by(AfastamentoMensagem.created_at.asc())
    )
    msgs = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "remetente_tipo": m.remetente_tipo,
            "mensagem": m.mensagem,
            "lida": m.lida,
            "created_at": str(m.created_at),
        }
        for m in msgs
    ]


@router.post("/{afastamento_id}/mensagens")
async def enviar_mensagem(
    afastamento_id: UUID,
    data: MensagemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    msg = AfastamentoMensagem(
        empresa_id=current_user.empresa_id,
        afastamento_id=afastamento_id,
        remetente_id=current_user.id,
        remetente_tipo=data.remetente_tipo,
        mensagem=data.mensagem,
    )
    db.add(msg)
    await db.commit()
    return {"message": "Mensagem enviada", "id": str(msg.id)}


@router.get("/{afastamento_id}/atestados")
async def listar_atestados(
    afastamento_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista atestados de um afastamento."""
    from api.models.atestado import AtestadoMedico
    result = await db.execute(
        select(AtestadoMedico).where(
            AtestadoMedico.afastamento_id == afastamento_id,
            AtestadoMedico.empresa_id == current_user.empresa_id,
        ).order_by(AtestadoMedico.created_at.desc())
    )
    atestados = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "nome_arquivo": a.nome_arquivo,
            "status_validacao": a.status_validacao,
            "score_validacao": a.score_validacao,
            "cid_extraido": a.cid_extraido,
            "medico_nome": a.medico_nome,
            "enviado_por": a.enviado_por,
            "created_at": str(a.created_at),
        }
        for a in atestados
    ]


@router.post("/{afastamento_id}/atestados/{atestado_id}/validar")
async def validar_atestado_ia(
    afastamento_id: UUID,
    atestado_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """RH valida atestado com IA."""
    import base64
    from api.models.atestado import AtestadoMedico

    result = await db.execute(
        select(AtestadoMedico).where(
            AtestadoMedico.id == atestado_id,
            AtestadoMedico.afastamento_id == afastamento_id,
            AtestadoMedico.empresa_id == current_user.empresa_id,
        )
    )
    atestado = result.scalar_one_or_none()
    if not atestado:
        raise HTTPException(status_code=404, detail="Atestado não encontrado.")

    if not atestado.conteudo_base64:
        raise HTTPException(status_code=400, detail="Conteúdo do atestado não disponível.")

    try:
        import httpx
        from api.config import settings

        conteudo_bytes = base64.b64decode(atestado.conteudo_base64)

        prompt = """Analise este atestado médico conforme as Portarias MPS/INSS 13 e 14/2026 (Novo Atestmed).

Extraia e valide:
1. Nome do paciente
2. CID-10 informado
3. Prazo de afastamento em dias
4. Nome e CRM do médico
5. Data de emissão
6. Assinatura/carimbo presente

Verifique conformidade com:
- Portaria 13/2026: campos obrigatórios do atestado
- Portaria 14/2026: requisitos para aceite pelo INSS

Responda APENAS em JSON:
{
  "status": "valido" ou "invalido" ou "pendente",
  "score": 0.0 a 1.0,
  "cid_extraido": "CID encontrado",
  "dias_extraidos": número,
  "medico_nome": "nome do médico",
  "medico_crm": "CRM",
  "alertas": ["lista de problemas encontrados"],
  "resumo": "análise em uma frase"
}"""

        # Extrair texto do PDF
        import fitz
        import io
        pdf_doc = fitz.open(stream=io.BytesIO(conteudo_bytes), filetype="pdf")
        texto_pdf = ""
        for page in pdf_doc:
            texto_pdf += page.get_text()
        pdf_doc.close()

        import anthropic as _anth
        _cli = _anth.Anthropic(api_key=settings.anthropic_api_key)
        _msg = _cli.messages.create(
            model="claude-haiku-4-5", max_tokens=500,
            messages=[{"role": "user", "content": prompt + "\n\nCONTEÚDO DO ATESTADO:\n" + texto_pdf[:3000]}]
        )
        texto = _msg.content[0].text

        import json, re
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            dados = json.loads(match.group())
        else:
            dados = {"status": "pendente", "score": 0.5, "alertas": ["Não foi possível analisar automaticamente"]}

    except Exception as e:
        dados = {"status": "pendente", "score": 0.5, "alertas": [f"Erro na análise: {str(e)[:100]}"]}

    # Atualizar atestado
    atestado.status_validacao = dados.get("status", "pendente")
    atestado.score_validacao = dados.get("score", 0.5)
    atestado.cid_extraido = dados.get("cid_extraido")
    atestado.dias_extraidos = dados.get("dias_extraidos")
    atestado.medico_nome = dados.get("medico_nome")
    atestado.medico_crm = dados.get("medico_crm")
    atestado.alertas = dados.get("alertas", [])
    await db.commit()

    return {
        "status": dados.get("status"),
        "score": dados.get("score"),
        "cid_extraido": dados.get("cid_extraido"),
        "dias_extraidos": dados.get("dias_extraidos"),
        "medico_nome": dados.get("medico_nome"),
        "alertas": dados.get("alertas", []),
        "resumo": dados.get("resumo", ""),
    }
