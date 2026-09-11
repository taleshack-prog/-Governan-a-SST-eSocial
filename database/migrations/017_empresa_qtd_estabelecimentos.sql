-- ==============================================================
-- SST ESOCIAL GOV — Migração 017: Quantidade de estabelecimentos na empresa
-- Base: roteiro Carolina, Módulo 0 Nível 1 — "Quantidade de estabelecimentos: abre o nível 2".
-- Campo declaratório: a empresa informa quantas unidades tem (matriz + filiais/obras).
-- Natureza: ADITIVA.
-- ==============================================================

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS qtd_estabelecimentos INTEGER;

COMMENT ON COLUMN empresas.qtd_estabelecimentos IS 'Quantidade declarada de estabelecimentos (matriz + filiais/obras). Roteiro Modulo 0 Nivel 1.';
