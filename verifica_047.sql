-- verifica_047.sql — ARQUIVO TEMPORARIO, apagar depois. Somente leitura.
-- Confere se a tabela de eventos nasceu PROTEGIDA. E o ponto que a Carolina marcou: as
-- migrations de isolamento pulam em silencio as tabelas que ainda nao existem, entao tabela
-- criada depois delas nasce vazando e nada falha para avisar.
\pset pager off

\echo '>>> 1. a tabela existe e tem RLS ligado e forcado (esperado: t | t)'
SELECT relrowsecurity AS rls_ligado, relforcerowsecurity AS rls_forcado
  FROM pg_class WHERE relname = 'enquadramento_evento';

\echo ''
\echo '>>> 2. a policy existe E usa NULLIF (esperado: 1 linha, com NULLIF no texto)'
\echo '    sem NULLIF, conexao de pool reaproveitada manda string vazia e o cast ::uuid estoura'
SELECT policyname, (qual::text LIKE '%NULLIF%') AS tem_nullif
  FROM pg_policies WHERE tablename = 'enquadramento_evento';

\echo ''
\echo '>>> 3. o trigger que preenche escritorio_id (esperado: trg_fill_escritorio)'
SELECT tgname FROM pg_trigger
 WHERE tgrelid = 'enquadramento_evento'::regclass AND NOT tgisinternal;

\echo ''
\echo '>>> 4. escritorio_id e NOT NULL e tem DEFAULT (esperado: NO | com current_setting)'
SELECT is_nullable, column_default
  FROM information_schema.columns
 WHERE table_name = 'enquadramento_evento' AND column_name = 'escritorio_id';

\echo ''
\echo '>>> 5. VARREDURA GERAL: alguma policy do banco ficou sem NULLIF? (esperado: 0 linhas)'
SELECT tablename, policyname FROM pg_policies
 WHERE schemaname = 'public' AND qual::text LIKE '%current_setting%'
   AND qual::text NOT LIKE '%NULLIF%';

\echo ''
\echo '>>> 6. VARREDURA GERAL: tabela com escritorio_id mas SEM RLS? (esperado: 0 linhas)'
\echo '    e exatamente o modo de falha que esta migration existe para nao repetir'
SELECT c.relname AS tabela_desprotegida
  FROM pg_class c
  JOIN information_schema.columns col
    ON col.table_name = c.relname AND col.column_name = 'escritorio_id'
 WHERE c.relkind = 'r' AND col.table_schema = 'public' AND NOT c.relrowsecurity
 ORDER BY 1;

\echo ''
\echo '>>> 7. eventos gravados ate agora, por tipo'
SELECT evento, count(*) AS quantos,
       count(alteracoes) AS com_diff,
       min(ocorrido_em) AS primeiro, max(ocorrido_em) AS ultimo
  FROM enquadramento_evento GROUP BY evento ORDER BY evento;

\echo ''
\echo '>>> 8. os dez eventos mais recentes, legiveis'
SELECT to_char(competencia, 'MM/YYYY') AS comp,
       evento,
       coalesce(autor, '-')                         AS autor,
       to_char(ocorrido_em, 'DD/MM HH24:MI')        AS quando,
       coalesce(aliquota_devida::text, '-')         AS devida,
       coalesce(fap::text, '-')                     AS fap,
       coalesce(aliquota_aplicada::text, '-')       AS aplicada,
       -- protegido: jsonb_array_length() estoura quando o valor nao e lista, e derruba
       -- a consulta toda em vez de mostrar a linha defeituosa.
       CASE WHEN jsonb_typeof(alteracoes) = 'array'
            THEN jsonb_array_length(alteracoes) ELSE 0 END      AS n_mudancas,
       coalesce(jsonb_typeof(alteracoes), 'SQL NULL')           AS tipo_json
  FROM enquadramento_evento
 ORDER BY ocorrido_em DESC LIMIT 10;
