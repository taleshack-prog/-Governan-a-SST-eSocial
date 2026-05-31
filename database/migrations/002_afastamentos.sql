-- ==============================================================
-- SST ESOCIAL GOV — Migração 002: Módulo Afastamentos
-- Arquivo: database/migrations/002_afastamentos.sql
-- ==============================================================

-- Tabela principal de afastamentos
CREATE TABLE IF NOT EXISTS afastamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    trabalhador_id UUID NOT NULL REFERENCES trabalhadores(id),
    
    -- Dados do afastamento
    tipo VARCHAR(50) NOT NULL, -- doenca, acidente, acidente_trabalho, maternidade, outros
    cid VARCHAR(10),           -- CID-10 do diagnóstico
    cid_descricao VARCHAR(255),
    data_inicio DATE NOT NULL,
    data_prevista_retorno DATE,
    data_retorno_real DATE,
    dias_afastamento INTEGER,
    
    -- Status do caso
    status VARCHAR(50) NOT NULL DEFAULT 'recebido',
    -- recebido, em_analise, pendente, em_andamento, retorno_proximo,
    -- aguardando_confirmacao, encerrado, reaberto
    
    -- Dados previdenciários
    num_atestados INTEGER DEFAULT 0,
    num_indeferimentos INTEGER DEFAULT 0,
    nexo_acidentario BOOLEAN DEFAULT FALSE,
    cat_emitida BOOLEAN DEFAULT FALSE,
    beneficio_inss VARCHAR(10), -- B31, B91, etc
    
    -- Custo estimado
    salario_base DECIMAL(10,2),
    custo_primeiros_15dias DECIMAL(10,2),
    custo_total_estimado DECIMAL(10,2),
    
    -- Responsabilidade
    responsavel_rh_id UUID REFERENCES usuarios(id),
    
    -- Observações
    motivo_informado TEXT,
    observacoes TEXT,
    historico JSONB DEFAULT '[]',
    
    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES usuarios(id)
);

-- Tabela de atestados vinculados ao afastamento
CREATE TABLE IF NOT EXISTS atestados (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    afastamento_id UUID NOT NULL REFERENCES afastamentos(id),
    trabalhador_id UUID NOT NULL REFERENCES trabalhadores(id),
    
    -- Dados do atestado
    data_emissao DATE,
    data_inicio_repouso DATE,
    dias_afastamento INTEGER,
    cid VARCHAR(10),
    cid_descricao VARCHAR(255),
    
    -- Médico
    medico_nome VARCHAR(255),
    medico_crm VARCHAR(50),
    medico_especialidade VARCHAR(100),
    
    -- Validação
    status VARCHAR(50) DEFAULT 'pendente',
    -- pendente, valido, invalido, pendente_complemento
    
    -- Checklist Novo Atestmed (Portarias 13 e 14/2026)
    checklist JSONB DEFAULT '{}',
    -- tem_cid, tem_data_inicio, tem_prazo_dias, tem_assinatura,
    -- tem_crm, tem_identificacao_paciente, legivel, sem_rasuras
    
    -- Validação IA
    ai_validacao_id UUID REFERENCES ai_validacoes(id),
    ai_score DECIMAL(3,2),
    ai_alertas JSONB DEFAULT '[]',
    
    -- Arquivo
    storage_path VARCHAR(500),
    content_hash VARCHAR(64),
    
    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES usuarios(id)
);

-- Tabela de mensagens RH <-> Trabalhador
CREATE TABLE IF NOT EXISTS afastamento_mensagens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    afastamento_id UUID NOT NULL REFERENCES afastamentos(id),
    remetente_id UUID REFERENCES usuarios(id),
    remetente_tipo VARCHAR(20), -- rh, gestor, trabalhador, sistema
    mensagem TEXT NOT NULL,
    lida BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabela de automações/notificações programadas
CREATE TABLE IF NOT EXISTS afastamento_notificacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    afastamento_id UUID NOT NULL REFERENCES afastamentos(id),
    tipo VARCHAR(50), -- lembrete_rh, lembrete_gestor, lembrete_trabalhador, confirmacao_retorno
    dias_antes INTEGER,
    data_programada DATE,
    enviada BOOLEAN DEFAULT FALSE,
    enviada_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_afastamentos_empresa ON afastamentos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_afastamentos_trabalhador ON afastamentos(trabalhador_id);
CREATE INDEX IF NOT EXISTS idx_afastamentos_status ON afastamentos(status);
CREATE INDEX IF NOT EXISTS idx_afastamentos_retorno ON afastamentos(data_prevista_retorno);
CREATE INDEX IF NOT EXISTS idx_atestados_afastamento ON atestados(afastamento_id);

-- Trigger de auditoria
CREATE TRIGGER audit_afastamentos
    AFTER INSERT OR UPDATE OR DELETE ON afastamentos
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_atestados
    AFTER INSERT OR UPDATE OR DELETE ON atestados
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- Comentário
COMMENT ON TABLE afastamentos IS 'SST-ESOCIAL-GOV: Módulo de afastamentos por doença/acidente';
COMMENT ON TABLE atestados IS 'SST-ESOCIAL-GOV: Atestados médicos vinculados a afastamentos';
