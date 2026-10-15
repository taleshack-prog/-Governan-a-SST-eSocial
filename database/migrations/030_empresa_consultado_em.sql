-- 030_empresa_consultado_em.sql
-- RF-0.150 (ajuste): gravar data/hora da consulta de CNPJ junto do cadastro. O retorno da
-- consulta (razao, fantasia, CNAE principal/secundarios, endereco, data de abertura) passa a
-- ser persistido; aqui guardamos QUANDO foi consultado, para a marca "consultado, nao confirmado".
-- Natureza: ADITIVA e idempotente.
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS consultado_em TIMESTAMPTZ;
