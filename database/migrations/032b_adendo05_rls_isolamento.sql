-- 032b_adendo05_rls_isolamento.sql
-- Adendo 05 — isolamento imposto NO BANCO (RN-24 / RF-0.202), PARTE B.
-- Rodar como superusuario, DEPOIS de validar a 032a (app conectando como radar_app e funcionando).
--
-- O que faz: liga ROW LEVEL SECURITY + FORCE em toda tabela de dados de cliente, com politica
-- por escritorio lida da GUC 'app.escritorio' (setada pelo backend a cada transacao), e fecha a
-- coluna escritorio_id com NOT NULL.
--
-- Fail-closed: sem a GUC, current_setting(...) e NULL e a comparacao nunca casa => ZERO linhas.
-- Nunca "tudo". FORCE e necessario porque o DONO da tabela tambem seria dispensado do RLS.
-- Superusuario (postgres/sst_user) continua vendo tudo — e por isso que o app NAO pode conectar
-- como superusuario: ele conecta como radar_app (NOSUPERUSER NOBYPASSRLS).
--
-- EXCECAO do login (bootstrap): 'usuarios' libera LEITURA quando a GUC esta vazia, porque a
-- autenticacao precisa achar o usuario ANTES de saber o escritorio dele. Nao e explorável por
-- usuario autenticado: toda requisicao autenticada carrega a GUC. A escrita segue estrita.
--
-- Tabelas de referencia (RN-26) ficam SEM RLS de proposito: CNAE/grau, FPAS, Terceiros, CPRB
-- transicao, SELIC, dicionario de rubricas — sao globais, da curadoria, compartilhadas por todos.
BEGIN;

DO $$
DECLARE
    t   TEXT;
    esc UUID;
    tenant_tables TEXT[] := ARRAY[
        'empresas','estabelecimentos',
        'estabelecimento_atividade','estabelecimento_enquadramento',
        'estabelecimento_fap','estabelecimento_rat_aplicado',
        'empresa_regime','empresa_cprb','empresa_cnae_secundario',
        'documentos_tecnicos','trabalhadores','vinculos',
        'agentes_nocivos','ai_validacoes','atestados','atestados_medicos',
        'cat_registros','exames_medicos','funcionario_usuarios','questionario_resposta',
        'achado','rubrica_empresa',
        'afastamentos','alertas_afastamento','afastamento_mensagens','afastamento_notificacoes',
        'audit_log'
    ];
BEGIN
    SELECT id INTO esc FROM escritorios ORDER BY created_at LIMIT 1;

    FOREACH t IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=t) THEN
            -- garante que nada ficou sem chave antes de fechar a coluna
            EXECUTE format('UPDATE %I SET escritorio_id = %L WHERE escritorio_id IS NULL', t, esc);
            EXECUTE format('ALTER TABLE %I ALTER COLUMN escritorio_id SET NOT NULL', t);
            EXECUTE format('ALTER TABLE %I ENABLE  ROW LEVEL SECURITY', t);
            EXECUTE format('ALTER TABLE %I FORCE   ROW LEVEL SECURITY', t);
            EXECUTE format('DROP POLICY IF EXISTS p_escritorio ON %I', t);
            EXECUTE format(
                'CREATE POLICY p_escritorio ON %I FOR ALL '
                'USING (escritorio_id = current_setting(''app.escritorio'', true)::uuid) '
                'WITH CHECK (escritorio_id = current_setting(''app.escritorio'', true)::uuid)', t);
        END IF;
    END LOOP;

    -- usuarios: leitura liberada com GUC vazia (bootstrap do login); escrita estrita.
    UPDATE usuarios SET escritorio_id = esc WHERE escritorio_id IS NULL;
    ALTER TABLE usuarios ALTER COLUMN escritorio_id SET NOT NULL;
    ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
    ALTER TABLE usuarios FORCE  ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS p_escritorio_sel ON usuarios;
    DROP POLICY IF EXISTS p_escritorio_mod ON usuarios;
    CREATE POLICY p_escritorio_sel ON usuarios FOR SELECT
        USING (current_setting('app.escritorio', true) IS NULL
               OR escritorio_id = current_setting('app.escritorio', true)::uuid);
    CREATE POLICY p_escritorio_mod ON usuarios FOR ALL
        USING (escritorio_id = current_setting('app.escritorio', true)::uuid)
        WITH CHECK (escritorio_id = current_setting('app.escritorio', true)::uuid);

    -- escritorios: cada um ve apenas o proprio registro.
    ALTER TABLE escritorios ENABLE ROW LEVEL SECURITY;
    ALTER TABLE escritorios FORCE  ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS p_proprio ON escritorios;
    CREATE POLICY p_proprio ON escritorios FOR ALL
        USING (id = current_setting('app.escritorio', true)::uuid)
        WITH CHECK (id = current_setting('app.escritorio', true)::uuid);
END $$;

-- Bootstrap do WORKER (Celery): a task roda fora de um request, logo sem a GUC — e sob RLS veria
-- ZERO linhas. Ela tem o empresa_id em maos, mas ler 'empresas' para descobrir o escritorio ja
-- cairia no RLS. Esta funcao SECURITY DEFINER resolve so essa traducao (empresa -> escritorio),
-- sem devolver nenhum dado de cliente. A task chama, seta a GUC, e segue isolada normalmente.
CREATE OR REPLACE FUNCTION app_escritorio_de_empresa(p_empresa UUID) RETURNS UUID
LANGUAGE sql SECURITY DEFINER SET search_path = public STABLE AS $fn$
    SELECT escritorio_id FROM empresas WHERE id = p_empresa
$fn$;
REVOKE ALL ON FUNCTION app_escritorio_de_empresa(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app_escritorio_de_empresa(UUID) TO radar_app;

COMMIT;
