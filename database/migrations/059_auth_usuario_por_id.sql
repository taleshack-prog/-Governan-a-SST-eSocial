-- 059_auth_usuario_por_id.sql — AJUSTA
-- O PONTO QUE FALTOU NO ISOLAMENTO (27/10, 19h).
--
-- A 058 foi aplicada e revertida em minutos: o login abria e fechava. A causa esta aqui.
--
-- O QUE EU TINHA VISTO. O login (POST /auth/token) le usuarios pelo e-mail sem contexto de
-- escritorio, porque so descobre o escritorio depois de achar o usuario. A 057 resolveu isso com
-- auth_usuario_por_email().
--
-- O QUE EU NAO TINHA VISTO. get_current_user() faz a MESMA leitura sem contexto, pelo id do
-- token, e roda em TODA requisicao autenticada — nao uma vez por sessao. E a mesma
-- circularidade: o escritorio que seria usado para filtrar vem justamente do usuario que a
-- consulta esta procurando.
--
-- Com a policy estrita, essa busca deixava de encontrar qualquer linha, toda requisicao
-- respondia 401 e o aplicativo deslogava. O login em si funcionava: o token saia. Morria a
-- chamada seguinte.
--
-- POR QUE DUAS FUNCOES, E NAO UMA GENERICA. Cada uma aceita exatamente um identificador e
-- devolve no maximo uma linha. Uma funcao que recebesse criterio variavel seria um "leia
-- usuarios como o dono" de proposito geral, e a razao de esta tabela ter RLS e nao existir uma
-- porta dessas. Sao duas portas estreitas, cada uma com uma chave so.
--
-- Idempotente.
BEGIN;

CREATE OR REPLACE FUNCTION auth_usuario_por_id(p_id UUID)
RETURNS SETOF usuarios
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    SELECT * FROM usuarios WHERE id = p_id LIMIT 1;
$fn$;

COMMENT ON FUNCTION auth_usuario_por_id(UUID) IS
    'Busca o usuário pelo id, atravessando a RLS. Existe para a validação do token em '
    'get_current_user, que roda antes de o contexto de escritório ser fixado. Não use em '
    'nenhum outro lugar.';

REVOKE ALL ON FUNCTION auth_usuario_por_id(UUID) FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        GRANT EXECUTE ON FUNCTION auth_usuario_por_id(UUID) TO radar_app;
    END IF;
END $$;

COMMIT;

-- Conferencia depois de aplicar (esperado: as DUAS funcoes, prosecdef = t, search_path fixo):
--   SELECT p.proname, p.prosecdef, p.proconfig
--     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
--    WHERE p.proname IN ('auth_usuario_por_email', 'auth_usuario_por_id') AND n.nspname = 'public'
--    ORDER BY p.proname;
--
--   -- PUBLIC nao executa nenhuma das duas (esperado: nenhuma linha com grantee = PUBLIC)
--   SELECT routine_name, grantee, privilege_type FROM information_schema.routine_privileges
--    WHERE routine_name IN ('auth_usuario_por_email', 'auth_usuario_por_id');
