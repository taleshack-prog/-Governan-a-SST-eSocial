-- 026_empresa_fap_cprb.sql
-- FAP por ano da empresa (RF-0.135) + CPRB como periodo (RF-0.136).
-- FAP: 0,5 a 2,0, uma linha por ano. Numeric(5,4) p/ nao truncar (ex.: 1,2341).
-- CPRB: deixa de ser checkbox e vira periodo (inicio/fim) — uma adesao vale por periodo.
-- Natureza: ADITIVA. Idempotente.

CREATE TABLE IF NOT EXISTS empresa_fap (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    ano         SMALLINT     NOT NULL,
    indice      NUMERIC(5,4) NOT NULL CHECK (indice BETWEEN 0.5000 AND 2.0000),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_empresa_fap UNIQUE (empresa_id, ano)
);
CREATE INDEX IF NOT EXISTS idx_empresa_fap_empresa ON empresa_fap(empresa_id);

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cprb_inicio DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cprb_fim    DATE;
