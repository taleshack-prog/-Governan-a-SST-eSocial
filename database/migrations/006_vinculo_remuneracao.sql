-- ==============================================================
-- SST ESOCIAL GOV — Migração 006: Remuneração de referência no vínculo (Módulo 0, fase 0C)
-- Base: PRD/TDD v2 — RF-0.05. Colocada no vínculo (entidade contratual/temporal),
-- consistente com RN-04. É valor de REFERÊNCIA; o de cálculo vem de competencia_folha (futuro).
-- Natureza: ADITIVA.
-- ==============================================================

ALTER TABLE vinculos ADD COLUMN IF NOT EXISTS remuneracao_base NUMERIC(14,2);

COMMENT ON COLUMN vinculos.remuneracao_base IS 'Remuneracao de referencia informada no cadastro (RF-0.05). NAO e base de calculo: esta vem da folha por competencia (RN-04).';
