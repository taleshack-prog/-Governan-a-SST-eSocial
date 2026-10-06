-- 027_adendo03_tela_empresa.sql
-- Adendo 03: o enquadramento pertence ao ESTABELECIMENTO, nao a empresa (RN-17;
-- Dec. 3.048/99 art. 202 par. 3/3-A; Sumula 351 STJ). Estrutura correta desde ja:
-- enquadramento como tabela filha POR VIGENCIA (nao plana); regime e CPRB por periodo;
-- transicao da CPRB versionada; empresa ganha periodo de apuracao e origem.
-- Natureza: ADITIVA, com DROP da empresa_fap (criada na 026 no lugar errado; FAP e do
-- estabelecimento — estabelecimento_fap ja existe). Idempotente.

-- 1) Enquadramento do estabelecimento POR VIGENCIA (RN-17 / nao deixar plano)
CREATE TABLE IF NOT EXISTS estabelecimento_enquadramento (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    vigencia_inicio    DATE NOT NULL,
    vigencia_fim       DATE,                         -- NULL = em aberto
    cnae               CHAR(7),
    atividade_preponderante TEXT,
    grau_risco         SMALLINT CHECK (grau_risco BETWEEN 1 AND 3),
    aliquota_rat       NUMERIC(3,2),
    codigo_fpas        VARCHAR(4),
    codigo_terceiros   VARCHAR(4),
    -- fundamentacao propagada (RN-18) — preenchida quando as tabelas da Fase 1 existirem
    fund_dispositivo   VARCHAR(200),
    fund_ato_normativo VARCHAR(200),
    fund_anexo         VARCHAR(80),
    fund_vigencia      VARCHAR(80),
    origem             VARCHAR(16) NOT NULL DEFAULT 'declarado',  -- consultado | declarado | manual
    confirmado         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_estab_enq_estab ON estabelecimento_enquadramento(estabelecimento_id);

-- 2) empresa: periodo de apuracao (RF-0.151) + origem do cadastro (RF-0.150)
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS periodo_apuracao_inicio DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS periodo_apuracao_fim    DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS origem_cadastro         VARCHAR(16);  -- consultado | declarado
-- CNAE deixa de ser obrigatorio na empresa (migra para o estabelecimento)
ALTER TABLE empresas ALTER COLUMN cnae_principal DROP NOT NULL;

-- 3) Regime tributario por periodo (RF-0.156)
CREATE TABLE IF NOT EXISTS empresa_regime (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id    UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    regime        VARCHAR(30) NOT NULL,              -- lucro_real | lucro_presumido | simples
    anexo_simples VARCHAR(10),
    inicio        DATE NOT NULL,
    fim           DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_empresa_regime_emp ON empresa_regime(empresa_id);

-- 4) CPRB por periodo (RF-0.157) — opcao anual, a empresa entra e sai
CREATE TABLE IF NOT EXISTS empresa_cprb (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    inicio     DATE NOT NULL,
    fim        DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_empresa_cprb_emp ON empresa_cprb(empresa_id);

-- 5) Transicao da CPRB, VERSIONADA (RF-0.158 / RN-18) — seed da tabela 4.4 do Adendo 03.
--    patronal_folha_pct = % da cota patronal devida sobre a folha (ex.: 2025 => 5% = 25% de 20%).
--    cprb_receita_pct   = % da aliquota da CPRB sobre a receita (NULL em 2028 = extinta).
--    [A CONFIRMAR B.1]: nao incidencia sobre 13o na transicao — nao implementado aqui.
CREATE TABLE IF NOT EXISTS cprb_transicao (
    ano_inicio         SMALLINT PRIMARY KEY,
    ano_fim            SMALLINT,                      -- NULL = em diante
    cprb_receita_pct   NUMERIC(5,2),
    patronal_folha_pct NUMERIC(5,2) NOT NULL,
    substitui_integral BOOLEAN NOT NULL,              -- true ate 2024
    fonte              VARCHAR(120) NOT NULL DEFAULT 'Lei 12.546/2011; transicao Lei 14.973/2024'
);
INSERT INTO cprb_transicao (ano_inicio, ano_fim, cprb_receita_pct, patronal_folha_pct, substitui_integral) VALUES
 (2011, 2024, 100.00, 0.00,  TRUE),
 (2025, 2025, 80.00,  5.00,  FALSE),
 (2026, 2026, 60.00,  10.00, FALSE),
 (2027, 2027, 40.00,  15.00, FALSE),
 (2028, NULL, NULL,   20.00, FALSE)
ON CONFLICT (ano_inicio) DO NOTHING;

-- 6) FAP e do estabelecimento (RF-0.154). A empresa_fap da 026 estava errada; so havia
--    dado de teste. Removida.
DROP TABLE IF EXISTS empresa_fap;
