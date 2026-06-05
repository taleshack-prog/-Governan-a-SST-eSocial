# ==============================================================
# SST ESOCIAL GOV — FastAPI main.py
# Arquivo: api/main.py
# Porta: 8001 (evita conflito com outros projetos)
# ==============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import traceback

from api.config import settings
from api.routers.afastamentos import router as afastamentos_router
from api.routers.radar import router as radar_router
from api.routers.ppp import router as ppp_router
from api.routers.alertas import router as alertas_router
from api.routers.auth_funcionario import router as auth_func_router
from api.routers.admin import router as admin_router
from api.routers.radar_financeiro import router as radar_fin_router
from api.routers.inconsistencias import router as inconsistencias_router
from api.routers.tendencias import router as tendencias_router
from api.routers.previa import router as previa_router
from api.routers.atestados import router as atestados_router
from api.routers import (
    auth, empresas, trabalhadores, documentos,
    agentes_nocivos, exames_medicos, cat, ai_validacoes, auditoria
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 {settings.app_name} iniciando [env={settings.app_env}]")
    yield
    # Shutdown
    print(f"🛑 {settings.app_name} encerrando")


app = FastAPI(
    title="SST eSocial Gov — API",
    description="Sistema de Governança SST/eSocial com IA. Validação de documentos, agentes nocivos e conformidade regulatória.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"[500] {request.method} {request.url.path}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__, "trace": tb},
    )

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
API_PREFIX = "/api"
app.include_router(auth.router,             prefix=f"{API_PREFIX}/auth",        tags=["Auth"])
app.include_router(empresas.router,         prefix=f"{API_PREFIX}/empresas",    tags=["Empresas"])
app.include_router(trabalhadores.router,    prefix=f"{API_PREFIX}/trabalhadores", tags=["Trabalhadores"])
app.include_router(documentos.router,       prefix=f"{API_PREFIX}/documentos",  tags=["Documentos"])
app.include_router(agentes_nocivos.router,  prefix=f"{API_PREFIX}/agentes",     tags=["Agentes Nocivos"])
app.include_router(exames_medicos.router,   prefix=f"{API_PREFIX}/exames",      tags=["Exames Médicos"])
app.include_router(cat.router,              prefix=f"{API_PREFIX}/cat",         tags=["CAT"])
app.include_router(ai_validacoes.router,    prefix=f"{API_PREFIX}/validacoes",  tags=["IA Validações"])
app.include_router(afastamentos_router,     prefix=f"{API_PREFIX}/afastamentos", tags=["Afastamentos"])
app.include_router(radar_router,           prefix=f"{API_PREFIX}/radar", tags=["Radar Previdenciário"])
app.include_router(ppp_router,             prefix=f"{API_PREFIX}/ppp", tags=["PPP Digital"])
app.include_router(alertas_router,         prefix=f"{API_PREFIX}/alertas", tags=["Alertas"])
app.include_router(auth_func_router,       prefix=f"{API_PREFIX}/funcionarios/auth", tags=["Auth Funcionário"])
app.include_router(admin_router,           prefix=f"{API_PREFIX}/admin", tags=["Admin"])
app.include_router(radar_fin_router,      prefix=f"{API_PREFIX}/radar-financeiro", tags=["Radar Financeiro"])
app.include_router(inconsistencias_router, prefix=f"{API_PREFIX}/inconsistencias", tags=["Inconsistências"])
app.include_router(tendencias_router,      prefix=f"{API_PREFIX}/tendencias", tags=["Tendências"])
app.include_router(previa_router,          prefix=f"{API_PREFIX}/previa", tags=["PrevIA"])
app.include_router(atestados_router,      prefix=f"{API_PREFIX}/afastamentos", tags=["Atestados"])
app.include_router(auditoria.router,        prefix=f"{API_PREFIX}/auditoria",   tags=["Auditoria"])


@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/api/debug/db", tags=["Health"])
async def debug_db():
    """Testa conexão com o banco e retorna o erro exato se falhar."""
    from sqlalchemy import text
    from api.database import engine
    config = {
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "db": settings.postgres_db,
        "user": settings.postgres_user,
        "password_set": bool(settings.postgres_password and settings.postgres_password != "changeme"),
    }
    try:
        async with engine.connect() as conn:
            row = await conn.execute(text("SELECT current_user, version()"))
            r = row.fetchone()
            return {"status": "ok", "config": config, "pg_user": r[0], "pg_version": r[1][:50]}
    except Exception as e:
        return {"status": "error", "config": config, "error": str(e), "type": type(e).__name__}
