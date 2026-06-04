# ==============================================================
# SST ESOCIAL GOV — Database async (SQLAlchemy + asyncpg)
# Arquivo: api/database.py
# ==============================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from api.config import settings


def _build_engine():
    db_url = settings.get_database_url()
    # Se a URL tem senha com caracteres especiais, usa connect_args
    if settings.postgres_password and '#' in settings.postgres_password:
        # Remove a senha da URL e passa via connect_args
        import re
        from urllib.parse import quote_plus
        password_encoded = quote_plus(settings.postgres_password)
        db_url = re.sub(r':([^@]+)@', f':{password_encoded}@', db_url)
    return create_async_engine(
        db_url,
        echo=settings.app_env == "development",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(session: AsyncSession, empresa_id: str) -> None:
    tenant_id = str(empresa_id)
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
