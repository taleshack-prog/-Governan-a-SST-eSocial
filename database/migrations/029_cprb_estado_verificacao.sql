-- 029_cprb_estado_verificacao.sql
-- RF-0.163..0.166 — estado explicito de verificacao da CPRB + limites do periodo.
--
-- RF-0.163: o bloco vazio era ambiguo (nao optou vs ninguem verificou). A empresa passa a ter
--   um ESTADO explicito: nao_informado (padrao, vai a conferencia) | nao_optante (marcacao com
--   autor/data, calculo com patronal cheia) | optante (com a lista de periodos).
-- RF-0.164: a exceçao da regra ano-calendario (inicio != janeiro / fim != dezembro) depende da
--   data de abertura/encerramento da empresa — por isso as colunas abaixo.
-- Natureza: ADITIVA e idempotente. Nao mexe em empresa_cprb (periodos) nem na transicao.

-- Estado da verificacao da CPRB (nivel empresa)
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cprb_status VARCHAR(16) NOT NULL DEFAULT 'nao_informado';
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cprb_verificado_por VARCHAR(200);
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS cprb_verificado_em  TIMESTAMPTZ;

-- CHECK do dominio (recria de forma idempotente)
ALTER TABLE empresas DROP CONSTRAINT IF EXISTS ck_empresas_cprb_status;
ALTER TABLE empresas ADD CONSTRAINT ck_empresas_cprb_status
    CHECK (cprb_status IN ('nao_informado', 'nao_optante', 'optante'));

-- Datas de abertura/encerramento da empresa (excecao da regra ano-calendario, RF-0.164)
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_abertura     DATE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_encerramento DATE;

-- Backfill: empresas que ja tinham periodos de CPRB sao, de fato, optantes; as demais ficam
-- no padrao 'nao_informado' (ninguem marcou — vai a conferencia).
UPDATE empresas e SET cprb_status = 'optante'
 WHERE e.cprb_status = 'nao_informado'
   AND EXISTS (SELECT 1 FROM empresa_cprb c WHERE c.empresa_id = e.id);
