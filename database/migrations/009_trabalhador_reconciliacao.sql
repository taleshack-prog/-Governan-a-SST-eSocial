-- ==============================================================
-- SST ESOCIAL GOV — Migração 009: Reconciliação model↔banco da tabela trabalhadores
-- Motivo: o model Trabalhador tem cargo/setor/matricula/data_admissao/ges que
--         nunca entraram no banco. Sem eles, SELECT via ORM em Trabalhador quebra.
-- Natureza: ADITIVA.
-- ==============================================================

ALTER TABLE trabalhadores ADD COLUMN IF NOT EXISTS cargo VARCHAR(200);
ALTER TABLE trabalhadores ADD COLUMN IF NOT EXISTS setor VARCHAR(200);
ALTER TABLE trabalhadores ADD COLUMN IF NOT EXISTS matricula VARCHAR(50);
ALTER TABLE trabalhadores ADD COLUMN IF NOT EXISTS data_admissao DATE;
ALTER TABLE trabalhadores ADD COLUMN IF NOT EXISTS ges VARCHAR(20);

COMMENT ON COLUMN trabalhadores.ges IS 'Grupo de Exposicao Similar. Reconciliado do model em 009.';
