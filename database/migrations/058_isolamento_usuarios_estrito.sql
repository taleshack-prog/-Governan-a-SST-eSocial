-- 058_isolamento_usuarios_estrito.sql — AJUSTA
-- PASSO 3 DE 3: A TRAVA (janela pedida pela Carolina, 27/10, 21h).
--
-- Esta e a migration que fecha o isolamento da tabela usuarios. Ate aqui, a policy de SELECT
-- tinha um ramo permissivo:
--
--     USING (NULLIF(current_setting('app.escritorio', true), '') IS NULL
--            OR escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
--
-- Com o contexto vazio, QUALQUER usuario era visivel — a aplicacao podia ler a tabela inteira e
-- enumerar todos os usuarios de todos os escritorios. O ramo existia porque o login precisa achar
-- o usuario pelo e-mail antes de saber o escritorio dele.
--
-- Os passos 1 e 2 resolveram a circularidade: auth_usuario_por_email() atravessa a RLS pelos
-- privilegios do dono, exige o e-mail exato, devolve no maximo uma linha, e o login ja a usa em
-- producao. Com isso, o ramo permissivo deixou de ser necessario e passa a ser so exposicao.
--
-- ---------------------------------------------------------------------------------------------
-- A GUARDA, E POR QUE ELA ESTA AQUI
--
-- Hoje, as 18h45, o passo 2 subiu antes de a funcao existir no banco e o login ficou fora por
-- alguns minutos: o codigo chamava algo que nao estava la. Foi erro de sequencia, nao de logica.
--
-- Esta migration nao depende de ninguem lembrar da ordem. Ela VERIFICA que a funcao existe e
-- aborta com uma frase legivel se nao existir. Aplicar a trava sem a funcao derrubaria o login de
-- todos os usuarios ao mesmo tempo, e seria descoberto pela porta — alguem tentando entrar.
--
-- Idempotente: reaplicar nao muda nada.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE p.proname = 'auth_usuario_por_email' AND n.nspname = 'public'
    ) THEN
        RAISE EXCEPTION
            'A função auth_usuario_por_email não existe neste banco. Aplique a migration 057 '
            'ANTES desta: sem ela, remover o ramo permissivo derruba o login de todos os '
            'usuários, porque a busca por e-mail deixa de encontrar qualquer linha.';
    END IF;
END $$;

-- A TRAVA. Daqui em diante, ler usuarios exige contexto de escritorio — sem excecao. O unico
-- caminho que ainda atravessa a RLS e a funcao do login, e ela pede o e-mail exato.
DROP POLICY IF EXISTS p_escritorio_sel ON usuarios;
CREATE POLICY p_escritorio_sel ON usuarios FOR SELECT
    USING (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);

-- A policy de escrita nao muda: ela ja era estrita desde a 039.

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) a policy de SELECT nao tem mais o ramo "IS NULL" (esperado: 1 linha, SEM 'IS NULL')
--   SELECT policyname, cmd, qual FROM pg_policies
--    WHERE tablename = 'usuarios' ORDER BY policyname;
--
--   -- 2) sem contexto, a tabela nao devolve nada (esperado: 0)
--   SELECT count(*) FROM usuarios;
--
--   -- 3) a funcao do login continua achando (troque pelo e-mail real; esperado: 1 linha)
--   -- SELECT email FROM auth_usuario_por_email('alguem@exemplo.com');
--
-- ---------------------------------------------------------------------------------------------
-- ROLLBACK, se o login nao entrar depois da trava. Devolve o ramo permissivo e tudo volta ao que
-- era antes das 21h. Nao desfaz a funcao nem o passo 2 — eles sao inofensivos com a policy
-- tolerante, e foi assim que rodaram a tarde inteira.
--
--   DROP POLICY IF EXISTS p_escritorio_sel ON usuarios;
--   CREATE POLICY p_escritorio_sel ON usuarios FOR SELECT
--       USING (NULLIF(current_setting('app.escritorio', true), '') IS NULL
--              OR escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);
