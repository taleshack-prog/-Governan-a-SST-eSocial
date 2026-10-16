# api/routers/auth.py — SST ESOCIAL GOV
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db, set_escritorio_ctx, aplicar_escritorio_agora
from api.models.usuario import Usuario
from api.auth import verify_password, create_access_token, get_current_user, hash_password
from pydantic import BaseModel, EmailStr

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    nome: str
    perfil: str
    empresa_id: str | None


class UserCreate(BaseModel):
    email: EmailStr
    senha: str
    nome: str
    perfil: str = "leitura"
    empresa_id: str | None = None


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Adendo 05 / RN-24: a busca acima roda SEM contexto de escritorio (ainda nao sabemos qual e —
    # e por isso que a policy de SELECT da 'usuarios' tolera a GUC vazia). Agora que o usuario esta
    # autenticado, FIXA o contexto ANTES de gravar: sem isso o UPDATE de ultimo_login nao casa com
    # a policy, atinge zero linhas e o ORM derruba o login inteiro.
    set_escritorio_ctx(user.escritorio_id)
    await aplicar_escritorio_agora(db)

    # Atualizar último login
    user.ultimo_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token({"sub": str(user.id), "empresa_id": str(user.empresa_id)})
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        nome=user.nome,
        perfil=user.perfil,
        empresa_id=str(user.empresa_id) if user.empresa_id else None,
    )


@router.get("/me")
async def get_me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "nome": current_user.nome,
        "perfil": current_user.perfil,
        "empresa_id": str(current_user.empresa_id) if current_user.empresa_id else None,
    }
