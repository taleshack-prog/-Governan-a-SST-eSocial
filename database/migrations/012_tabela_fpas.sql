-- ==============================================================
-- SST ESOCIAL GOV — Migração 012: Tabela FPAS (Etapa 3 do v2, fase 3A-2b)
-- Fonte oficial: IN RFB nº 971/2009, Anexo II.
-- Carga inicial = codigos CONFIRMADOS; tabela pronta para carga completa.
-- Natureza: ADITIVA.
-- ==============================================================

CREATE TABLE IF NOT EXISTS tabela_fpas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_fpas VARCHAR(4) NOT NULL,
    descricao VARCHAR(300) NOT NULL,
    aliquota_terceiros NUMERIC(4,2) NOT NULL,
    codigo_terceiros VARCHAR(4),
    fonte VARCHAR(120) NOT NULL DEFAULT 'IN RFB 971/2009 Anexo II',
    confirmado BOOLEAN NOT NULL DEFAULT TRUE,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_fpas_codigo UNIQUE (codigo_fpas)
);

CREATE INDEX IF NOT EXISTS idx_tabela_fpas_codigo ON tabela_fpas(codigo_fpas);

COMMENT ON TABLE tabela_fpas IS 'SST-ESOCIAL-GOV: aliquotas de Terceiros por codigo FPAS. Fonte: IN RFB 971/2009 Anexo II.';
COMMENT ON COLUMN tabela_fpas.aliquota_terceiros IS 'Percentual de Terceiros. Usado no calculo de credito/passivo.';

INSERT INTO tabela_fpas (codigo_fpas, descricao, aliquota_terceiros, codigo_terceiros, confirmado)
VALUES
 ('507', 'Industria (regra geral) — comercio e industria',  5.80, '0079', TRUE),
 ('515', 'Comercio (empregador urbano em geral / comercio)', 5.80, '0115', TRUE),
 ('604', 'Produtor rural pessoa juridica',                   2.50, '0001', TRUE)
ON CONFLICT (codigo_fpas) DO NOTHING;
