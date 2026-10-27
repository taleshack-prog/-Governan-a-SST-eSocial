# api/routers/auth.py — SST ESOCIAL GOV
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

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
    # A busca pelo e-mail precisa rodar SEM contexto de escritorio: ele so sera conhecido depois
    # de achar o usuario. Hoje isso acontece sozinho porque cada requisicao ASGI nasce num task
    # proprio, com copia limpa do ContextVar — mas depender disso e depender de um detalhe do
    # servidor. Limpar aqui torna a condicao explicita: se o contexto de outra requisicao
    # vazasse, a policy de leitura filtraria pelo escritorio ERRADO e o usuario receberia
    # "email ou senha incorretos" sem que houvesse nada de errado com a senha dele.
    set_escritorio_ctx(None)
    # A BUSCA PASSA PELA FUNCAO, nao pela tabela (migration 057; passo 2 de 3 do isolamento).
    #
    # Enquanto a leitura era direta, ela dependia do ramo permissivo da policy de usuarios — o
    # "contexto vazio ve todo mundo". Esse ramo e o que sai no passo 3, e com ele a consulta
    # direta deixaria de encontrar qualquer linha: o sistema responderia "email ou senha
    # incorretos" para credenciais corretas, para todos os usuarios de uma vez.
    #
    # auth_usuario_por_email() atravessa a RLS pelos privilegios do dono, exige o e-mail EXATO e
    # devolve no maximo uma linha. E o UNICO ponto do sistema autorizado a ler usuarios sem
    # contexto de escritorio; qualquer outra leitura continua passando pela policy.
    #
    # from_statement() porque o ORM precisa da ENTIDADE, e nao de uma tupla: o codigo abaixo grava
    # ultimo_login neste mesmo objeto, e isso exige que ele esteja gerenciado pela sessao.
    result = await db.execute(
        select(Usuario).from_statement(
            text("SELECT * FROM auth_usuario_por_email(:email)")
        ).params(email=form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Adendo 05 / RN-24: a busca acima roda SEM contexto de escritorio (ainda nao sabemos qual e —
    # e por isso ela passa pela funcao, e nao pela tabela; desde a migration 058 a policy de
    # SELECT de 'usuarios' NAO tolera mais a GUC vazia). Agora que o usuario esta
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
