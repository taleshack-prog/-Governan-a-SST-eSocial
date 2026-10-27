-- 057_auth_usuario_por_email.sql — AJUSTA
-- PASSO 1 DE 3 DO ISOLAMENTO DA TABELA usuarios (janela pedida pela Carolina, 27/10, 21h).
--
-- ESTA MIGRATION NAO MUDA COMPORTAMENTO NENHUM. Ela so cria a funcao que o passo 2 passara a
-- usar. Enquanto a policy continuar tolerante, o login nao depende dela — e e justamente por
-- isso que ela entra antes, fora da janela: a funcao tem de existir quando o codigo que a chama
-- subir, e nao o contrario.
--
-- ---------------------------------------------------------------------------------------------
-- O PROBLEMA QUE ELA RESOLVE
--
-- A policy de SELECT da tabela usuarios tem hoje um ramo permissivo:
--
--     USING (NULLIF(current_setting('app.escritorio', true), '') IS NULL
--            OR escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
--
-- Com o contexto vazio, QUALQUER usuario e visivel. O ramo existe por uma circularidade real: o
-- login precisa achar o usuario pelo e-mail ANTES de saber a que escritorio ele pertence, e o
-- contexto so pode ser fixado depois disso.
--
-- Remover o ramo sem resolver a circularidade derruba o login de todo mundo: a busca por e-mail
-- deixa de encontrar qualquer linha e o sistema responde "email ou senha incorretos" para
-- credenciais corretas.
--
-- ---------------------------------------------------------------------------------------------
-- POR QUE SECURITY DEFINER, E POR QUE ISSO E MAIS ESTRITO DO QUE HOJE
--
-- A funcao roda com os privilegios do dono da tabela, entao atravessa a RLS — e e exatamente o
-- que o login precisa para o unico passo em que ainda nao ha escritorio conhecido.
--
-- Parece afrouxar, e aperta: HOJE, sem contexto, a aplicacao le a tabela INTEIRA e pode enumerar
-- todos os usuarios de todos os escritorios. Depois do passo 3 ela nao le nada sem contexto, e o
-- unico caminho restante e esta funcao, que exige o e-mail EXATO e devolve no maximo uma linha.
-- A superficie sai de "a tabela toda" para "quem souber o endereco completo de alguem".
--
-- 'search_path' fixo e obrigatorio em SECURITY DEFINER: sem ele, quem chama pode plantar um
-- schema na frente e fazer a funcao operar sobre outra tabela 'usuarios', com os privilegios do
-- dono. E a armadilha classica desse recurso.
--
-- RETURNS SETOF usuarios de proposito: o login precisa da entidade completa (hash da senha,
-- escritorio, empresa, perfil, nome) e o ORM a mapeia direto, sem uma segunda consulta e sem uma
-- lista de colunas que teria de ser mantida em sincronia com o modelo.
--
-- Idempotente.
BEGIN;

CREATE OR REPLACE FUNCTION auth_usuario_por_email(p_email TEXT)
RETURNS SETOF usuarios
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    SELECT * FROM usuarios WHERE email = p_email LIMIT 1;
$fn$;

COMMENT ON FUNCTION auth_usuario_por_email(TEXT) IS
    'Busca o usuário pelo e-mail exato, atravessando a RLS. Existe para o único passo do login '
    'em que o escritório ainda não é conhecido. Não use em nenhum outro lugar: toda leitura de '
    'usuarios fora do login deve passar pela policy, com o contexto fixado.';

-- Só a aplicação executa. REVOKE de PUBLIC primeiro porque o padrao do Postgres e conceder
-- EXECUTE a todos — e numa funcao SECURITY DEFINER isso entrega o bypass da RLS a qualquer papel.
REVOKE ALL ON FUNCTION auth_usuario_por_email(TEXT) FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        GRANT EXECUTE ON FUNCTION auth_usuario_por_email(TEXT) TO radar_app;
    END IF;
END $$;

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) a funcao existe, e SECURITY DEFINER e tem search_path fixo
--   --    (esperado: 1 linha, prosecdef = t, e 'search_path=public, pg_temp' na config)
--   SELECT p.proname, p.prosecdef, p.proconfig
--     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--    WHERE p.proname = 'auth_usuario_por_email' AND n.nspname = 'public';
--
--   -- 2) PUBLIC nao executa (esperado: nenhuma linha com grantee = PUBLIC)
--   SELECT grantee, privilege_type FROM information_schema.routine_privileges
--    WHERE routine_name = 'auth_usuario_por_email';
--
--   -- 3) a funcao acha quem existe (troque pelo e-mail real; esperado: 1 linha)
--   -- SELECT id, email, escritorio_id FROM auth_usuario_por_email('alguem@exemplo.com');
