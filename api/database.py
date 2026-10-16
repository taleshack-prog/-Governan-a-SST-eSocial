# ==============================================================
# SST ESOCIAL GOV — Database async (SQLAlchemy + asyncpg)
# Arquivo: api/database.py
# ==============================================================

from typing import AsyncGenerator
from contextvars import ContextVar
from uuid import UUID as _UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session as _OrmSession
from sqlalchemy import text, event
from sqlalchemy.engine import URL as SAUrl
from api.config import settings


def _build_engine():
    # URL.create() faz encoding automático de caracteres especiais na senha (#, @, etc.)
    # connect_args ssl="require" é obrigatório para Supabase
    url = SAUrl.create(
        drivername="postgresql+asyncpg",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )
    return create_async_engine(
        url,
        echo=settings.app_env == "development",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={"ssl": "require"} if settings.app_env == "production" else {},
    )

engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# ==============================================================
# Adendo 05 / RN-24 — contexto de ESCRITORIO por request (base do RLS)
# ==============================================================
# O isolamento e imposto no banco (RLS) a partir da GUC 'app.escritorio'. O desafio: os endpoints
# dao commit no meio do request, e 'SET LOCAL' morre com a transacao. Por isso a chave vive num
# ContextVar (isolado por request) e e REAPLICADA no inicio de CADA transacao pelo listener
# 'after_begin'. Assim nenhuma query roda sem o contexto depois de autenticada.
escritorio_ctx: ContextVar[str | None] = ContextVar("escritorio_ctx", default=None)


def set_escritorio_ctx(escritorio_id) -> str | None:
    """Fixa o escritorio do request. Valida como UUID (nunca interpola valor arbitrario)."""
    if escritorio_id is None:
        escritorio_ctx.set(None)
        return None
    valor = str(_UUID(str(escritorio_id)))
    escritorio_ctx.set(valor)
    return valor


@event.listens_for(_OrmSession, "after_begin")
def _aplicar_escritorio(session, transaction, connection):  # noqa: ARG001
    """Reaplica a GUC no inicio de cada transacao (inclusive apos cada commit)."""
    esc = escritorio_ctx.get()
    if esc:
        connection.exec_driver_sql(f"SET LOCAL app.escritorio = '{esc}'")


async def aplicar_escritorio_agora(session: AsyncSession) -> None:
    """Aplica a GUC na transacao JA aberta (o after_begin dela ja passou)."""
    esc = escritorio_ctx.get()
    if esc:
        await session.execute(text(f"SET LOCAL app.escritorio = '{esc}'"))


def ativar_escritorio_por_empresa(session, empresa_id) -> str | None:
    """Bootstrap de contexto para WORKER (Celery), que roda fora de um request.

    A task tem o empresa_id, mas sob RLS ela nao conseguiria ler 'empresas' para descobrir o
    escritorio. app_escritorio_de_empresa e SECURITY DEFINER e faz so essa traducao. Chame isto
    logo apos abrir a sessao sincrona e ANTES de qualquer consulta a dado de cliente.
    """
    esc = session.execute(
        text("SELECT app_escritorio_de_empresa(CAST(:e AS uuid))"), {"e": str(empresa_id)}
    ).scalar()
    if not esc:
        return None
    valor = set_escritorio_ctx(esc)
    session.execute(text(f"SET LOCAL app.escritorio = '{valor}'"))
    return valor


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(session: AsyncSession, empresa_id: str) -> None:
    tenant_id = str(empresa_id)
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))


# Sessão síncrona para uso em tasks Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

def _build_sync_engine():
    url = SAUrl.create(
        drivername="postgresql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )
    return create_engine(
        url,
        pool_size=3,
        max_overflow=5,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"} if settings.app_env == "production" else {},
    )

_sync_engine = _build_sync_engine()
SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)

@contextmanager
def get_sync_session() -> Session:
    session = SyncSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
