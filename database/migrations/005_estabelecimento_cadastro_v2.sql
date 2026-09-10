-- ==============================================================
-- SST ESOCIAL GOV — Migração 005: Cadastro de Estabelecimento completo (Módulo 0, fase 0B)
-- Base: PRD/TDD v2 — RF-0.03. Reconcilia 1A (matriz/filial) com v2 (CNPJ/CNO).
-- Natureza: RENAME (preserva dados) + ADITIVA. Nada é removido.
-- ==============================================================

-- RENAMEs idempotentes: só renomeiam se o nome antigo ainda existir.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='estabelecimentos' AND column_name='tipo')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='estabelecimentos' AND column_name='posicao') THEN
        ALTER TABLE estabelecimentos RENAME COLUMN tipo TO posicao;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_estab_tipo')
       AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_estab_posicao') THEN
        ALTER TABLE estabelecimentos RENAME CONSTRAINT chk_estab_tipo TO chk_estab_posicao;
    END IF;
END$$;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname='idx_estabelecimentos_tipo')
       AND NOT EXISTS (SELECT 1 FROM pg_class WHERE relname='idx_estabelecimentos_posicao') THEN
        ALTER INDEX idx_estabelecimentos_tipo RENAME TO idx_estabelecimentos_posicao;
    END IF;
END$$;

ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS tipo_estabelecimento VARCHAR(4) NOT NULL DEFAULT 'CNPJ';
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS atividade_descrita TEXT;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS status VARCHAR(12) NOT NULL DEFAULT 'ativa';
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS data_inicio DATE;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS data_prevista_conclusao DATE;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS identificador VARCHAR(20);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_estab_tipo_estab') THEN
        ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_tipo_estab
            CHECK (tipo_estabelecimento IN ('CNPJ', 'CNO'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_estab_status') THEN
        ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_status
            CHECK (status IN ('ativa', 'paralisada', 'encerrada'));
    END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_estabelecimentos_tipo_estab ON estabelecimentos(tipo_estabelecimento);
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_status ON estabelecimentos(status);

COMMENT ON COLUMN estabelecimentos.posicao IS 'matriz | filial — hierarquia (origem: Alteracao 1)';
COMMENT ON COLUMN estabelecimentos.tipo_estabelecimento IS 'CNPJ | CNO — natureza do estabelecimento (RF-0.03 v2)';
COMMENT ON COLUMN estabelecimentos.status IS 'ativa | paralisada | encerrada. Encerrada nao some (RN-05)';
COMMENT ON COLUMN estabelecimentos.atividade_descrita IS 'Descricao livre da atividade real; insumo do RF-0.04';
