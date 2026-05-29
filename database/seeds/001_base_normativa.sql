-- ==============================================================
-- SST ESOCIAL GOV — Seeds: Base Normativa + Perfis
-- Arquivo: database/seeds/001_base_normativa.sql
-- ==============================================================

-- Perfis de acesso padrão
INSERT INTO perfis_padrao (nome, descricao, permissoes) VALUES
('admin',               'Acesso total ao sistema',                      '{"all": true}'::JSONB),
('rh',                  'Acesso a dados de recursos humanos',           '{"trabalhadores": true, "vinculos": true}'::JSONB),
('sst',                 'Acesso a módulos de segurança do trabalho',    '{"documentos": true, "agentes": true, "cat": true}'::JSONB),
('saude_ocupacional',   'Acesso a dados de saúde ocupacional',          '{"exames": true, "pcmso": true}'::JSONB),
('juridico',            'Acesso a documentos jurídicos',                '{"documentos": ["read"], "audit": true}'::JSONB),
('leitura',             'Acesso apenas de leitura',                     '{"all": ["read"]}'::JSONB)
ON CONFLICT (nome) DO NOTHING;

-- Base Normativa SST
INSERT INTO base_normativa (codigo, tipo, titulo, ementa, data_publicacao, orgao_emissor) VALUES
('NR-01', 'NR', 'Disposições Gerais e Gerenciamento de Riscos Ocupacionais',
    'Estabelece a obrigatoriedade do Gerenciamento de Riscos Ocupacionais (GRO) e do PGR.',
    '1978-06-08', 'MTE'),
('NR-04', 'NR', 'Serviços Especializados em Engenharia de Segurança e em Medicina do Trabalho',
    'Define a obrigatoriedade e dimensionamento do SESMT.',
    '1978-06-08', 'MTE'),
('NR-06', 'NR', 'Equipamentos de Proteção Individual',
    'Regulamenta a obrigatoriedade de fornecimento e uso de EPIs.',
    '1978-06-08', 'MTE'),
('NR-07', 'NR', 'Programa de Controle Médico de Saúde Ocupacional',
    'Define a obrigatoriedade do PCMSO e dos exames médicos periódicos.',
    '1978-06-08', 'MTE'),
('NR-09', 'NR', 'Avaliação e Controle das Exposições Ocupacionais a Agentes Físicos, Químicos e Biológicos',
    'Obriga a avaliação quantitativa de agentes físicos, químicos e biológicos.',
    '1978-06-08', 'MTE'),
('NR-15', 'NR', 'Atividades e Operações Insalubres',
    'Define limites de tolerância para atividades insalubres.',
    '1978-06-08', 'MTE'),
('NR-17', 'NR', 'Ergonomia',
    'Visa estabelecer parâmetros para adaptação das condições de trabalho ao trabalhador.',
    '1978-06-08', 'MTE'),
('S-2240', 'eSocial', 'Condições Ambientais do Trabalho - Fatores de Risco',
    'Evento eSocial para informar as condições ambientais de trabalho com agentes nocivos (Tabela 24).',
    '2018-01-01', 'RFB/MTE'),
('S-2220', 'eSocial', 'Monitoramento da Saúde do Trabalhador',
    'Evento eSocial para informar os ASOs dos trabalhadores.',
    '2018-01-01', 'RFB/MTE'),
('S-2210', 'eSocial', 'Comunicação de Acidente de Trabalho',
    'Evento eSocial substituto da CAT em papel.',
    '2018-01-01', 'RFB/MTE')
ON CONFLICT (codigo) DO NOTHING;

-- Tabela 24 eSocial — Agentes Nocivos (amostra dos 23 principais usados no sistema)
-- Usada pelo AI Layer / tabela24_matcher.py
CREATE TABLE IF NOT EXISTS tabela24_esocial (
    codigo      VARCHAR(10) PRIMARY KEY,
    grupo       VARCHAR(50) NOT NULL,
    descricao   TEXT NOT NULL,
    tipo_agente VARCHAR(30) NOT NULL CHECK (tipo_agente IN ('fisico','quimico','biologico'))
);

INSERT INTO tabela24_esocial (codigo, grupo, descricao, tipo_agente) VALUES
('01.01.001', 'Grupo 01', 'Ruído acima dos limites de tolerância da NR-15 Anexo I',                                    'fisico'),
('01.02.001', 'Grupo 01', 'Calor acima dos limites de tolerância da NR-15 Anexo III',                                  'fisico'),
('01.03.001', 'Grupo 01', 'Frio abaixo dos limites de tolerância da NR-15 Anexo IX',                                   'fisico'),
('01.04.001', 'Grupo 01', 'Umidade acima dos limites da NR-15 Anexo X',                                                'fisico'),
('01.05.001', 'Grupo 01', 'Radiações ionizantes (raio X, raio gama, etc.)',                                             'fisico'),
('01.06.001', 'Grupo 01', 'Vibrações localizadas em mãos e braços acima dos limites da NR-15 Anexo VIII',              'fisico'),
('01.06.002', 'Grupo 01', 'Vibrações de corpo inteiro acima dos limites da NR-15 Anexo VIII',                          'fisico'),
('01.07.001', 'Grupo 01', 'Pressões hiperbáricas',                                                                      'fisico'),
('02.01.001', 'Grupo 02', 'Arsênio e seus compostos',                                                                   'quimico'),
('02.02.001', 'Grupo 02', 'Chumbo e seus compostos iônicos',                                                            'quimico'),
('02.03.001', 'Grupo 02', 'Cromo hexavalente e seus compostos',                                                         'quimico'),
('02.04.001', 'Grupo 02', 'Benzeno e seus derivados',                                                                   'quimico'),
('02.05.001', 'Grupo 02', 'Mercúrio e seus compostos',                                                                  'quimico'),
('02.06.001', 'Grupo 02', 'Sílica livre cristalizada',                                                                  'quimico'),
('02.07.001', 'Grupo 02', 'Asbesto (amianto) — todos os tipos',                                                         'quimico'),
('02.08.001', 'Grupo 02', 'Poeiras minerais (exceto sílica e amianto)',                                                 'quimico'),
('03.01.001', 'Grupo 03', 'Agentes biológicos: vírus em atividades com risco de contágio',                              'biologico'),
('03.02.001', 'Grupo 03', 'Agentes biológicos: bactérias em atividades com risco de contágio',                         'biologico'),
('03.03.001', 'Grupo 03', 'Agentes biológicos: fungos em atividades com risco de contágio',                            'biologico'),
('03.04.001', 'Grupo 03', 'Agentes biológicos: parasitas em atividades com risco de contágio',                         'biologico'),
('03.05.001', 'Grupo 03', 'Agentes biológicos: coleta/manuseio de lixo urbano',                                        'biologico'),
('03.06.001', 'Grupo 03', 'Agentes biológicos: atividades em cemitérios',                                               'biologico'),
('03.07.001', 'Grupo 03', 'Agentes biológicos: atividades em hospitais/laboratórios com materiais infecciosos',        'biologico')
ON CONFLICT (codigo) DO NOTHING;
