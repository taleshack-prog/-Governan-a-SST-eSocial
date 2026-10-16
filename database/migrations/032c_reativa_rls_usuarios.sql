-- 032c_reativa_rls_usuarios.sql
-- Conserta o incidente do login e RELIGA o RLS da tabela 'usuarios'.
--
-- O QUE QUEBROU: a 032b ligou RLS em 'usuarios'. O login grava ultimo_login logo apos conferir a
-- senha, e nesse instante o contexto do escritorio AINDA NAO estava fixado (so e conhecido depois
-- de achar o usuario). A policy de escrita exige o contexto => o UPDATE atingiu zero linhas => o
-- ORM abortou a requisicao => login caiu para todo mundo. Mitigacao aplicada na hora:
-- ALTER TABLE usuarios DISABLE ROW LEVEL SECURITY.
--
-- O CONSERTO: nao foi afrouxar a regra, foi corrigir a ordem no codigo — api/routers/auth.py passa
-- a FIXAR o contexto logo apos autenticar e ANTES de gravar. A policy de escrita segue estrita; so
-- a de leitura tolera contexto vazio, que e o que o login precisa para achar o usuario pelo e-mail.
--
-- ORDEM OBRIGATORIA: aplicar esta migration SOMENTE depois que a API ja estiver rodando com a
-- correcao do auth.py. Religar antes derruba o login de novo.
--
-- As policies da 032b continuam criadas (DISABLE apenas deixou de aplica-las); aqui so reativamos.
BEGIN;

ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios FORCE  ROW LEVEL SECURITY;

COMMIT;

-- Conferencia rapida depois de aplicar (esperado: t | t):
--   SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'usuarios';
-- E, principalmente: fazer login. Se o login falhar, desligue de novo com
--   ALTER TABLE usuarios DISABLE ROW LEVEL SECURITY;
-- e me chame — o isolamento das tabelas de dado de cliente nao depende desta.
