-- 038_tabela_fpas_versionada.sql
-- Carolina, 18/10 (Terceiros e FPAS), item 1: a tabela de aliquotas por codigo FPAS ganha a
-- DIMENSAO DE TEMPO. A chave deixa de ser o codigo e passa a ser o codigo MAIS o periodo.
--
-- O DEFEITO QUE ISTO FECHA. O Radar analisa sessenta competencias. Uma tabela sem vigencia
-- aplica a aliquota de HOJE a todo o passado e erra todos os meses em que a aliquota era outra
-- — e erra SEM EMITIR ERRO, porque o calculo conclui normalmente e devolve um numero. Numero
-- errado com aparencia de numero certo e o pior defeito possivel num laudo.
--
-- E MAIS: mesmo onde duas vigencias tenham valores IDENTICOS, as duas precisam existir
-- separadas, porque o laudo cita o FUNDAMENTO e o fundamento muda. Um documento que apure a
-- competencia de 03/2022 citando a IN RFB 2.110/2022 afirma que estava em vigor uma norma que
-- ainda nao existia — afirmacao falsa em peca lida por autoridade fiscal.
--
-- AS TRES VIGENCIAS NA JANELA DE APURACAO (levantamento da Carolina):
--   IN RFB 971/2009              ate a vigencia da IN RFB 2.110/2022
--   IN RFB 2.110/2022, Anexo III ate 31/03/2026
--   IN RFB 2.321/2026            de 01/04/2026 em diante
--
-- ATENCAO A DATA DE CORTE DA TERCEIRA: e 1º de ABRIL de 2026, NAO a data de publicacao
-- (14/04/2026). A norma saiu no meio do mes e vale desde o primeiro dia dele, de modo que a
-- competencia de abril de 2026 JA se apura pela tabela nova.
--
-- ESTA MIGRATION NAO CARREGA ALIQUOTA NOVA. Ela constroi a estrutura e datilografa o que ja
-- existe. As aliquotas das outras duas vigencias chegam em CSV da curadoria e entram pelo
-- loader scripts/carregar_tabela_fpas.py, que substitui o bloco de um ato normativo inteiro.
-- A estrutura se constroi vazia: se ela esperasse pela curadoria, a curadoria passaria a
-- esperar pela estrutura.
--
-- ALCANCE (RN-18 do Adendo 03 / RN-26 do Adendo 05): o mesmo tratamento vale para TODA tabela
-- normativa, nao so para esta. O problema reaparece nas aliquotas da CPRB (legislacao mudou
-- tres vezes em cinco anos — a 035 ja versionou a fundamentacao, falta a aliquota) e na
-- tabela-ponte entre versoes da CNAE. Regra juridica e dado versionado, nunca valor fixo
-- no codigo.
--
-- Idempotente.
BEGIN;

-- ---- 1) Dimensao de tempo ----
ALTER TABLE tabela_fpas
    ADD COLUMN IF NOT EXISTS vigencia_inicio DATE,
    ADD COLUMN IF NOT EXISTS vigencia_fim    DATE;

-- Backfill: as 25 linhas existentes vieram do Anexo III da IN RFB 2.110/2022 (a 013 registrou
-- isso na coluna 'fonte'). Recebem a vigencia dessa norma, fechada em 31/03/2026 pelo corte da
-- IN 2.321/2026. A data de INICIO abaixo acompanha a que a 035 ja usou para a fundamentacao do
-- FPAS; o CSV da curadoria e a fonte definitiva e o loader corrige o bloco inteiro se divergir.
UPDATE tabela_fpas
   SET vigencia_inicio = COALESCE(vigencia_inicio, DATE '2022-10-17'),
       vigencia_fim    = COALESCE(vigencia_fim,    DATE '2026-03-31')
 WHERE vigencia_inicio IS NULL;

ALTER TABLE tabela_fpas ALTER COLUMN vigencia_inicio SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_fpas_vigencia_ordem') THEN
        ALTER TABLE tabela_fpas
            ADD CONSTRAINT ck_fpas_vigencia_ordem
            CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio);
    END IF;
END $$;

-- ---- 2) A chave passa a ser codigo + periodo ----
-- O unique global do codigo e exatamente o que impedia duas vigencias coexistirem.
DO $$
DECLARE
    c TEXT;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'tabela_fpas'::regclass
           AND contype = 'u'
           AND pg_get_constraintdef(oid) = 'UNIQUE (codigo_fpas)'
    LOOP
        EXECUTE format('ALTER TABLE tabela_fpas DROP CONSTRAINT %I', c);
    END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_fpas_codigo_vigencia
    ON tabela_fpas (codigo_fpas, vigencia_inicio);

CREATE INDEX IF NOT EXISTS idx_fpas_codigo_periodo
    ON tabela_fpas (codigo_fpas, vigencia_inicio, vigencia_fim);

COMMENT ON COLUMN tabela_fpas.vigencia_inicio IS
    'Inicio da vigencia do ato que fixou esta aliquota. Chave com codigo_fpas.';
COMMENT ON COLUMN tabela_fpas.vigencia_fim IS
    'Fim da vigencia; NULL = em vigor. A competencia apurada escolhe a linha, nunca "a atual".';
COMMENT ON COLUMN tabela_fpas.fonte IS
    'Ato normativo que fixou a aliquota. O loader substitui por ato: e a chave do bloco.';

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT fonte, vigencia_inicio, vigencia_fim, count(*)
--     FROM tabela_fpas GROUP BY 1,2,3 ORDER BY 2;
--   -- esperado: 25 linhas em 2022-10-17 .. 2026-03-31, fonte IN RFB 2.110/2022 Anexo III
--
--   -- e o unique global tem de ter saido (esperado: zero linhas):
--   SELECT conname FROM pg_constraint
--    WHERE conrelid = 'tabela_fpas'::regclass AND contype = 'u'
--      AND pg_get_constraintdef(oid) = 'UNIQUE (codigo_fpas)';
