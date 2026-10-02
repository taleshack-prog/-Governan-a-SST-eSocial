-- 025_empresa_endereco_detalhe.sql
-- Detalha o endereco da empresa: bairro, numero e complemento (o CEP busca logradouro/
-- bairro/cidade/uf via ViaCEP no navegador; o usuario preenche so numero e complemento).
-- Natureza: ADITIVA. Idempotente (ADD COLUMN IF NOT EXISTS).

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS bairro      VARCHAR(120);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS numero      VARCHAR(20);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS complemento VARCHAR(120);
