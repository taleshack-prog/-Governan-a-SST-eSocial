# ==============================================================
# SST ESOCIAL GOV — Database async (SQLAlchemy + asyncpg)
# Arquivo: api/database.py
# ==============================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from api.config import settings


# Engine assíncrona
engine = create_async_engine(
    settings.get_database_url(),
    echo=settings.app_env == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base para todos os modelos ORM do projeto SST."""
    pass


async def get_db() -> AsyncSession:
    """Dependency injection: fornece sessão AsyncSQL para os endpoints."""
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(session: AsyncSession, empresa_id: str) -> None:
    """Define o contexto do tenant (RLS) na sessão PostgreSQL."""
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": str(empresa_id)},
    )
