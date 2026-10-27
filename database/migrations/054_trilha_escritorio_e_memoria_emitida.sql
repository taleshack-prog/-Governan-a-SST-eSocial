-- 054_trilha_escritorio_e_memoria_emitida.sql — AJUSTA
-- O BLOCO "ARQUIVAR OU EXCLUIR" (revisao da Carolina, 22/10, retomada em 27/10).
--
-- Duas tabelas, para dois pedidos que nenhuma tabela existente atende.
--
-- ---------------------------------------------------------------------------------------------
-- POR QUE NAO DA PARA USAR A TRILHA QUE JA EXISTE
--
-- 'enquadramento_evento' (migration 047) referencia estabelecimentos com ON DELETE CASCADE, e os
-- estabelecimentos somem quando a empresa e excluida. Registrar a exclusao ali seria gravar a
-- linha e apaga-la no mesmo ato — o registro morreria junto com o que ele existe para testemunhar.
--
-- Dai a primeira tabela nascer SEM chave estrangeira para empresa, e guardar razao social e CNPJ
-- como TEXTO COPIADO no instante do ato. Nas palavras dela: "a exclusao fica registrada na trilha
-- de eventos do escritorio: quem excluiu, quando e qual empresa (razao social e CNPJ), mesmo
-- depois de os dados da empresa sumirem."
--
-- ---------------------------------------------------------------------------------------------
-- POR QUE A SEGUNDA TABELA GUARDA O PDF, E NAO SO A DATA
--
-- Ela, em 27/10: "alem de registrar autor e data da emissao, guarda uma copia do PDF emitido, ou
-- pelo menos o hash dele. Os dados mudam e a memoria gerada depois sai diferente. Se um dia
-- questionarem o que constava numa memoria que foi para uma peca, o registro precisa conseguir
-- MOSTRAR o documento exatamente como saiu."
--
-- Registrar que houve emissao e metade da prova; a outra metade e o conteudo. Basta alguem alterar
-- um FAP para que a mesma memoria, gerada de novo, saia diferente da que foi protocolada. O hash
-- sozinho nao resolve: ele confere um arquivo que alguem ja tenha em maos, e nao devolve nada
-- quando o arquivo se perdeu. Por isso o PDF e guardado, e o SHA-256 vai junto — e ele que permite
-- demonstrar que a copia guardada nao foi trocada depois.
--
-- O CORTE E "A PARTIR DE AGORA", por decisao dela: a emissao nunca foi registrada, e nao ha dado
-- no passado para recuperar. Tudo o que saiu ate hoje e teste da KRETA e nenhuma peca foi
-- protocolada, entao o periodo sem registro esta vazio de verdade.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

-- ---------------------------------------------------------------------------------------------
-- 1) TRILHA DO ESCRITORIO — o que sobrevive a exclusao
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS escritorio_evento (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escritorio_id   UUID NOT NULL DEFAULT NULLIF(current_setting('app.escritorio', true), '')::uuid,

    -- Vocabulario fechado por CHECK, como na 047: evento e dado de maquina, nao texto livre.
    --   arquivada   — saiu da lista principal, dados integros (reversivel)
    --   restaurada  — voltou para a lista
    --   excluida    — apagada com os dados (irreversivel)
    evento          VARCHAR(24) NOT NULL,

    -- SEM REFERENCES, de proposito: depois da exclusao este id nao aponta para linha alguma, e
    -- uma chave estrangeira obrigaria a apagar a trilha junto ou a deixa-la invalida. Fica como
    -- referencia fraca, util enquanto a empresa existe e inofensiva depois.
    empresa_id      UUID,

    -- A IDENTIFICACAO COPIADA. E o que responde "qual empresa?" quando nao ha mais empresa.
    razao_social    VARCHAR(300) NOT NULL,
    cnpj            VARCHAR(20),

    autor           VARCHAR(200) NOT NULL,     -- nome da pessoa, no padrao do resto do sistema
    ocorrido_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    detalhe         VARCHAR(500),              -- ex.: o que havia no momento da exclusao

    CONSTRAINT ck_escritorio_evento_vocabulario
        CHECK (evento IN ('arquivada', 'restaurada', 'excluida'))
);

-- "O que aconteceu neste escritorio ultimamente" — a leitura da trilha.
CREATE INDEX IF NOT EXISTS idx_escritorio_evento_recente
    ON escritorio_evento (escritorio_id, ocorrido_em DESC);

-- O historico de UMA empresa, que o bloco do cadastro le para mostrar "Arquivada por... em...".
CREATE INDEX IF NOT EXISTS idx_escritorio_evento_empresa
    ON escritorio_evento (empresa_id, ocorrido_em DESC);

COMMENT ON TABLE escritorio_evento IS
    'Trilha dos atos de ciclo de vida da empresa (arquivar, restaurar, excluir). Sem chave '
    'estrangeira para empresas e com razao social e CNPJ copiados, para que o registro da '
    'exclusao sobreviva a propria exclusao.';

-- ---------------------------------------------------------------------------------------------
-- 2) MEMORIAS EMITIDAS — o documento como ele saiu
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memoria_emitida (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escritorio_id       UUID NOT NULL DEFAULT NULLIF(current_setting('app.escritorio', true), '')::uuid,

    -- Aqui as chaves estrangeiras SAO desejaveis: enquanto houver memoria emitida a empresa nao
    -- pode ser excluida (e a trava deste mesmo bloco), entao o CASCADE nunca dispara com
    -- documento guardado dentro. Ele existe para o caso de a trava um dia ser revista, e para
    -- que a tabela nunca guarde linha orfa.
    empresa_id          UUID NOT NULL REFERENCES empresas(id)         ON DELETE CASCADE,
    estabelecimento_id  UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,

    -- O DOCUMENTO. 'pdf' pode ser nulo quando o arquivo passar do teto que a aplicacao aceita
    -- guardar inline; 'bytes' registra o tamanho real de qualquer forma, e o hash continua
    -- valendo. Melhor um registro que diz "nao guardei a copia, aqui esta a impressao digital"
    -- do que um que silencia sobre isso.
    -- DOIS HASHES, com papeis distintos.
    --
    --   sha256          — do ARQUIVO guardado. E a prova de integridade: permite demonstrar que a
    --                     copia nao foi trocada depois.
    --   sha256_conteudo — do CONTEUDO que gerou o documento, sem a hora de geracao. E a chave de
    --                     deduplicacao.
    --
    -- Por que dois. A memoria imprime "Documento gerado em 27/10/2026 às 15:40", entao o arquivo
    -- muda a cada emissao ainda que nada nos dados tenha mudado. Deduplicar pelo hash do arquivo
    -- contaria cinco aberturas da mesma tela como cinco memorias emitidas — numero que a tela
    -- mostra e que participa da trava da exclusao. O que interessa guardar e cada versao do
    -- CONTEUDO: alterou-se um FAP, a memoria passa a dizer outra coisa e vira registro novo.
    sha256              CHAR(64) NOT NULL,
    sha256_conteudo     CHAR(64) NOT NULL,
    pdf                 BYTEA,
    bytes               INTEGER NOT NULL,

    -- O periodo que a peca cobre, copiado para que a listagem se leia sem reabrir o PDF.
    competencia_inicio  DATE,
    competencia_fim     DATE,

    -- PRIMEIRA e ULTIMA emissao deste mesmo conteudo. Reemitir a mesma memoria nao cria registro
    -- novo (ver a unicidade abaixo): o que importa guardar e cada VERSAO distinta do documento.
    emitida_por         VARCHAR(200) NOT NULL,
    emitida_em          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_emissao_por  VARCHAR(200),
    ultima_emissao_em   TIMESTAMPTZ,
    vezes               INTEGER NOT NULL DEFAULT 1,

    -- UM REGISTRO POR CONTEUDO DISTINTO. O endpoint da memoria e um GET: abrir a tela duas vezes,
    -- recarregar ou o navegador reaproveitar o pedido geraria linhas repetidas e uma contagem de
    -- "memorias emitidas" sem sentido. Reemitir o mesmo conteudo atualiza a ultima emissao, e so
    -- um conteudo DIFERENTE vira registro novo — que e exatamente o fato que ela quer poder
    -- provar: a memoria de 12/11 nao era a de hoje.
    CONSTRAINT uq_memoria_emitida_conteudo UNIQUE (estabelecimento_id, sha256_conteudo)
);

CREATE INDEX IF NOT EXISTS idx_memoria_emitida_empresa
    ON memoria_emitida (empresa_id, emitida_em DESC);

COMMENT ON TABLE memoria_emitida IS
    'Memorias de calculo emitidas, com autor, data, SHA-256 e a copia do PDF. Responde "o que '
    'constava na memoria de tal data" depois de os dados terem mudado, e e uma das duas '
    'condicoes que impedem a exclusao da empresa.';

-- ---------------------------------------------------------------------------------------------
-- Isolamento por escritorio — as migrations de RLS nao alcancam tabela nova (ver cabecalho da 047)
-- ---------------------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_fill_escritorio ON escritorio_evento;
CREATE TRIGGER trg_fill_escritorio
    BEFORE INSERT ON escritorio_evento
    FOR EACH ROW EXECUTE FUNCTION app_fill_escritorio();

DROP TRIGGER IF EXISTS trg_fill_escritorio ON memoria_emitida;
CREATE TRIGGER trg_fill_escritorio
    BEFORE INSERT ON memoria_emitida
    FOR EACH ROW EXECUTE FUNCTION app_fill_escritorio();

ALTER TABLE escritorio_evento ENABLE ROW LEVEL SECURITY;
ALTER TABLE escritorio_evento FORCE  ROW LEVEL SECURITY;
ALTER TABLE memoria_emitida   ENABLE ROW LEVEL SECURITY;
ALTER TABLE memoria_emitida   FORCE  ROW LEVEL SECURITY;

-- NULLIF obrigatorio (migration 039): sem ele, contexto vazio derruba a policy com erro de cast
-- em vez de simplesmente nao casar.
DROP POLICY IF EXISTS p_escritorio ON escritorio_evento;
CREATE POLICY p_escritorio ON escritorio_evento FOR ALL
    USING      (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
    WITH CHECK (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);

DROP POLICY IF EXISTS p_escritorio ON memoria_emitida;
CREATE POLICY p_escritorio ON memoria_emitida FOR ALL
    USING      (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
    WITH CHECK (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);

-- O ALTER DEFAULT PRIVILEGES da 032a so alcanca tabela criada pelo MESMO papel que o executou.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON escritorio_evento TO radar_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON memoria_emitida   TO radar_app;
    END IF;
END $$;

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) as duas tabelas existem e estao protegidas (esperado: duas linhas, t | t)
--   SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class
--    WHERE relname IN ('escritorio_evento', 'memoria_emitida');
--
--   -- 2) as policies usam NULLIF (esperado: duas linhas, com NULLIF no texto)
--   SELECT tablename, policyname, qual FROM pg_policies
--    WHERE tablename IN ('escritorio_evento', 'memoria_emitida');
--
--   -- 3) os triggers de preenchimento existem (esperado: duas linhas)
--   SELECT tgrelid::regclass AS tabela, tgname FROM pg_trigger
--    WHERE tgrelid IN ('escritorio_evento'::regclass, 'memoria_emitida'::regclass)
--      AND NOT tgisinternal;
--
--   -- 4) NENHUMA policy do banco ficou sem NULLIF (esperado: 0 linhas)
--   SELECT tablename, policyname FROM pg_policies
--    WHERE schemaname = 'public' AND qual LIKE '%current_setting%' AND qual NOT LIKE '%NULLIF%';
