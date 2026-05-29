-- ==============================================================
-- SST ESOCIAL GOV — Row Level Security (Multi-Tenant)
-- Arquivo: database/rls/rls_policies.sql
-- ==============================================================

-- Habilitar RLS nas tabelas sensíveis
ALTER TABLE estabelecimentos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE trabalhadores          ENABLE ROW LEVEL SECURITY;
ALTER TABLE vinculos               ENABLE ROW LEVEL SECURITY;
ALTER TABLE documentos_tecnicos    ENABLE ROW LEVEL SECURITY;
ALTER TABLE agentes_nocivos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE exames_medicos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE cat_registros          ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_validacoes          ENABLE ROW LEVEL SECURITY;
ALTER TABLE responsaveis_tecnicos  ENABLE ROW LEVEL SECURITY;

-- Configuração do contexto de tenant (chamado pelo backend ao iniciar sessão)
-- SET app.current_tenant_id = '<uuid_da_empresa>';

-- Política: cada tenant só enxerga seus próprios dados
CREATE POLICY pol_estabelecimentos_tenant ON estabelecimentos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_trabalhadores_tenant ON trabalhadores
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_vinculos_tenant ON vinculos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_documentos_tenant ON documentos_tecnicos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_agentes_tenant ON agentes_nocivos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_exames_tenant ON exames_medicos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_cat_tenant ON cat_registros
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_ai_validacoes_tenant ON ai_validacoes
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY pol_responsaveis_tenant ON responsaveis_tecnicos
    USING (empresa_id = current_setting('app.current_tenant_id', TRUE)::UUID);
