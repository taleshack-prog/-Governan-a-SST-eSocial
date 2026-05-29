-- ==============================================================
-- SST ESOCIAL GOV — Schema Principal
-- Arquivo: database/migrations/001_initial_schema.sql
-- Banco   : PostgreSQL 16 + pgvector
-- ==============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ==============================================================
-- TABELAS DE DOMÍNIO SST
-- ==============================================================

-- Empresas (multi-tenant)
CREATE TABLE IF NOT EXISTS empresas (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    razao_social        VARCHAR(300) NOT NULL,
    nome_fantasia       VARCHAR(300),
    cnpj                VARCHAR(14) UNIQUE NOT NULL,
    cnae_principal      VARCHAR(7) NOT NULL,
    regime_tributario   VARCHAR(50),
    grau_risco          INT CHECK (grau_risco BETWEEN 1 AND 4),
    ativo               BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Estabelecimentos
CREATE TABLE IF NOT EXISTS estabelecimentos (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id  UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    codigo      VARCHAR(20) NOT NULL,
    nome        VARCHAR(300) NOT NULL,
    cnpj        VARCHAR(14),
    cnae        VARCHAR(7),
    endereco    TEXT,
    cidade      VARCHAR(100),
    uf          CHAR(2),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(empresa_id, codigo)
);

-- Trabalhadores
CREATE TABLE IF NOT EXISTS trabalhadores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
    cpf                 VARCHAR(11) NOT NULL,
    nome                VARCHAR(300) NOT NULL,
    data_nascimento     DATE,
    sexo                CHAR(1) CHECK (sexo IN ('M','F','O')),
    pis_pasep           VARCHAR(11),
    ctps_numero         VARCHAR(20),
    ctps_serie          VARCHAR(10),
    ctps_uf             CHAR(2),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(empresa_id, cpf)
);

-- Vínculos empregatícios
CREATE TABLE IF NOT EXISTS vinculos (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trabalhador_id          UUID NOT NULL REFERENCES trabalhadores(id),
    empresa_id              UUID NOT NULL REFERENCES empresas(id),
    estabelecimento_id      UUID REFERENCES estabelecimentos(id),
    matricula               VARCHAR(50),
    cargo                   VARCHAR(200),
    cbo                     VARCHAR(6),
    data_admissao           DATE NOT NULL,
    data_demissao           DATE,
    tipo_contrato           VARCHAR(30) DEFAULT 'CLT',
    status                  VARCHAR(20) DEFAULT 'ativo' CHECK (status IN ('ativo','inativo','ferias','afastado')),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Perfis de acesso
CREATE TABLE IF NOT EXISTS perfis_padrao (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(50) UNIQUE NOT NULL,
    descricao   TEXT,
    permissoes  JSONB DEFAULT '{}'
);

-- Usuários do sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id      UUID REFERENCES empresas(id),
    email           VARCHAR(254) UNIQUE NOT NULL,
    senha_hash      VARCHAR(256) NOT NULL,
    nome            VARCHAR(200) NOT NULL,
    perfil          VARCHAR(50) DEFAULT 'leitura',
    ativo           BOOLEAN DEFAULT TRUE,
    ultimo_login    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================
-- TABELAS DE DOCUMENTOS SST
-- ==============================================================

-- Documentos técnicos (LTCAT, PGR, PCMSO, ASO, CAT, AET)
CREATE TABLE IF NOT EXISTS documentos_tecnicos (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id                      UUID NOT NULL REFERENCES empresas(id),
    estabelecimento_id              UUID REFERENCES estabelecimentos(id),
    tipo                            VARCHAR(20) NOT NULL CHECK (tipo IN ('LTCAT','PGR','PCMSO','ASO','CAT','AET','OUTRO')),
    titulo                          VARCHAR(500) NOT NULL,
    descricao                       TEXT,
    data_emissao                    DATE NOT NULL,
    data_validade                   DATE,
    responsavel_tecnico_nome        VARCHAR(300),
    responsavel_tecnico_registro    VARCHAR(50),
    responsavel_tecnico_conselho    VARCHAR(20),
    versao                          INT DEFAULT 1,
    status                          VARCHAR(20) DEFAULT 'rascunho' CHECK (status IN ('rascunho','ativo','vencido','substituido')),
    storage_path                    TEXT,
    storage_bucket                  VARCHAR(100),
    content_hash                    VARCHAR(64),
    metadata                        JSONB DEFAULT '{}',
    created_by                      UUID REFERENCES usuarios(id),
    created_at                      TIMESTAMPTZ DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ DEFAULT NOW()
);

-- Responsáveis técnicos
CREATE TABLE IF NOT EXISTS responsaveis_tecnicos (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id              UUID NOT NULL REFERENCES empresas(id),
    nome                    VARCHAR(300) NOT NULL,
    cpf                     VARCHAR(11),
    conselho_profissional   VARCHAR(20) NOT NULL,
    numero_registro         VARCHAR(50) NOT NULL,
    uf_registro             CHAR(2),
    especialidade           VARCHAR(100),
    ativo                   BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================
-- TABELAS eSocial S-2240 / S-2220
-- ==============================================================

-- Agentes nocivos mapeados (Tabela 24 eSocial)
CREATE TABLE IF NOT EXISTS agentes_nocivos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id),
    trabalhador_id      UUID REFERENCES trabalhadores(id),
    vinculo_id          UUID REFERENCES vinculos(id),
    codigo_tabela24     VARCHAR(10) NOT NULL,
    descricao_agente    TEXT NOT NULL,
    nivel_exposicao     VARCHAR(100),
    unidade_medida      VARCHAR(30),
    epc_eficaz          BOOLEAN,
    epi_eficaz          BOOLEAN,
    epi_ca              VARCHAR(20),
    data_inicio         DATE NOT NULL,
    data_fim            DATE,
    documento_origem_id UUID REFERENCES documentos_tecnicos(id),
    trecho_original     TEXT,
    confidence_score    FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    needs_review        BOOLEAN DEFAULT FALSE,
    created_by_ai       BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Exames médicos (ASO)
CREATE TABLE IF NOT EXISTS exames_medicos (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id),
    trabalhador_id      UUID NOT NULL REFERENCES trabalhadores(id),
    vinculo_id          UUID REFERENCES vinculos(id),
    tipo_exame          VARCHAR(30) NOT NULL CHECK (tipo_exame IN ('admissional','periodico','demissional','mudanca_funcao','retorno_trabalho')),
    data_exame          DATE NOT NULL,
    data_validade       DATE,
    medico_nome         VARCHAR(300),
    medico_crm          VARCHAR(20),
    resultado           VARCHAR(20) CHECK (resultado IN ('apto','apto_restricoes','inapto')),
    observacoes         TEXT,
    documento_id        UUID REFERENCES documentos_tecnicos(id),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- CAT — Comunicação de Acidente de Trabalho
CREATE TABLE IF NOT EXISTS cat_registros (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id),
    trabalhador_id      UUID NOT NULL REFERENCES trabalhadores(id),
    numero_cat          VARCHAR(30),
    tipo_cat            VARCHAR(20) CHECK (tipo_cat IN ('inicial','reabertura','comunicacao_obito')),
    data_acidente       TIMESTAMPTZ NOT NULL,
    local_acidente      TEXT,
    tipo_acidente       VARCHAR(100),
    descricao           TEXT,
    cid_principal       VARCHAR(10),
    parte_corpo         VARCHAR(100),
    agente_causador     VARCHAR(200),
    afastamento         BOOLEAN DEFAULT FALSE,
    dias_afastamento    INT,
    status_esocial      VARCHAR(30) DEFAULT 'pendente' CHECK (status_esocial IN ('pendente','enviado','aceito','rejeitado')),
    protocolo_esocial   VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================
-- TABELAS DO AI LAYER
-- ==============================================================

-- Base normativa (NRs, leis, decretos)
CREATE TABLE IF NOT EXISTS base_normativa (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo          VARCHAR(30) UNIQUE NOT NULL,
    tipo            VARCHAR(20) NOT NULL CHECK (tipo IN ('NR','Lei','Decreto','Portaria','eSocial','Outro')),
    titulo          VARCHAR(500) NOT NULL,
    ementa          TEXT,
    data_publicacao DATE,
    data_vigencia   DATE,
    orgao_emissor   VARCHAR(100),
    url_oficial     TEXT,
    ativo           BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks da base normativa para RAG
CREATE TABLE IF NOT EXISTS normativa_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    normativa_id    UUID NOT NULL REFERENCES base_normativa(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    titulo          VARCHAR(500),
    conteudo        TEXT NOT NULL,
    embedding       vector(384),
    tokens          INT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(normativa_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_normativa_chunks_embedding
    ON normativa_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Validações IA
CREATE TABLE IF NOT EXISTS ai_validacoes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    empresa_id          UUID NOT NULL REFERENCES empresas(id),
    documento_id        UUID REFERENCES documentos_tecnicos(id),
    tipo_validacao      VARCHAR(50) NOT NULL,
    status              VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente','processando','concluido','erro')),
    confidence_score    FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    grade_label         VARCHAR(10),
    resultado           JSONB DEFAULT '{}',
    erros               JSONB DEFAULT '[]',
    alertas             JSONB DEFAULT '[]',
    sugestoes           JSONB DEFAULT '[]',
    model_used          VARCHAR(100),
    tokens_used         INT,
    latency_ms          INT,
    needs_human_review  BOOLEAN DEFAULT FALSE,
    reviewed_by         UUID REFERENCES usuarios(id),
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Etapas detalhadas de cada validação IA (pipeline 9 etapas)
CREATE TABLE IF NOT EXISTS ai_validacao_etapas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validacao_id    UUID NOT NULL REFERENCES ai_validacoes(id) ON DELETE CASCADE,
    etapa_numero    INT NOT NULL CHECK (etapa_numero BETWEEN 1 AND 9),
    nome_etapa      VARCHAR(100) NOT NULL,
    status          VARCHAR(20) DEFAULT 'ok' CHECK (status IN ('ok','aviso','erro','pulado')),
    entrada         JSONB,
    saida           JSONB,
    latency_ms      INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Feedback dos usuários sobre outputs da IA
CREATE TABLE IF NOT EXISTS ai_feedback (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    validacao_id    UUID NOT NULL REFERENCES ai_validacoes(id),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id),
    rating          INT CHECK (rating BETWEEN 1 AND 5),
    correto         BOOLEAN,
    comentario      TEXT,
    correcao        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================
-- TRILHA DE AUDITORIA IMUTÁVEL
-- ==============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tabela          VARCHAR(100) NOT NULL,
    operacao        VARCHAR(10) NOT NULL CHECK (operacao IN ('INSERT','UPDATE','DELETE')),
    registro_id     UUID NOT NULL,
    empresa_id      UUID,
    usuario_id      UUID,
    dados_antes     JSONB,
    dados_depois    JSONB,
    ip_address      INET,
    user_agent      TEXT,
    hash_anterior   VARCHAR(64),
    hash_atual      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_audit_log_tabela ON audit_log(tabela);
CREATE INDEX IF NOT EXISTS idx_audit_log_registro ON audit_log(registro_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_empresa ON audit_log(empresa_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documentos_empresa ON documentos_tecnicos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_documentos_tipo ON documentos_tecnicos(tipo);
CREATE INDEX IF NOT EXISTS idx_agentes_trabalhador ON agentes_nocivos(trabalhador_id);
CREATE INDEX IF NOT EXISTS idx_agentes_codigo ON agentes_nocivos(codigo_tabela24);
CREATE INDEX IF NOT EXISTS idx_exames_trabalhador ON exames_medicos(trabalhador_id);
CREATE INDEX IF NOT EXISTS idx_cat_empresa ON cat_registros(empresa_id);
CREATE INDEX IF NOT EXISTS idx_ai_validacoes_documento ON ai_validacoes(documento_id);
CREATE INDEX IF NOT EXISTS idx_vinculos_trabalhador ON vinculos(trabalhador_id);
CREATE INDEX IF NOT EXISTS idx_vinculos_empresa ON vinculos(empresa_id);
