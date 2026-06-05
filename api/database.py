# ==============================================================
# SST ESOCIAL GOV — Database async (SQLAlchemy + asyncpg)
# Arquivo: api/database.py
# ==============================================================

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.engine import URL as SAUrl
from api.config import settings


def _build_engine():
    # URL.create() faz encoding automático de caracteres especiais na senha (#, @, etc.)
    # connect_args ssl="require" é obrigatório para Supabase
    url = SAUrl.create(
        drivername="postgresql+asyncpg",
        username=settings.postgres_user,
        password=settings.postgres_password,
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(session: AsyncSession, empresa_id: str) -> None:
    tenant_id = str(empresa_id)
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
