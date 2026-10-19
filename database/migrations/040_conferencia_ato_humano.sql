-- 040_conferencia_ato_humano.sql
-- Carolina, 19/10 (segunda rodada do Cadastro), itens 1 e 2: "conferido" passa a ser ATO DE
-- PESSOA, com autor e data gravados, e nao conclusao do calculo.
--
-- O DEFEITO. A maquina de estados tinha, de fato, DOIS estados — com pendencia e sem pendencia
-- — e o rotulo do terceiro foi aplicado ao segundo: o sistema chamava de "conferido" toda
-- competencia em que o aplicado estava informado e a comparacao fechou. Ninguem havia conferido
-- nada. O contador leria "58 conferidas" e um laudo emitido afirmaria que 58 competencias foram
-- conferidas por quem subscreve a peca — e a peca leva a assinatura da advogada, nao a do
-- sistema. Conferir e ato profissional, nao resultado de calculo.
--
-- NAO HA BACKFILL A FAZER, e isso e melhor do que parece. O estado nunca foi gravado: ele era
-- DERIVADO em api/services/enquadramento_situacao.py a cada leitura. Logo a afirmacao falsa
-- vivia na resposta da API e no PDF, nunca no banco. Trocar a regra de derivacao corrige as 58
-- competencias de uma vez e retroativamente, sem tocar em linha nenhuma. O banco nunca afirmou
-- o que a tela afirmava.
--
-- OS TRES ESTADOS, agora com significado proprio:
--   em conferencia — tem pendencia: falta dado, o motor nao concluiu. Derivado.
--   apurado        — o motor calculou ate o fim sem pendencia. Afirmacao do SISTEMA. Derivado.
--   conferido      — uma pessoa examinou e validou. Afirmacao de PESSOA. GRAVADO, com autor e
--                    data. Nada chega aqui sem acao explicita de alguem.
--
-- ITEM 2 — REVOGACAO. Conferir e assinar sobre um numero determinado. Se o numero mudou depois
-- da assinatura, a assinatura nao corresponde mais a nada. Toda alteracao em dado de calculo
-- (atividade, quantitativo, FAP, FPAS, regime, CPRB) reapura a serie e REVOGA a conferencia das
-- competencias afetadas — registrando o que foi revogado, quando e por quem, para que o
-- historico nao se perca junto com o aval.
--
-- Idempotente.
BEGIN;

ALTER TABLE estabelecimento_enquadramento
    -- O ato humano
    ADD COLUMN IF NOT EXISTS conferido_por   VARCHAR(200),
    ADD COLUMN IF NOT EXISTS conferido_em    TIMESTAMPTZ,
    -- O rastro da revogacao, quando o dado de calculo muda sob uma competencia ja conferida
    ADD COLUMN IF NOT EXISTS revogado_em     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revogado_por    VARCHAR(200),
    ADD COLUMN IF NOT EXISTS revogado_de     VARCHAR(200);

COMMENT ON COLUMN estabelecimento_enquadramento.conferido_por IS
    'Quem validou esta competencia. NULL = nao conferida. Nunca preenchido pelo motor: so por '
    'acao explicita de pessoa, pelo endpoint de conferir.';
COMMENT ON COLUMN estabelecimento_enquadramento.revogado_de IS
    'Quem havia conferido antes de a reapuracao revogar. Preserva o rastro do aval que deixou '
    'de valer porque o numero mudou.';

-- Garantia estrutural: nao existe competencia conferida sem autor E data. Um dos dois sozinho
-- seria um aval sem assinatura ou uma assinatura sem data.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_enq_conferido_completo') THEN
        ALTER TABLE estabelecimento_enquadramento
            ADD CONSTRAINT ck_enq_conferido_completo
            CHECK ((conferido_por IS NULL) = (conferido_em IS NULL));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_enq_conferido
    ON estabelecimento_enquadramento (estabelecimento_id, conferido_em)
    WHERE conferido_por IS NOT NULL;

COMMIT;

-- Conferencia depois de aplicar (esperado: 0 conferidas — ninguem conferiu ainda, e e isso
-- que o sistema passa a dizer):
--   SELECT count(*) FILTER (WHERE conferido_por IS NOT NULL) AS conferidas,
--          count(*) FILTER (WHERE conferido_por IS NULL AND NOT em_fila) AS apuradas,
--          count(*) FILTER (WHERE em_fila) AS em_conferencia
--     FROM estabelecimento_enquadramento;
