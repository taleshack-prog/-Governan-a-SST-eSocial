-- ==============================================================
-- SST ESOCIAL GOV — Migração 007: Questionário de configuração (Módulo 0, fase 0D)
-- Base: PRD/TDD v2 — RF-0.06 + RN-03 (imutável e versionado: nova resposta = novo registro).
-- Natureza: ADITIVA — cria tabela nova.
-- ==============================================================

CREATE TABLE IF NOT EXISTS questionario_resposta (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    pergunta_codigo VARCHAR(60) NOT NULL,
    resposta TEXT NOT NULL,
    respondido_por UUID REFERENCES usuarios(id),
    respondido_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questionario_empresa_pergunta
    ON questionario_resposta(empresa_id, pergunta_codigo, respondido_em DESC);

COMMENT ON TABLE questionario_resposta IS 'SST-ESOCIAL-GOV: respostas do questionario de config (RF-0.06). Imutavel/versionado (RN-03): nova resposta cria novo registro, a anterior e mantida. Vigente = mais recente por (empresa, pergunta).';
COMMENT ON COLUMN questionario_resposta.pergunta_codigo IS 'Ex: alimentacao_forma, plr_acordo_previo, plr_frequencia, premios_natureza, possui_terceirizados';
