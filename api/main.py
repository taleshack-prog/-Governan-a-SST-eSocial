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
from uuid import uuid4
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
from api.routers.importacao import router as importacao_router
from api.routers.importacao_pdf import router as importacao_pdf_router
from api.routers.importacao_universal import router as importacao_universal_router
from api.routers.atestados import router as atestados_router
from api.routers.estabelecimentos import router as estabelecimentos_router
from api.routers.diagnostico import router as diagnostico_router
from api.routers.rubricas import router as rubricas_router
from api.routers.achados import router as achados_router
from api.routers.relatorios import router as relatorios_router
from api.routers.cnae import router as cnae_router
from api.routers.fundamentacao import router as fundamentacao_router
from api.routers import (
    auth, empresas, trabalhadores, documentos,
    agentes_nocivos, exames_medicos, cat, ai_validacoes, auditoria
)


async def _checar_papel_rls() -> None:
    """Adendo 05 / RN-24: o RLS so vale se a aplicacao NAO conectar com papel privilegiado.
    Superusuario ignora RLS sempre; BYPASSRLS tambem. Se isso acontecer, o isolamento por
    escritorio nao produz erro nenhum — simplesmente nao filtra. Logo, avisa alto na partida."""
    from sqlalchemy import text
    from api.database import engine
    try:
        async with engine.connect() as conn:
            r = (await conn.execute(text(
                "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
            ))).fetchone()
        if r is None:
            return
        usuario, super_, bypass = r[0], bool(r[1]), bool(r[2])
        if super_ or bypass:
            print("=" * 78)
            print(f"⚠️  ATENCAO: a aplicacao conectou como '{usuario}' "
                  f"(superuser={super_}, bypassrls={bypass}).")
            print("    O RLS do Adendo 05 NAO esta sendo aplicado — nao ha isolamento entre")
            print("    escritorios. Defina APP_DB_USER/APP_DB_PASSWORD para o papel radar_app.")
            print("=" * 78)
        else:
            print(f"🔒 Isolamento por escritorio ativo — conectado como '{usuario}' (RLS aplicavel).")
    except Exception as e:  # nunca derrubar a partida por causa da checagem
        print(f"⚠️  Nao foi possivel verificar o papel do banco: {type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🚀 {settings.app_name} iniciando [env={settings.app_env}]")
    await _checar_papel_rls()
    yield
    # Shutdown
    print(f"🛑 {settings.app_name} encerrando")


# Documentacao da API (item (c) da Carolina, 06/11): /api/docs, /api/redoc e
# /api/openapi.json respondiam sem autenticacao — a superficie inteira da API navegavel por
# qualquer um. Agora so em desenvolvimento, ou se DOCS_PUBLICAS for ligada de proposito.
_DOCS = settings.app_env == "development" or settings.docs_publicas

app = FastAPI(
    title="SST eSocial Gov — API",
    description="Sistema de Governança SST/eSocial com IA. Validação de documentos, agentes nocivos e conformidade regulatória.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if _DOCS else None,
    redoc_url="/api/redoc" if _DOCS else None,
    openapi_url="/api/openapi.json" if _DOCS else None,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Item (b) da Carolina, 06/11: erro 500 devolve mensagem generica com codigo de
    referencia; o stack trace fica no log.

    O traceback nomeia caminho de arquivo, numero de linha e estrutura interna — mapa da casa
    para quem estiver olhando. A referencia liga o que o usuario ve ao que ficou no log, sem
    entregar nada: o suporte pede o codigo e acha a ocorrencia.
    """
    ref = uuid4().hex[:12]
    print(f"[500 ref={ref}] {request.method} {request.url.path}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Erro interno no servidor. Informe a referência {ref} ao suporte.",
            "referencia": ref,
        },
    )

# Middlewares
# Item (d) da Carolina, 06/11: CORS restrito aos dominios do sistema. Antes era ["*"] fixo
# aqui, e a lista do config.py nao era lida por ninguem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routers
API_PREFIX = "/api"
app.include_router(auth.router,             prefix=f"{API_PREFIX}/auth",        tags=["Auth"])
app.include_router(empresas.router,         prefix=f"{API_PREFIX}/empresas",    tags=["Empresas"])
app.include_router(estabelecimentos_router, prefix=f"{API_PREFIX}/estabelecimentos", tags=["Estabelecimentos"])
app.include_router(cnae_router,             prefix=f"{API_PREFIX}/cnae",        tags=["CNAE / Enquadramento"])
app.include_router(fundamentacao_router,    prefix=f"{API_PREFIX}/fundamentacao", tags=["Fundamentação normativa"])
app.include_router(diagnostico_router, prefix=f"{API_PREFIX}/diagnostico", tags=["Diagnóstico"])
app.include_router(rubricas_router, prefix=f"{API_PREFIX}/rubricas", tags=["Rubricas"])
app.include_router(achados_router, prefix=f"{API_PREFIX}/achados", tags=["Achados"])
app.include_router(relatorios_router, prefix=f"{API_PREFIX}/relatorios", tags=["Relatórios"])
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
app.include_router(importacao_router,      prefix=f"{API_PREFIX}/importacao", tags=["Importação"])
app.include_router(importacao_pdf_router,  prefix=f"{API_PREFIX}/importacao", tags=["Importação PDF"])
app.include_router(importacao_universal_router, prefix=f"{API_PREFIX}/importacao-universal", tags=["Importação Universal"])
app.include_router(atestados_router,      prefix=f"{API_PREFIX}/afastamentos", tags=["Atestados"])
app.include_router(auditoria.router,        prefix=f"{API_PREFIX}/auditoria",   tags=["Auditoria"])


@app.get("/api/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


# REMOVIDO em 06/11, item (a) da Carolina: o endpoint GET /api/debug/db.
#
# Ele respondia sem autenticacao e entregava host, porta, nome do banco, usuario do banco,
# versao do Postgres e se o papel era superuser/bypassrls — e, em caso de falha, o erro de
# conexao cru. Nas palavras dela: "entregar a configuracao do banco com papel de superusuario
# e convite".
#
# A informacao de diagnostico NAO se perdeu: a mesma checagem de papel roda na partida, em
# _checar_papel_rls(), e vai para o log do servico, onde so quem tem acesso ao projeto le.
# Para conferir sob demanda, use o log da partida ou psql direto.
