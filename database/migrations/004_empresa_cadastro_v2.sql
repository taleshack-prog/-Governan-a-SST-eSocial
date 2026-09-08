-- ==============================================================
-- SST ESOCIAL GOV — Migração 004: Cadastro de Empresa completo (Módulo 0, fase 0A)
-- Arquivo: database/migrations/004_empresa_cadastro_v2.sql
-- Base: PRD/TDD v2 — RF-0.01. Natureza: ADITIVA — nada é removido.
-- ==============================================================

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS codigo_fpas VARCHAR(4);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS anexo_simples VARCHAR(10);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS apura_cprb BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS grau_risco_declarado SMALLINT;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS rat_aplicado NUMERIC(4,2);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS possui_sesmt BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS possui_cipa BOOLEAN NOT NULL DEFAULT FALSE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_empresa_grau_risco_decl') THEN
        ALTER TABLE empresas ADD CONSTRAINT chk_empresa_grau_risco_decl
            CHECK (grau_risco_declarado IS NULL OR grau_risco_declarado IN (1, 2, 3));
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS empresa_cnae_secundario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cnae VARCHAR(7) NOT NULL,
    CONSTRAINT uq_empresa_cnae_sec UNIQUE (empresa_id, cnae)
);

CREATE INDEX IF NOT EXISTS idx_empresa_cnae_sec_empresa ON empresa_cnae_secundario(empresa_id);

COMMENT ON COLUMN empresas.rat_aplicado IS 'RAT que a empresa DECLARA aplicar hoje; o RAT de calculo vive no estabelecimento (Alteracao 1)';
COMMENT ON COLUMN empresas.codigo_fpas IS 'Codigo FPAS: define composicao de Terceiros';
COMMENT ON TABLE empresa_cnae_secundario IS 'SST-ESOCIAL-GOV: CNAEs secundarios da empresa (RF-0.01)';
