#!/bin/bash
# ==============================================================
# SST ESOCIAL GOV — Migrador manual controlado
# Aplica os .sql na ordem (migrations -> triggers -> seeds), registrando o que já
# rodou em schema_migrations. Idempotente e seguro para produção.
# Uso local:   ./scripts/run_migrations.sh
# Uso Railway: DATABASE_URL_SYNC="postgresql://..." ./scripts/run_migrations.sh
# ==============================================================
set -euo pipefail

if [ -n "${DATABASE_URL_SYNC:-}" ]; then
    CONN="$DATABASE_URL_SYNC"
elif [ -n "${DATABASE_URL:-}" ]; then
    CONN="$(echo "$DATABASE_URL" | sed 's#postgresql+asyncpg://#postgresql://#')"
else
    : "${POSTGRES_USER:?defina DATABASE_URL_SYNC ou POSTGRES_USER}"
    : "${POSTGRES_PASSWORD:?defina POSTGRES_PASSWORD}"
    HOST="${POSTGRES_HOST:-localhost}"; PORT="${POSTGRES_PORT:-5432}"; DB="${POSTGRES_DB:-sst_esocial_db}"
    CONN="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${HOST}:${PORT}/${DB}"
fi

PSQL="psql $CONN -v ON_ERROR_STOP=1 -q"

echo "==> Garantindo tabela de controle schema_migrations"
$PSQL <<'SQL'
CREATE TABLE IF NOT EXISTS schema_migrations (
    arquivo   VARCHAR(200) PRIMARY KEY,
    categoria VARCHAR(20)  NOT NULL,
    aplicado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SQL

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

aplicar_dir() {
    local dir="$1" categoria="$2"
    local caminho="$BASE_DIR/database/$dir"
    [ -d "$caminho" ] || { echo "   (pasta $dir ausente, pulando)"; return; }
    for f in $(ls "$caminho"/*.sql 2>/dev/null | sort); do
        local nome; nome="$(basename "$f")"
        local ja; ja=$($PSQL -tA -c "SELECT 1 FROM schema_migrations WHERE arquivo = '$nome'") || ja=""
        if [ "$ja" = "1" ]; then
            echo "   [skip] $categoria/$nome (já aplicado)"; continue
        fi
        echo "   [aplicando] $categoria/$nome"
        $PSQL -f "$f"
        $PSQL -c "INSERT INTO schema_migrations (arquivo, categoria) VALUES ('$nome', '$categoria')"
    done
}

echo "==> 1/3 Migrations"; aplicar_dir "migrations" "migration"
echo "==> 2/3 Triggers";   aplicar_dir "triggers" "trigger"
echo "==> 3/3 Seeds";      aplicar_dir "seeds" "seed"

echo ""
echo "==> Estado atual:"
$PSQL -c "SELECT categoria, count(*) FROM schema_migrations GROUP BY categoria ORDER BY categoria;"
echo "==> Migração concluída."
