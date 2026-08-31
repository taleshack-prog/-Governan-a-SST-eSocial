-- ==============================================================
-- SST ESOCIAL GOV — Migração 003: Custeio por Estabelecimento (Alteração 1, fase 1A)
-- Arquivo: database/migrations/003_estabelecimento_custeio.sql
-- Natureza: ADITIVA — apenas adiciona colunas e uma tabela nova. Nada é removido.
-- Auditoria da tabela nova fica em database/triggers/audit_trigger.sql (ordem correta).
-- ==============================================================

-- ---- 1) Novos campos no estabelecimento (parametrização fiscal por CNPJ) ----
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS tipo VARCHAR(10) NOT NULL DEFAULT 'filial';
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS cnae_secundarios TEXT;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS grau_risco SMALLINT;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS aliquota_rat NUMERIC(4,2);
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS fpas VARCHAR(4);
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS num_empregados INTEGER NOT NULL DEFAULT 0;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS folha_mensal NUMERIC(14,2) NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_estab_grau_risco') THEN
        ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_grau_risco
            CHECK (grau_risco IS NULL OR grau_risco IN (1, 2, 3));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_estab_tipo') THEN
        ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_tipo
            CHECK (tipo IN ('matriz', 'filial'));
    END IF;
END$$;

-- ---- 2) Histórico anual do FAP (TDD 7.2: nunca sobrescrito, um por ano) ----
CREATE TABLE IF NOT EXISTS estabelecimento_fap (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    ano_vigencia SMALLINT NOT NULL,
    valor_fap NUMERIC(3,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_estab_fap_ano UNIQUE (estabelecimento_id, ano_vigencia),
    CONSTRAINT chk_fap_faixa CHECK (valor_fap >= 0.50 AND valor_fap <= 2.00)
);

-- ---- 3) Índices ----
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_empresa ON estabelecimentos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_tipo ON estabelecimentos(tipo);
CREATE INDEX IF NOT EXISTS idx_estab_fap_estab ON estabelecimento_fap(estabelecimento_id);

-- ---- 4) Comentários ----
COMMENT ON COLUMN estabelecimentos.tipo IS 'matriz | filial — sede vs unidades';
COMMENT ON COLUMN estabelecimentos.aliquota_rat IS 'RAT base (1/2/3%). RAT efetivo = aliquota_rat * FAP do ano, calculado em runtime';
COMMENT ON TABLE estabelecimento_fap IS 'SST-ESOCIAL-GOV: FAP por ano de vigencia (0.5-2.0), historico imutavel';
