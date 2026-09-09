-- ==============================================================
-- SST ESOCIAL GOV — Migração 010: Dicionário de Rubricas (Etapa 3 do v2, fase 3A-1)
-- Base: PRD/TDD v2 — seção 8. "O cérebro do Módulo de Folha".
-- Regra de reputação: só grau CONSOLIDADO gera achado de crédito com valor exibido.
-- Natureza: ADITIVA — cria tabela + carga inicial das rubricas prioritárias.
-- ==============================================================

CREATE TABLE IF NOT EXISTS dicionario_rubrica (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(60) NOT NULL,
    codigo_esocial VARCHAR(20),
    descricao VARCHAR(300) NOT NULL,
    natureza_juridica VARCHAR(20) NOT NULL,
    tratamento_correto VARCHAR(15) NOT NULL,
    grau_seguranca VARCHAR(15) NOT NULL,
    fundamento TEXT,
    condicao TEXT,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    versao INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_dic_rubrica_slug UNIQUE (slug),
    CONSTRAINT chk_dic_natureza CHECK (natureza_juridica IN ('remuneratoria','indenizatoria','nao_salarial')),
    CONSTRAINT chk_dic_tratamento CHECK (tratamento_correto IN ('incide','nao_incide','condicional')),
    CONSTRAINT chk_dic_grau CHECK (grau_seguranca IN ('consolidado','provavel','controvertido'))
);

CREATE INDEX IF NOT EXISTS idx_dic_rubrica_codigo ON dicionario_rubrica(codigo_esocial);
CREATE INDEX IF NOT EXISTS idx_dic_rubrica_grau ON dicionario_rubrica(grau_seguranca);

COMMENT ON TABLE dicionario_rubrica IS 'SST-ESOCIAL-GOV: dicionario de rubricas (v2 secao 8). fundamento visivel apenas no perfil advogada.';
COMMENT ON COLUMN dicionario_rubrica.grau_seguranca IS 'consolidado gera credito com valor; provavel gera alerta amarelo; controvertido nao gera credito';
COMMENT ON COLUMN dicionario_rubrica.fundamento IS 'Norma e precedente. NUNCA exposto ao cliente comum.';

INSERT INTO dicionario_rubrica (slug, descricao, natureza_juridica, tratamento_correto, grau_seguranca, fundamento)
VALUES
 ('afastamento_15dias',
  'Primeiros 15 dias de afastamento por incapacidade',
  'indenizatoria', 'nao_incide', 'consolidado',
  'STJ, REsp 1.230.957/RS (Tema 478) — nao incide contribuicao previdenciaria sobre os 15 primeiros dias.'),
 ('salario_maternidade',
  'Salario-maternidade',
  'indenizatoria', 'nao_incide', 'consolidado',
  'STF, RE 576.967 (Tema 72) — inconstitucional a incidencia sobre o salario-maternidade.'),
 ('aviso_previo_indenizado',
  'Aviso previo indenizado',
  'indenizatoria', 'nao_incide', 'consolidado',
  'STJ, REsp 1.230.957/RS (Tema 478) — nao incide contribuicao sobre o aviso previo indenizado.'),
 ('vale_transporte',
  'Vale-transporte, inclusive quando pago em pecunia',
  'nao_salarial', 'nao_incide', 'consolidado',
  'STF, RE 478.410 — nao incide contribuicao sobre o vale-transporte, ainda que pago em dinheiro.')
ON CONFLICT (slug) DO NOTHING;
