-- 023_empresa_endereco.sql
-- Adiciona endereco a empresa (matriz). Espelha os campos do estabelecimento
-- (endereco/cidade/uf) + cep. Nao fazia sentido a filial ter endereco e a matriz nao.
-- Natureza: ADITIVA. Idempotente (ADD COLUMN IF NOT EXISTS).

ALTER TABLE empresas ADD COLUMN IF NOT EXISTS endereco VARCHAR(500);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cidade   VARCHAR(100);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS uf       VARCHAR(2);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cep      VARCHAR(9);
