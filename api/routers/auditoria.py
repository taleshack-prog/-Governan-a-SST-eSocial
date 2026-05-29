# api/routers/auditoria.py — SST ESOCIAL GOV
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.audit_log import AuditLog
from api.models.usuario import Usuario
from api.auth import require_perfil

router = APIRouter()


@router.get("/")
async def listar_auditoria(
    tabela: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_perfil("admin")),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if tabela:
        query = query.where(AuditLog.tabela == tabela)
    if current_user.empresa_id:
        query = query.where(AuditLog.empresa_id == current_user.empresa_id)

    result = await db.execute(query)
    return [
        {
            "id": log.id,
            "tabela": log.tabela,
            "operacao": log.operacao,
            "registro_id": str(log.registro_id),
            "hash_atual": log.hash_atual,
            "created_at": str(log.created_at),
        }
        for log in result.scalars()
    ]
