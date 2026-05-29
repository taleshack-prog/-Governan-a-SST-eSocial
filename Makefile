# ==============================================================
# SST ESOCIAL GOV — Makefile
# Uso: make <comando>
# ==============================================================

.PHONY: help up down build db-migrate db-seed logs test lint clean

# Cores
CYAN  := \033[0;36m
RESET := \033[0m

help:
	@echo "$(CYAN)SST ESOCIAL GOV — Comandos disponíveis:$(RESET)"
	@echo "  make up          - Sobe todos os containers"
	@echo "  make down        - Para e remove containers"
	@echo "  make build       - (Re)build das imagens"
	@echo "  make db-migrate  - Roda migrations do banco"
	@echo "  make db-seed     - Popula dados iniciais"
	@echo "  make logs        - Exibe logs em tempo real"
	@echo "  make test        - Roda testes (pytest)"
	@echo "  make lint        - Roda linter (ruff)"
	@echo "  make clean       - Remove volumes e containers"
	@echo "  make health      - Verifica saúde da API"

up:
	@echo "$(CYAN)Subindo SST eSocial Gov...$(RESET)"
	docker compose up -d
	@echo "$(CYAN)API disponível em: http://localhost:8001/api/docs$(RESET)"
	@echo "$(CYAN)Frontend em      : http://localhost:3001$(RESET)"

down:
	docker compose down

build:
	docker compose build --no-cache

db-migrate:
	@echo "$(CYAN)Rodando migrations...$(RESET)"
	docker compose exec api alembic upgrade head

db-seed:
	@echo "$(CYAN)Populando dados iniciais...$(RESET)"
	docker compose exec db psql -U $${POSTGRES_USER:-sst_user} -d $${POSTGRES_DB:-sst_esocial_db} -f /docker-entrypoint-initdb.d/seeds/001_base_normativa.sql

logs:
	docker compose logs -f api worker

logs-all:
	docker compose logs -f

test:
	@echo "$(CYAN)Rodando testes...$(RESET)"
	docker compose exec api pytest tests/ -v --asyncio-mode=auto

lint:
	docker compose exec api ruff check api/ ai-layer/

health:
	@curl -s http://localhost:8001/api/health | python3 -m json.tool

clean:
	@echo "$(CYAN)Limpando volumes e containers SST...$(RESET)"
	docker compose down -v
	docker volume rm sst_esocial_postgres_data sst_esocial_redis_data sst_esocial_minio_data 2>/dev/null || true
