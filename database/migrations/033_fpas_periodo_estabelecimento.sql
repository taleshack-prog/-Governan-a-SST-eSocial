-- 033_fpas_periodo_estabelecimento.sql
-- Adendo 04 (revisao da Carolina, item 4): o FPAS do ESTABELECIMENTO passa a ter VIGENCIA.
--
-- POR QUE COM PERIODO, e nao um campo unico: o FPAS define a composicao de Terceiros, e essa
-- composicao nao e constante dentro da janela de apuracao. Um campo unico obrigaria a escolher
-- uma das vigencias e silenciar a outra — exatamente o tipo de valor presumido que a memoria de
-- enquadramento nao pode conter.
--
-- NAO CONFUNDIR com 'estabelecimento_fap' (FAP, o multiplicador do RAT, por ano). Sao coisas
-- diferentes separadas por uma letra: FAP = Fator Acidentario de Prevencao; FPAS = codigo que
-- determina as contribuicoes a Terceiros. Dai o nome longo desta tabela.
--
-- A coluna legada 'estabelecimentos.fpas' (VARCHAR(4), valor unico, nunca exposta em tela) fica
-- como esta: nao e lida nem escrita por este codigo. Sera removida junto das demais colunas
-- depreciadas, numa migration propria de limpeza.
--
-- ISOLAMENTO (Adendo 05 / RN-24): esta tabela nasce com escritorio_id, trigger de preenchimento,
-- NOT NULL, RLS ENABLE+FORCE e a MESMA politica p_escritorio das demais tabelas de dado de
-- cliente. Toda tabela nova precisa repetir este bloco — sem ele o isolamento nao falha com
-- erro, simplesmente deixa de filtrar aquela tabela.
--
-- Idempotente: pode rodar duas vezes sem efeito colateral.
--
-- PRE-CONDICAO: exige 031 + 032a + 032b. A migration ABORTA com mensagem clara se faltarem, em
-- vez de criar a tabela sem isolamento — uma tabela de cliente sem RLS nao da erro nenhum,
-- apenas para de filtrar, e esse e justamente o modo de falha silenciosa a evitar.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                   WHERE table_schema = 'public' AND table_name = 'escritorios') THEN
        RAISE EXCEPTION 'Falta a migration 031 (tabela escritorios). Aplique 031, 032a e 032b antes desta.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'app_fill_escritorio') THEN
        RAISE EXCEPTION 'Falta a migration 032a (funcao app_fill_escritorio). Aplique 032a antes desta.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        RAISE EXCEPTION 'Falta a migration 032a (papel radar_app). Aplique 032a antes desta.';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS estabelecimento_fpas_periodo (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    codigo_fpas        VARCHAR(4) NOT NULL,
    inicio             DATE NOT NULL,
    fim                DATE,
    declarado_por      VARCHAR(200),              -- autoria (RN-23): quem informou
    declarado_em       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_estab_fpas_periodo_ordem CHECK (fim IS NULL OR fim >= inicio)
);

CREATE INDEX IF NOT EXISTS idx_estab_fpas_periodo_estab
    ON estabelecimento_fpas_periodo(estabelecimento_id, inicio);

-- ---- Isolamento por escritorio (espelha 031 + 032a + 032b) ----
DO $$
DECLARE
    esc UUID;
BEGIN
    SELECT id INTO esc FROM escritorios ORDER BY created_at LIMIT 1;

    -- 1) chave do tenant, com o mesmo DEFAULT das demais
    ALTER TABLE estabelecimento_fpas_periodo
        ADD COLUMN IF NOT EXISTS escritorio_id UUID
        DEFAULT current_setting('app.escritorio', true)::uuid;

    -- 2) backfill (tabela nova: normalmente vazia; a linha existe para ser idempotente)
    IF esc IS NOT NULL THEN
        UPDATE estabelecimento_fpas_periodo SET escritorio_id = esc WHERE escritorio_id IS NULL;
    END IF;

    -- 3) trigger de preenchimento. O DEFAULT nao basta: o ORM manda NULL explicito, e DEFAULT
    --    de coluna nao se aplica a NULL explicito. Esta foi a pegadinha achada na 032a.
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_fill_escritorio'
          AND tgrelid = 'estabelecimento_fpas_periodo'::regclass
    ) THEN
        CREATE TRIGGER trg_fill_escritorio BEFORE INSERT ON estabelecimento_fpas_periodo
            FOR EACH ROW EXECUTE FUNCTION app_fill_escritorio();
    END IF;

    -- 4) fecha a coluna e liga o RLS (FORCE: o dono da tabela tambem seria dispensado)
    ALTER TABLE estabelecimento_fpas_periodo ALTER COLUMN escritorio_id SET NOT NULL;
    ALTER TABLE estabelecimento_fpas_periodo ENABLE ROW LEVEL SECURITY;
    ALTER TABLE estabelecimento_fpas_periodo FORCE  ROW LEVEL SECURITY;

    DROP POLICY IF EXISTS p_escritorio ON estabelecimento_fpas_periodo;
    CREATE POLICY p_escritorio ON estabelecimento_fpas_periodo FOR ALL
        USING      (escritorio_id = current_setting('app.escritorio', true)::uuid)
        WITH CHECK (escritorio_id = current_setting('app.escritorio', true)::uuid);
END $$;

-- 5) permissoes da role da aplicacao. O ALTER DEFAULT PRIVILEGES da 032a cobre tabelas criadas
--    pelo mesmo papel que o executou; o GRANT explicito abaixo torna isso independente de quem
--    roda esta migration.
GRANT SELECT, INSERT, UPDATE, DELETE ON estabelecimento_fpas_periodo TO radar_app;

COMMIT;

-- Conferencia depois de aplicar (esperado: t | t):
--   SELECT relrowsecurity, relforcerowsecurity
--     FROM pg_class WHERE relname = 'estabelecimento_fpas_periodo';
