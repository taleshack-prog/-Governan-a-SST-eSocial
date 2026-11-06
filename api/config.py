# ==============================================================
# SST ESOCIAL GOV — Configurações do Backend
# Arquivo: api/config.py
# ==============================================================

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Aplicação
    app_name: str = "SST eSocial Gov"
    app_env: str = "development"
    secret_key: str = "changeme-must-be-64-chars-minimum-in-production-env"
    access_token_expire_minutes: int = 43200
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Banco de dados
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "sst_esocial_db"
    postgres_user: str = "sst_user"
    postgres_password: str = "changeme"
    database_url: str = ""
    database_url_sync: str = ""
    # Role da aplicacao (Adendo 05 RN-24): NOSUPERUSER NOBYPASSRLS, para o RLS valer.
    # Vazio => cai no POSTGRES_USER/POSTGRES_PASSWORD (dono do banco).
    app_db_user: str = ""
    app_db_password: str = ""

    @property
    def db_user(self) -> str:
        return self.app_db_user or self.postgres_user

    @property
    def db_password(self) -> str:
        return self.app_db_password if self.app_db_user else self.postgres_password

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # IA
    anthropic_api_key: str = ""
    llm_model: str = "anthropic/claude-haiku-4-5"
    llm_fallback_model: str = "openai/gpt-4o-mini"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Consulta de CNPJ (Adendo 03 RF-0.150) — provider atras de adapter, trocavel por config
    cnpj_provider: str = "brasilapi"          # brasilapi | serpro (futuro)
    cnpj_timeout: int = 12

    # SSL do banco (06/11) — chave propria, separada do APP_ENV por decisao da Carolina.
    # Antes, APP_ENV governava o echo do SQL E o ssl obrigatorio. Amarrados, a correcao do log
    # (segura) ficava refem da mudanca de SSL (reinicia servico). Agora cada uma vira sozinha.
    # Padrao desligado: a rede privada da Railway ja cifra o trafego por WireGuard, entao o SSL
    # aqui e segunda camada, nao protecao ausente. Ligar so depois de provado de dentro do conteiner.
    db_ssl: bool = False

    # Documentacao da API. Fechada fora de desenvolvimento: /api/docs e /api/openapi.json
    # expunham a superficie inteira da API sem autenticacao.
    docs_publicas: bool = False

    # CORS — restrito aos dominios do sistema (decisao da Carolina, 06/11).
    # Antes o main.py tinha allow_origins=["*"] fixo no codigo e esta lista nao era lida por
    # ninguem. Qualquer site podia chamar a API do navegador.
    cors_origins: List[str] = [
        "https://www.radarprevi.com.br",
        "https://radarprevi.com.br",
        "https://governan-a-sst-e-social.vercel.app",
        "https://governan-a-sst-e-social-1xq8.vercel.app",   # app do funcionario
        "http://localhost:3000", "http://localhost:3003", "http://localhost:3004",
        "http://localhost:3005", "http://localhost:8003", "http://localhost:5173",
    ]
    # Deploys de previa da Vercel nascem com URL unica a cada push. O regex cobre apenas o
    # namespace da nossa equipe (hack-tech-farm) — nenhum outro dominio .vercel.app entra.
    cors_origin_regex: str = r"^https://[a-z0-9-]+-hack-tech-farm\.vercel\.app$"

    # Logs
    log_level: str = "INFO"

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def get_database_url_sync(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
