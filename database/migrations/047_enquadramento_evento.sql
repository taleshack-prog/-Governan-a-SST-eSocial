-- 047_enquadramento_evento.sql — AJUSTAPREV
-- TRILHA DE EVENTOS DO ENQUADRAMENTO (especificacao da Carolina, 21/10).
--
-- POR QUE ELA EXISTE. Hoje a competencia guarda que uma conferencia foi revogada (revogado_em,
-- revogado_por, revogado_de), mas NAO guarda sobre qual numero a pessoa tinha assinado. Conferir
-- e assinar sobre um valor determinado; sem esse valor, o rastro registra que algo mudou e nao
-- consegue dizer o que foi validado. Numa peca que vai assinada, isso e a diferenca entre ter
-- prova e ter anotacao.
--
-- Nas palavras dela: "Por evento: competencia, o que aconteceu, quem, quando, o valor apurado
-- naquele instante, e nas revogacoes qual campo mudou, de que valor para qual."
--
-- ============================================================================================
-- ISOLAMENTO: ESTA TABELA NASCE PROTEGIDA, E ISSO NAO E ZELO EXCESSIVO
-- ============================================================================================
-- As migrations de isolamento (032a, 032b, 039) varrem uma LISTA FIXA de tabelas e pulam, em
-- silencio, as que ainda nao existem:
--
--     IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = t) THEN ...
--
-- Quem cria tabela depois delas nao recebe aviso nenhum: a tabela simplesmente nasce sem
-- escritorio_id, sem RLS e sem policy, e passa a vazar dados entre escritorios sem que nada
-- falhe. Por isso tudo o que aquelas tres migrations fariam esta aqui dentro, explicito:
--   1) coluna escritorio_id NOT NULL
--   2) DEFAULT a partir da GUC app.escritorio
--   3) trigger BEFORE INSERT (o DEFAULT nao se aplica quando o ORM manda NULL explicito)
--   4) ENABLE + FORCE ROW LEVEL SECURITY
--   5) policy p_escritorio com NULLIF(..., '') — sem o NULLIF, conexao de pool reaproveitada
--      devolve string vazia em vez de NULL e o cast ''::uuid ESTOURA (defeito que a 039 corrigiu)
--   6) GRANT para radar_app
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

CREATE TABLE IF NOT EXISTS enquadramento_evento (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escritorio_id       UUID NOT NULL DEFAULT NULLIF(current_setting('app.escritorio', true), '')::uuid,
    estabelecimento_id  UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    competencia         DATE NOT NULL,

    -- O QUE ACONTECEU. Vocabulario fechado por CHECK: evento e dado de maquina, nao texto livre.
    --   apurado      — o motor calculou (ou recalculou com numero diferente)
    --   conferido    — uma PESSOA validou
    --   desconferido — uma PESSOA retirou a propria validacao
    --   revogado     — o numero mudou por baixo de uma conferencia; ela deixou de valer
    evento              VARCHAR(24) NOT NULL,

    -- QUEM E QUANDO. 'autor' e nulo apenas quando o evento nasce de rotina sem usuario; o ato
    -- humano (conferido/desconferido) sempre tem nome — e a assinatura.
    autor               VARCHAR(200),
    ocorrido_em         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- O RETRATO DO CALCULO NAQUELE INSTANTE. E o nucleo do pedido: a conferencia precisa guardar
    -- o valor sobre o qual foi dada. Estes campos sao COPIA, nao referencia — se a competencia
    -- for recalculada amanha, o que foi assinado ontem continua legivel aqui.
    grau_risco          SMALLINT,
    aliquota_devida     NUMERIC(4, 2),
    fap                 NUMERIC(5, 4),
    aliquota_efetiva    NUMERIC(6, 4),
    aliquota_aplicada   NUMERIC(6, 4),
    rat_aplicavel       BOOLEAN,

    -- NAS REVOGACOES: O QUE MUDOU, DE QUE VALOR PARA QUAL.
    -- JSONB e nao tres colunas porque mais de um campo pode mudar na mesma reapuracao (grau E
    -- fator, tipicamente), e tres colunas obrigariam a escolher um para registrar e descartar o
    -- resto. Formato: [{"campo": "fap", "de": "1.0000", "para": "1.1500"}, ...]
    alteracoes          JSONB,

    -- Texto para a peca, quando houver. Nunca substitui 'alteracoes': um e para ler, o outro e
    -- para conferir.
    motivo              VARCHAR(300),

    CONSTRAINT ck_enq_evento_vocabulario
        CHECK (evento IN ('apurado', 'conferido', 'desconferido', 'revogado'))
);

-- Historico de UMA competencia, do mais recente para o mais antigo: e assim que a tela e a peca
-- vao ler.
CREATE INDEX IF NOT EXISTS idx_enq_evento_comp
    ON enquadramento_evento (estabelecimento_id, competencia, ocorrido_em DESC);

-- "O que aconteceu neste estabelecimento ultimamente", sem filtrar competencia.
CREATE INDEX IF NOT EXISTS idx_enq_evento_recente
    ON enquadramento_evento (estabelecimento_id, ocorrido_em DESC);

COMMENT ON TABLE enquadramento_evento IS
    'Trilha de eventos do enquadramento por competencia. Cada linha guarda o retrato do calculo '
    'no instante do evento — e o que torna a conferencia uma assinatura sobre um numero '
    'determinado, e nao apenas uma marca de que alguem olhou.';

-- ---------------------------------------------------------------------------------------------
-- Isolamento por escritorio (ver cabecalho: as migrations de RLS nao alcancam tabela nova)
-- ---------------------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_fill_escritorio ON enquadramento_evento;
CREATE TRIGGER trg_fill_escritorio
    BEFORE INSERT ON enquadramento_evento
    FOR EACH ROW EXECUTE FUNCTION app_fill_escritorio();

ALTER TABLE enquadramento_evento ENABLE ROW LEVEL SECURITY;
ALTER TABLE enquadramento_evento FORCE  ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_escritorio ON enquadramento_evento;
CREATE POLICY p_escritorio ON enquadramento_evento FOR ALL
    USING      (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
    WITH CHECK (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);

-- O ALTER DEFAULT PRIVILEGES da 032a so alcanca tabela criada pelo MESMO papel que o executou.
-- Explicito aqui para nao depender de quem roda esta migration.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON enquadramento_evento TO radar_app;
    END IF;
END $$;

-- As proximas migrations de isolamento precisam conhecer esta tabela. Se um dia a lista fixa
-- daquelas migrations for revista, 'enquadramento_evento' entra nela.

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) a tabela existe e esta protegida (esperado: t | t)
--   SELECT relrowsecurity, relforcerowsecurity
--     FROM pg_class WHERE relname = 'enquadramento_evento';
--
--   -- 2) a policy usa NULLIF (esperado: 1 linha, com NULLIF no texto)
--   SELECT policyname, qual FROM pg_policies WHERE tablename = 'enquadramento_evento';
--
--   -- 3) o trigger de preenchimento existe (esperado: trg_fill_escritorio)
--   SELECT tgname FROM pg_trigger
--    WHERE tgrelid = 'enquadramento_evento'::regclass AND NOT tgisinternal;
--
--   -- 4) NENHUMA policy do banco ficou sem NULLIF (esperado: 0 linhas)
--   SELECT tablename, policyname FROM pg_policies
--    WHERE schemaname = 'public' AND qual LIKE '%current_setting%' AND qual NOT LIKE '%NULLIF%';
