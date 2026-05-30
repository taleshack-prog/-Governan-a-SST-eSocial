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
    access_token_expire_minutes: int = 60
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

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # IA
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-haiku-4-5"
    llm_fallback_model: str = "openai/gpt-4o-mini"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # CORS
    cors_origins: List[str] = ["http://localhost:3004", "http://localhost:3003", "http://localhost:3000", "http://localhost:8003"]

    # Logs
    log_level: str = "INFO"

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def get_database_url_sync(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
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
