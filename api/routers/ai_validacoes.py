# api/routers/ai_validacoes.py — SST ESOCIAL GOV
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from api.database import get_db
from api.models.ai_validacao import AiValidacao
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()


class FeedbackInput(BaseModel):
    rating: Optional[int] = None
    correto: Optional[bool] = None
    comentario: Optional[str] = None
    correcao: Optional[dict] = None


@router.get("/")
async def listar_validacoes(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(AiValidacao).where(AiValidacao.empresa_id == current_user.empresa_id)
        .order_by(AiValidacao.created_at.desc())
    )
    return [
        {
            "id": str(v.id),
            "tipo_validacao": v.tipo_validacao,
            "status": v.status,
            "confidence_score": v.confidence_score,
            "grade_label": v.grade_label,
            "needs_human_review": v.needs_human_review,
            "created_at": str(v.created_at),
        }
        for v in result.scalars()
    ]


@router.get("/{val_id}")
async def obter_validacao(
    val_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(AiValidacao).where(
            AiValidacao.id == val_id,
            AiValidacao.empresa_id == current_user.empresa_id,
        )
    )
    val = result.scalar_one_or_none()
    if not val:
        raise HTTPException(status_code=404, detail="Validação não encontrada")
    return {
        "id": str(val.id),
        "tipo_validacao": val.tipo_validacao,
        "status": val.status,
        "confidence_score": val.confidence_score,
        "grade_label": val.grade_label,
        "resultado": val.resultado,
        "erros": val.erros,
        "alertas": val.alertas,
        "sugestoes": val.sugestoes,
        "model_used": val.model_used,
        "tokens_used": val.tokens_used,
        "needs_human_review": val.needs_human_review,
    }


@router.post("/{val_id}/feedback")
async def registrar_feedback(
    val_id: UUID,
    data: FeedbackInput,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(AiValidacao).where(
            AiValidacao.id == val_id,
            AiValidacao.empresa_id == current_user.empresa_id,
        )
    )
    val = result.scalar_one_or_none()
    if not val:
        raise HTTPException(status_code=404, detail="Validação não encontrada")

    # Salvar feedback para RLHF
    from api.models.ai_validacao import AiValidacao as AV
    from datetime import datetime, timezone

    # Marcar como revisado se feedback negativo
    if data.correto is False:
        val.needs_human_review = True
        val.reviewed_by = current_user.id
        val.reviewed_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Feedback registrado com sucesso",
        "validacao_id": str(val_id),
        "correto": data.correto,
        "impacto": "Registrado para melhoria do modelo"
    }
