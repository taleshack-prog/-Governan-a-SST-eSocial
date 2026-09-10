-- ==============================================================
-- SST ESOCIAL GOV — Migração 016: Enriquecimento de alertas (Alteração 4)
-- Base: v2 seção 11 (estrutura do alerta) + 11.1 (mapeamento por gatilho).
-- Completa o achado: tipo_valor, data_limite, acao_sugerida, fundamento_interno.
-- Natureza: ADITIVA.
-- ==============================================================

ALTER TABLE achado ADD COLUMN IF NOT EXISTS tipo_valor VARCHAR(12);
ALTER TABLE achado ADD COLUMN IF NOT EXISTS data_limite DATE;
ALTER TABLE achado ADD COLUMN IF NOT EXISTS acao_sugerida VARCHAR(200);
ALTER TABLE achado ADD COLUMN IF NOT EXISTS fundamento_interno TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_achado_tipo_valor') THEN
        ALTER TABLE achado ADD CONSTRAINT chk_achado_tipo_valor
            CHECK (tipo_valor IS NULL OR tipo_valor IN ('exposicao','recuperacao'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='chk_achado_esfera') THEN
        ALTER TABLE achado ADD CONSTRAINT chk_achado_esfera
            CHECK (esfera IS NULL OR esfera IN ('consultivo','administrativo','judicial'));
    END IF;
END$$;

COMMENT ON COLUMN achado.tipo_valor IS 'exposicao (passivo) | recuperacao (credito) — v2 secao 11';
COMMENT ON COLUMN achado.fundamento_interno IS 'Fundamento tecnico-juridico. NUNCA exposto ao cliente comum — so perfil advogada.';
