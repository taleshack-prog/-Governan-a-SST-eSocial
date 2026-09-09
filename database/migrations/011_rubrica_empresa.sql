-- ==============================================================
-- SST ESOCIAL GOV — Migração 011: Rubricas da Empresa (Etapa 3 do v2, fase 3A-2)
-- Base: PRD/TDD v2 — seção 7 + RN 7.2 (conciliação obrigatória).
-- Natureza: ADITIVA.
-- ==============================================================

CREATE TABLE IF NOT EXISTS rubrica_empresa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    codigo_esocial VARCHAR(20),
    descricao VARCHAR(300) NOT NULL,
    natureza_declarada VARCHAR(30),
    incide_inss_praticado BOOLEAN NOT NULL DEFAULT TRUE,
    incide_fgts_praticado BOOLEAN NOT NULL DEFAULT TRUE,
    valor_mensal NUMERIC(14,2) NOT NULL DEFAULT 0,
    dicionario_rubrica_id UUID REFERENCES dicionario_rubrica(id),
    status_conciliacao VARCHAR(12) NOT NULL DEFAULT 'pendente',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_rubrica_status CHECK (status_conciliacao IN ('pendente','conciliada'))
);

CREATE INDEX IF NOT EXISTS idx_rubrica_empresa_estab ON rubrica_empresa(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_rubrica_empresa_status ON rubrica_empresa(status_conciliacao);
CREATE INDEX IF NOT EXISTS idx_rubrica_empresa_codigo ON rubrica_empresa(codigo_esocial);

COMMENT ON TABLE rubrica_empresa IS 'SST-ESOCIAL-GOV: rubricas como a empresa parametrizou (v2 secao 7). Conciliada com dicionario_rubrica (RN 7.2).';
COMMENT ON COLUMN rubrica_empresa.status_conciliacao IS 'pendente ate casar com o dicionario; conciliada quando vinculada.';
