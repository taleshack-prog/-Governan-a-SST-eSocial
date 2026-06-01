# ==============================================================
# SST ESOCIAL GOV — FastAPI main.py
# Arquivo: api/main.py
# Porta: 8001 (evita conflito com outros projetos)
# ==============================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.config import settings
from api.routers.afastamentos import router as afastamentos_router
from api.routers.radar import router as radar_router
from api.routers.ppp import router as ppp_router
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

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
app.include_router(atestados_router,      prefix=f"{API_PREFIX}/afastamentos", tags=["Atestados"])
app.include_router(auditoria.router,        prefix=f"{API_PREFIX}/auditoria",   tags=["Auditoria"])


@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
