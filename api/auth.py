# ==============================================================
# SST ESOCIAL GOV — Autenticação JWT + RBAC
# Arquivo: api/auth.py
# ==============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.config import settings
from api.database import get_db
from api.models.usuario import Usuario

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

PERFIS_HIERARQUIA = {
    "admin": 100,
    "sst": 60,
    "saude_ocupacional": 50,
    "rh": 40,
    "juridico": 30,
    "leitura": 10,
}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.ativo:
        raise credentials_exception
    return user


def require_perfil(perfil_minimo: str):
    """Decorator factory para exigir nível mínimo de perfil."""
    async def dependency(current_user: Usuario = Depends(get_current_user)):
        nivel_usuario = PERFIS_HIERARQUIA.get(current_user.perfil, 0)
        nivel_minimo = PERFIS_HIERARQUIA.get(perfil_minimo, 999)
        if nivel_usuario < nivel_minimo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Perfil '{perfil_minimo}' ou superior necessário.",
            )
        return current_user
    return dependency
