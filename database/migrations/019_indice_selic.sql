-- ==============================================================
-- SST ESOCIAL GOV — Migração 019: Índice SELIC mensal (correção de crédito)
-- Base: roteiro Carolina, Módulo 2 Camada 3 — "Atualização pela SELIC".
-- Fonte oficial: BCB SGS série 4390 (SELIC acumulada no mês). Tabela local como fonte
-- primária (funciona offline); atualizada por task via API do Banco Central.
-- Regra Receita (art. 39 §4 Lei 9.250/95): SELIC acumulada do mês seguinte ao pagamento
-- até o mês anterior à restituição, + 1% no mês da restituição.
-- Natureza: ADITIVA.
-- ==============================================================

CREATE TABLE IF NOT EXISTS indice_selic (
    competencia DATE PRIMARY KEY,             -- 1o dia do mes
    taxa_mensal NUMERIC(8,4) NOT NULL,        -- % daquele mes (serie 4390)
    fonte VARCHAR(50) DEFAULT 'BCB SGS 4390',
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_selic_competencia ON indice_selic(competencia);

COMMENT ON TABLE indice_selic IS 'SELIC acumulada mensal (BCB serie 4390) para correcao de credito previdenciario. Roteiro Modulo 2 Camada 3.';
