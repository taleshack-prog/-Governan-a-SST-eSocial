-- 032a_adendo05_app_role.sql
-- Adendo 05 — isolamento (RN-24), PARTE A: papel de aplicacao + preenchimento automatico da chave.
-- Rodar como superusuario (postgres / sst_user).
--
-- Por que: RLS so vale se o app conectar com um papel NAO-superusuario e NAO-bypassrls. O papel
-- atual (postgres/sst_user) e superuser => RLS seria ignorado. Aqui criamos 'radar_app'
-- (LOGIN, sem superuser/bypass), damos os grants, e fazemos a coluna escritorio_id se preencher
-- sozinha a partir da GUC app.escritorio (setada pelo backend por request). NADA de RLS ainda —
-- isso e a 032b. Apos esta migration + a troca da conexao, o app funciona igual a hoje.
--
-- IMPORTANTE: esta migration NAO define a senha de radar_app (segredo nao entra no git).
-- Depois de aplicar, rode (em cada banco), escolhendo a senha:
--     ALTER ROLE radar_app PASSWORD 'ESCOLHA_UMA_SENHA_FORTE';
-- e troque a conexao do app (POSTGRES_USER=radar_app / POSTGRES_PASSWORD=...) no Railway e no
-- compose local. Reversivel: basta voltar a conexao para postgres/sst_user.
BEGIN;

-- 1) Papel de aplicacao (idempotente), explicitamente sem superuser e sem bypass de RLS
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        CREATE ROLE radar_app LOGIN NOSUPERUSER NOBYPASSRLS;
    ELSE
        ALTER ROLE radar_app NOSUPERUSER NOBYPASSRLS;
    END IF;
END $$;

-- 2) Grants: conectar, usar o schema, DML em todas as tabelas e sequences (atuais e futuras)
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO radar_app', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO radar_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO radar_app;
GRANT USAGE, SELECT, UPDATE        ON ALL SEQUENCES   IN SCHEMA public TO radar_app;
GRANT EXECUTE                      ON ALL FUNCTIONS   IN SCHEMA public TO radar_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES    TO radar_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE         ON SEQUENCES TO radar_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE                        ON FUNCTIONS TO radar_app;

-- 3) escritorio_id se preenche sozinho a partir da GUC (sem tocar no codigo de cada insert).
--
--    Usamos DEFAULT **e** trigger BEFORE INSERT. Motivo: o DEFAULT da coluna NAO se aplica quando
--    o cliente envia NULL explicitamente (o ORM pode fazer isso). O trigger cobre todos os
--    caminhos — ORM, SQL cru, import — e e o que garante a chave em 100% dos inserts.
--    Enquanto a GUC nao estiver setada, resolve para NULL (coluna ainda nullable nesta fase).
--    Tambem rebackfilla qualquer linha que tenha nascido NULL entre a 031 e a 032a.
CREATE OR REPLACE FUNCTION app_fill_escritorio() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.escritorio_id IS NULL THEN
        NEW.escritorio_id := current_setting('app.escritorio', true)::uuid;
    END IF;
    RETURN NEW;
END
$fn$;

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
        'audit_log','usuarios'
    ];
BEGIN
    SELECT id INTO esc FROM escritorios ORDER BY created_at LIMIT 1;
    FOREACH t IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=t) THEN
            EXECUTE format('ALTER TABLE %I ALTER COLUMN escritorio_id SET DEFAULT current_setting(''app.escritorio'', true)::uuid', t);
            EXECUTE format('UPDATE %I SET escritorio_id = %L WHERE escritorio_id IS NULL', t, esc);
            EXECUTE format('DROP TRIGGER IF EXISTS trg_fill_escritorio ON %I', t);
            EXECUTE format('CREATE TRIGGER trg_fill_escritorio BEFORE INSERT ON %I '
                           'FOR EACH ROW EXECUTE FUNCTION app_fill_escritorio()', t);
        END IF;
    END LOOP;
END $$;

GRANT EXECUTE ON FUNCTION app_fill_escritorio() TO radar_app;

COMMIT;
