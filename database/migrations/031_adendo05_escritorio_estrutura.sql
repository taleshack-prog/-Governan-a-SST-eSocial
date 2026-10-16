-- 031_adendo05_escritorio_estrutura.sql
-- Adendo 05 — multiempresa e multiescritorio. ESTRUTURA (precede qualquer tela).
-- Cria a entidade ESCRITORIO (o tenant/limite de isolamento), poe a chave escritorio_id em
-- TODAS as tabelas de dados de cliente (RF-0.201), papeis de acesso (RF-0.204), unicidade de
-- CNPJ por escritorio (RN-25/RF-0.203) e migra o cadastro atual sem perda (RF-0.210).
--
-- NAO cria politica de isolamento (RLS) nem filtro de app, e NAO poe escritorio_id como NOT NULL:
-- isso vem na 032 JUNTO com o backend que passa a preencher a chave em todo insert. Enquanto a
-- 032 nao entra, a coluna fica nullable para NAO quebrar os inserts do app atual (a Carolina segue
-- testando). Esta migration e aditiva e idempotente.
--
-- Modalidade do produto (SaaS x OaaS) e um atributo do escritorio: um unico produto/codigo,
-- dois modos de operacao. OaaS = a operacao da propria advogada como um escritorio; SaaS = o
-- contador/advogado contratante como outro escritorio.
BEGIN;

-- 1) Entidade escritorio (RF-0.200)
CREATE TABLE IF NOT EXISTS escritorios (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    razao_social     VARCHAR(300) NOT NULL,
    cnpj             VARCHAR(14),                       -- CNPJ do operador (pode faltar no seed)
    modalidade       VARCHAR(10)  NOT NULL DEFAULT 'oaas',   -- saas | oaas
    plano            VARCHAR(30)  NOT NULL DEFAULT 'trial',
    data_contratacao DATE,
    status           VARCHAR(16)  NOT NULL DEFAULT 'ativo',  -- ativo | suspenso | encerrado
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_escritorios_modalidade CHECK (modalidade IN ('saas','oaas')),
    CONSTRAINT ck_escritorios_status     CHECK (status IN ('ativo','suspenso','encerrado'))
);

-- 2) escritorio_id (NULLABLE) em todas as tabelas de tenant + backfill + indice (RF-0.201/0.210).
--    Backfill trivial: hoje existe um unico escritorio, entao tudo pertence a ele. O NOT NULL
--    entra na 032, quando o backend ja estiver preenchendo a chave.
DO $$
DECLARE
    esc UUID;
    t   TEXT;
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
    -- RF-0.210: cria o primeiro escritorio (operacao propria = OaaS) se ainda nao existe
    SELECT id INTO esc FROM escritorios ORDER BY created_at LIMIT 1;
    IF esc IS NULL THEN
        INSERT INTO escritorios (razao_social, modalidade, plano, status)
        VALUES ('Escritório Principal', 'oaas', 'trial', 'ativo')
        RETURNING id INTO esc;
    END IF;

    FOREACH t IN ARRAY tenant_tables LOOP
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=t) THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS escritorio_id UUID REFERENCES escritorios(id)', t);
            EXECUTE format('UPDATE %I SET escritorio_id = %L WHERE escritorio_id IS NULL', t, esc);
            EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_escritorio ON %I (escritorio_id)', t, t);
        END IF;
    END LOOP;

    -- 3) usuarios: vinculo ao escritorio + papel (RF-0.204). Usuario atual vira titular (RF-0.210).
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS escritorio_id UUID REFERENCES escritorios(id);
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS papel VARCHAR(12) NOT NULL DEFAULT 'operador';
    UPDATE usuarios SET escritorio_id = esc WHERE escritorio_id IS NULL;
    UPDATE usuarios SET papel = 'titular' WHERE papel NOT IN ('operador','leitor','cliente');
    CREATE INDEX IF NOT EXISTS idx_usuarios_escritorio ON usuarios (escritorio_id);
END $$;

ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS ck_usuarios_papel;
ALTER TABLE usuarios ADD  CONSTRAINT ck_usuarios_papel
    CHECK (papel IN ('titular','operador','leitor','cliente'));

-- 4) RN-25/RF-0.203: CNPJ e unico DENTRO do escritorio, nunca global.
--    Remove QUALQUER unique global sobre empresas(cnpj), seja qual for o nome gerado pelo ORM.
DO $$
DECLARE c TEXT;
BEGIN
    FOR c IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_attribute att ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey)
        WHERE rel.relname = 'empresas' AND con.contype = 'u'
          AND array_length(con.conkey, 1) = 1 AND att.attname = 'cnpj'
    LOOP
        EXECUTE format('ALTER TABLE empresas DROP CONSTRAINT %I', c);
    END LOOP;
END $$;
DROP INDEX IF EXISTS empresas_cnpj_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_empresas_escritorio_cnpj ON empresas (escritorio_id, cnpj);

-- 5) RF-0.207/0.209: colunas que arquivar/medicao consomem — precisam existir desde ja (§7).
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS arquivada     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE empresas ADD COLUMN IF NOT EXISTS arquivada_em  TIMESTAMPTZ;

COMMIT;
