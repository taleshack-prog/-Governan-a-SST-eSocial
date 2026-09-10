-- ==============================================================
-- SST ESOCIAL GOV — Migração 015: Memória de cálculo da prescrição (Etapa 4, fase 4A)
-- Base: v2 seção 10 (Régua de prescrição). Requisito de auditoria: composição por
-- competência — "sem memória de cálculo, o achado não serve como prova".
-- Natureza: ADITIVA.
-- ==============================================================

CREATE TABLE IF NOT EXISTS memoria_calculo_prescricao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    achado_id UUID NOT NULL REFERENCES achado(id) ON DELETE CASCADE,
    competencia DATE NOT NULL,
    valor_competencia NUMERIC(14,2) NOT NULL,
    dentro_janela BOOLEAN NOT NULL DEFAULT TRUE,
    data_referencia DATE NOT NULL,
    calculado_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_memoria_achado_comp UNIQUE (achado_id, competencia, data_referencia)
);

CREATE INDEX IF NOT EXISTS idx_memoria_achado ON memoria_calculo_prescricao(achado_id);
CREATE INDEX IF NOT EXISTS idx_memoria_competencia ON memoria_calculo_prescricao(competencia);

COMMENT ON TABLE memoria_calculo_prescricao IS 'SST-ESOCIAL-GOV: memoria de calculo da prescricao (v2 secao 10). Composicao por competencia.';
