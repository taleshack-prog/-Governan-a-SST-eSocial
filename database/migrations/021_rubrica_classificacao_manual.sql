-- 021_rubrica_classificacao_manual.sql
-- Fila de classificacao manual das rubricas Caixa 3 (condicional).
-- A decisao do tecnico/advogada (incide|nao_incide) grava na propria rubrica_empresa.
-- Natureza: ADITIVA.

ALTER TABLE rubrica_empresa
  ADD COLUMN IF NOT EXISTS classificacao_manual VARCHAR(12),
  ADD COLUMN IF NOT EXISTS classificado_por VARCHAR(160),
  ADD COLUMN IF NOT EXISTS classificado_em TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS justificativa_classificacao TEXT;

DO $$ BEGIN
  ALTER TABLE rubrica_empresa
    ADD CONSTRAINT chk_classificacao_manual
    CHECK (classificacao_manual IS NULL OR classificacao_manual IN ('incide','nao_incide'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_rubrica_empresa_classif ON rubrica_empresa(classificacao_manual);

COMMENT ON COLUMN rubrica_empresa.classificacao_manual IS 'Decisao manual p/ rubricas condicionais (Caixa 3): incide|nao_incide. NULL = pendente na fila.';
