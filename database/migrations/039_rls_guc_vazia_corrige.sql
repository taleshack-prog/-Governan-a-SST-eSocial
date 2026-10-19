-- 039_rls_guc_vazia_corrige.sql
-- CORRIGE UM DEFEITO REAL nas policies da 032b, achado pelo teste de aceitacao da SECAO 8 do
-- Adendo 05 executado PELA APLICACAO (nao so por SQL).
--
-- O DEFEITO. As policies comparam com current_setting('app.escritorio', true) e tratam NULL
-- como "sem contexto". Mas a GUC so vale NULL enquanto NUNCA foi setada naquela conexao. Depois
-- de um unico SET LOCAL seguido de commit, o Postgres a restaura para STRING VAZIA, nao para
-- NULL. Provado:
--
--     -- conexao nova:
--     SELECT current_setting('app.escritorio', true) IS NULL;   --> t
--     BEGIN; SET LOCAL app.escritorio = '...'; COMMIT;
--     SELECT current_setting('app.escritorio', true) IS NULL;   --> f   (vale '')
--     SELECT current_setting('app.escritorio', true)::uuid;     --> ERRO: invalid input
--                                                                   syntax for type uuid: ""
--
-- As conexoes vivem num POOL e sao reaproveitadas. Logo, a partir da segunda requisicao numa
-- mesma conexao a GUC nunca mais e NULL — ela e ''.
--
-- O QUE ISSO CAUSAVA
--   1) 'usuarios': a policy de leitura libera o login quando nao ha contexto. Com '' no lugar de
--      NULL, o ramo "IS NULL" falha e o cast ''::uuid estoura. Resultado: o PRIMEIRO login numa
--      conexao nova funciona e TODOS OS SEGUINTES falham (401 ou 500). Como o RLS da 'usuarios'
--      esta desligado em producao desde o incidente de 16/10, isso estava latente — e a 032c,
--      que religa essa trava, teria derrubado o login de novo, pelo mesmo efeito e por outro
--      mecanismo.
--   2) Tabelas de cliente: o fail-closed prometido ("sem contexto => zero linhas") nao era zero
--      linhas, era ERRO. Nao vaza dado — mas e o modo de falha errado, e mascarava a intencao.
--
-- O CONSERTO. NULLIF(current_setting('app.escritorio', true), '') em TODAS as policies: conexao
-- nova devolve NULL, conexao reaproveitada devolve NULL, contexto fixado devolve o UUID. O
-- fail-closed volta a ser o que estava escrito que era.
--
-- Depois desta migration a 032c passa a ser segura de aplicar.
--
-- Idempotente: recria as policies.
BEGIN;

DO $$
DECLARE
    t   TEXT;
    tenant_tables TEXT[] := ARRAY[
        'empresas','estabelecimentos',
        'estabelecimento_atividade','estabelecimento_enquadramento',
        'estabelecimento_fap','estabelecimento_rat_aplicado','estabelecimento_fpas_periodo',
        'empresa_regime','empresa_cprb','empresa_cnae_secundario',
        'documentos_tecnicos','trabalhadores','vinculos',
        'agentes_nocivos','ai_validacoes','atestados','atestados_medicos',
        'cat_registros','exames_medicos','funcionario_usuarios','questionario_resposta',
        'achado','rubrica_empresa',
        'afastamentos','alertas_afastamento','afastamento_mensagens','afastamento_notificacoes',
        'audit_log'
    ];
BEGIN
    FOREACH t IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables
                    WHERE table_schema='public' AND table_name=t) THEN
            EXECUTE format('DROP POLICY IF EXISTS p_escritorio ON %I', t);
            EXECUTE format(
                'CREATE POLICY p_escritorio ON %I FOR ALL '
                'USING (escritorio_id = NULLIF(current_setting(''app.escritorio'', true), '''')::uuid) '
                'WITH CHECK (escritorio_id = NULLIF(current_setting(''app.escritorio'', true), '''')::uuid)', t);
        END IF;
    END LOOP;

    -- usuarios: leitura tolera contexto ausente (bootstrap do login); escrita estrita.
    DROP POLICY IF EXISTS p_escritorio_sel ON usuarios;
    DROP POLICY IF EXISTS p_escritorio_mod ON usuarios;
    CREATE POLICY p_escritorio_sel ON usuarios FOR SELECT
        USING (NULLIF(current_setting('app.escritorio', true), '') IS NULL
               OR escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);
    CREATE POLICY p_escritorio_mod ON usuarios FOR ALL
        USING (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
        WITH CHECK (escritorio_id = NULLIF(current_setting('app.escritorio', true), '')::uuid);

    -- escritorios: cada um ve apenas o proprio registro.
    DROP POLICY IF EXISTS p_proprio ON escritorios;
    CREATE POLICY p_proprio ON escritorios FOR ALL
        USING (id = NULLIF(current_setting('app.escritorio', true), '')::uuid)
        WITH CHECK (id = NULLIF(current_setting('app.escritorio', true), '')::uuid);
END $$;

COMMIT;

-- Conferencia depois de aplicar (esperado: NENHUMA policy sem NULLIF):
--   SELECT schemaname, tablename, policyname
--     FROM pg_policies
--    WHERE schemaname = 'public'
--      AND qual LIKE '%current_setting%'
--      AND qual NOT LIKE '%NULLIF%';
