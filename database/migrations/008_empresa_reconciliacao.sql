-- ==============================================================
-- SST ESOCIAL GOV — Migração 008: Reconciliação model↔banco da tabela empresas
-- Motivo: o model Empresa tem campos (plano, limites, contatos) que nunca entraram
--         no banco via migration. Sem eles, qualquer SELECT via ORM em Empresa quebra.
-- Natureza: ADITIVA — adiciona as colunas faltantes com os mesmos defaults do model.
-- ==============================================================

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS plano VARCHAR(20) DEFAULT 'trial';
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS plano_expira_em DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS max_trabalhadores INTEGER DEFAULT 10;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS contato_nome VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS contato_email VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS contato_telefone VARCHAR(20);

COMMENT ON COLUMN empresas.plano IS 'Plano comercial (trial por padrao). Reconciliado do model em 008.';
