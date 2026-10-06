-- 028_adendo04_estrutura.sql
-- Adendo 04 (Estabelecimentos) — FASE 1: estrutura (secao 7). A ordem manda: estrutura antes
-- da interface. O grau de risco e CONSEQUENCIA da atividade preponderante (RN-20), apurada
-- por competencia (RN-21). Entradas: atividades com quantitativo (por periodo) e FAP/ano e
-- RAT aplicado (por periodo). Saida: enquadramento apurado, uma linha por competencia.
-- Natureza: ADITIVA + reestrutura a estabelecimento_enquadramento (so dado de teste). Idempotente.

-- 1) estabelecimento: natureza CAEPF (RF-0.171), posicao obra, datas de abertura/encerramento (RF-0.172)
ALTER TABLE estabelecimentos ALTER COLUMN tipo_estabelecimento TYPE VARCHAR(6);
ALTER TABLE estabelecimentos DROP CONSTRAINT IF EXISTS chk_estab_tipo_estab;
ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_tipo_estab
    CHECK (tipo_estabelecimento IN ('CNPJ', 'CNO', 'CAEPF'));
ALTER TABLE estabelecimentos DROP CONSTRAINT IF EXISTS chk_estab_posicao;
ALTER TABLE estabelecimentos ADD CONSTRAINT chk_estab_posicao
    CHECK (posicao IN ('matriz', 'filial', 'obra'));
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS data_abertura     DATE;
ALTER TABLE estabelecimentos ADD COLUMN IF NOT EXISTS data_encerramento DATE;

-- 2) FAP por estabelecimento/ano: origem + data; precisao 4 casas (RF-0.177). Campo vazio != 1,0.
ALTER TABLE estabelecimento_fap ALTER COLUMN valor_fap TYPE NUMERIC(5,4);
ALTER TABLE estabelecimento_fap DROP CONSTRAINT IF EXISTS chk_fap_faixa;
ALTER TABLE estabelecimento_fap ADD CONSTRAINT chk_fap_faixa CHECK (valor_fap >= 0.5000 AND valor_fap <= 2.0000);
ALTER TABLE estabelecimento_fap ADD COLUMN IF NOT EXISTS origem       VARCHAR(16);
ALTER TABLE estabelecimento_fap ADD COLUMN IF NOT EXISTS declarado_em TIMESTAMPTZ;

-- 3) Lista de atividades declaradas (INPUT) — secao 2.1 / RF-0.173. Quantitativo por periodo.
CREATE TABLE IF NOT EXISTS estabelecimento_atividade (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    cnae               CHAR(7) NOT NULL,
    descricao          TEXT,
    quantitativo       INTEGER,                  -- segurados empregados + avulsos; NULL = nao declarado
    vigencia_inicio    DATE NOT NULL,
    vigencia_fim       DATE,                     -- NULL = em aberto
    declarado_por      VARCHAR(160),
    declarado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_estab_ativ_estab ON estabelecimento_atividade(estabelecimento_id);

-- 4) RAT aplicado pela empresa por periodo (INPUT) — RF-0.179, separado do devido.
CREATE TABLE IF NOT EXISTS estabelecimento_rat_aplicado (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    aliquota           NUMERIC(4,2) NOT NULL,
    inicio             DATE NOT NULL,
    fim                DATE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_estab_ratap_estab ON estabelecimento_rat_aplicado(estabelecimento_id);

-- 5) Enquadramento APURADO (OUTPUT), uma linha por competencia — secao 7 / RN-21.
--    A estrutura da 027 era declarativa; aqui vira o resultado do motor. Recriada.
DROP TABLE IF EXISTS estabelecimento_enquadramento;
CREATE TABLE estabelecimento_enquadramento (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    competencia        DATE NOT NULL,                 -- 1o dia do mes
    cnae_preponderante CHAR(7),
    criterio           VARCHAR(24),                   -- maior_quantitativo | desempate_grau | fila_conferencia
    grau_risco         SMALLINT CHECK (grau_risco IS NULL OR grau_risco BETWEEN 1 AND 3),
    aliquota_devida    NUMERIC(4,2),                  -- grau convertido (1/2/3 %)
    fap                NUMERIC(5,4),
    aliquota_efetiva   NUMERIC(6,4),                  -- devida x FAP
    aliquota_aplicada  NUMERIC(4,2),                  -- o que a empresa aplicou (do rat_aplicado)
    em_fila            BOOLEAN NOT NULL DEFAULT FALSE, -- CNO, CNAE sem Anexo I, FAP vazio (RF-0.182/0.177)
    motivo_fila        VARCHAR(200),
    -- fundamentacao propagada (RN-18)
    fund_dispositivo   VARCHAR(200),
    fund_ato_normativo VARCHAR(200),
    fund_anexo         VARCHAR(80),
    fund_vigencia      VARCHAR(80),
    data_apuracao      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    versao_tabelas     VARCHAR(80),
    CONSTRAINT uq_estab_enq_comp UNIQUE (estabelecimento_id, competencia)
);
CREATE INDEX IF NOT EXISTS idx_estab_enq_estab ON estabelecimento_enquadramento(estabelecimento_id);
