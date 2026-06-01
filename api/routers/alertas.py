# ==============================================================
# SST ESOCIAL GOV — Router: Alertas de Afastamento
# Arquivo: api/routers/alertas.py
# ==============================================================

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from api.database import get_db, set_tenant
from api.models.afastamento import AlertaAfastamento
from api.models.usuario import Usuario
from api.auth import get_current_user

router = APIRouter()

PRIORIDADE_COR = {
    "critica": "red",
    "alta": "orange",
    "media": "yellow",
    "baixa": "blue",
}

@router.get("/")
async def listar_alertas(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(AlertaAfastamento).where(
            and_(
                AlertaAfastamento.empresa_id == current_user.empresa_id,
                AlertaAfastamento.resolvido == False,
            )
        ).order_by(AlertaAfastamento.created_at.desc())
    )
    alertas = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "afastamento_id": str(a.afastamento_id),
            "tipo": a.tipo,
            "mensagem": a.mensagem,
            "prioridade": a.prioridade,
            "cor": PRIORIDADE_COR.get(a.prioridade, "blue"),
            "lido": a.lido,
            "created_at": str(a.created_at),
        }
        for a in alertas
    ]

@router.patch("/{alerta_id}/lido")
async def marcar_lido(
    alerta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(AlertaAfastamento).where(
            and_(
                AlertaAfastamento.id == alerta_id,
                AlertaAfastamento.empresa_id == current_user.empresa_id,
            )
        )
    )
    alerta = result.scalar_one_or_none()
    if alerta:
        alerta.lido = True
        await db.commit()
    return {"ok": True}

@router.patch("/{alerta_id}/resolver")
async def resolver_alerta(
    alerta_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    await set_tenant(db, current_user.empresa_id)
    result = await db.execute(
        select(AlertaAfastamento).where(
            and_(
                AlertaAfastamento.id == alerta_id,
                AlertaAfastamento.empresa_id == current_user.empresa_id,
            )
        )
    )
    alerta = result.scalar_one_or_none()
    if alerta:
        alerta.resolvido = True
        await db.commit()
    return {"ok": True}

@router.post("/executar-verificacao")
async def executar_verificacao_manual(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Executa verificação manual de alertas."""
    from api.tasks.afastamento_tasks import _verificar_alertas
    result = await _verificar_alertas()
    return result
