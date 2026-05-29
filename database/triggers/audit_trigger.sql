-- ==============================================================
-- SST ESOCIAL GOV — Trigger de Auditoria Imutável
-- Arquivo: database/triggers/audit_trigger.sql
-- ==============================================================

-- Função genérica que grava no audit_log com hash encadeado SHA-256
CREATE OR REPLACE FUNCTION fn_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    v_hash_anterior VARCHAR(64);
    v_dados_antes   JSONB;
    v_dados_depois  JSONB;
    v_hash_atual    VARCHAR(64);
    v_payload       TEXT;
BEGIN
    -- Pegar o último hash para encadeamento
    SELECT hash_atual INTO v_hash_anterior
    FROM audit_log
    ORDER BY id DESC
    LIMIT 1;

    IF v_hash_anterior IS NULL THEN
        v_hash_anterior := 'GENESIS_BLOCK_SST_ESOCIAL_GOV';
    END IF;

    -- Montar dados antes e depois
    IF TG_OP = 'INSERT' THEN
        v_dados_antes  := NULL;
        v_dados_depois := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        v_dados_antes  := to_jsonb(OLD);
        v_dados_depois := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        v_dados_antes  := to_jsonb(OLD);
        v_dados_depois := NULL;
    END IF;

    -- Payload para o hash atual: hash_anterior + tabela + operação + timestamp + dados
    v_payload := v_hash_anterior
        || TG_TABLE_NAME
        || TG_OP
        || NOW()::TEXT
        || COALESCE(v_dados_depois::TEXT, v_dados_antes::TEXT, '');

    v_hash_atual := encode(digest(v_payload, 'sha256'), 'hex');

    INSERT INTO audit_log (
        tabela,
        operacao,
        registro_id,
        empresa_id,
        dados_antes,
        dados_depois,
        hash_anterior,
        hash_atual
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN (v_dados_antes->>'id')::UUID
             ELSE (v_dados_depois->>'id')::UUID END,
        CASE WHEN TG_OP = 'DELETE' THEN (v_dados_antes->>'empresa_id')::UUID
             ELSE (v_dados_depois->>'empresa_id')::UUID END,
        v_dados_antes,
        v_dados_depois,
        v_hash_anterior,
        v_hash_atual
    );

    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Aplicar trigger nas tabelas principais
CREATE OR REPLACE TRIGGER trg_audit_documentos
    AFTER INSERT OR UPDATE OR DELETE ON documentos_tecnicos
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE OR REPLACE TRIGGER trg_audit_agentes
    AFTER INSERT OR UPDATE OR DELETE ON agentes_nocivos
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE OR REPLACE TRIGGER trg_audit_exames
    AFTER INSERT OR UPDATE OR DELETE ON exames_medicos
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE OR REPLACE TRIGGER trg_audit_cat
    AFTER INSERT OR UPDATE OR DELETE ON cat_registros
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

CREATE OR REPLACE TRIGGER trg_audit_ai_validacoes
    AFTER INSERT OR UPDATE OR DELETE ON ai_validacoes
    FOR EACH ROW EXECUTE FUNCTION fn_audit_log();

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION fn_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_updated_at_empresas
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

CREATE OR REPLACE TRIGGER trg_updated_at_documentos
    BEFORE UPDATE ON documentos_tecnicos
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();

CREATE OR REPLACE TRIGGER trg_updated_at_usuarios
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION fn_updated_at();
