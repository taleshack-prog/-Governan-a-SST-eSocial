-- 024_cnae_fpas_sugestao.sql
-- Sugestao de FPAS por SECAO do CNAE (heuristica por setor — NAO e lei).
-- O FPAS nao e determinado pelo Anexo V; depende da atividade. Esta tabela da um
-- palpite por secao (divisao de 2 digitos do CNAE) para PRE-SELECIONAR o FPAS na tela,
-- sempre marcado como "sugerido — confirmar". REQUER VALIDACAO JURIDICA (Carolina).
-- Natureza: ADITIVA. Idempotente (ON CONFLICT DO NOTHING).

CREATE TABLE IF NOT EXISTS cnae_fpas_sugestao (
    secao          CHAR(1)      PRIMARY KEY,         -- A..U (secao CNAE)
    divisao_ini    SMALLINT     NOT NULL,            -- divisao inicial (2 primeiros digitos)
    divisao_fim    SMALLINT     NOT NULL,            -- divisao final
    setor          VARCHAR(120) NOT NULL,
    fpas_sugerido  VARCHAR(4)   NOT NULL,
    observacao     VARCHAR(220),
    fonte          VARCHAR(160) NOT NULL DEFAULT 'Heuristica por secao CNAE — requer validacao juridica'
);

INSERT INTO cnae_fpas_sugestao (secao, divisao_ini, divisao_fim, setor, fpas_sugerido, observacao) VALUES
 ('A', 1, 3,  'Agricultura, pecuaria, producao florestal, pesca e aquicultura', '604', 'Produtor rural PJ; se nao for, rever (pode ser 507/787).'),
 ('B', 5, 9,  'Industrias extrativas',                                          '507', NULL),
 ('C', 10, 33,'Industrias de transformacao',                                    '507', NULL),
 ('D', 35, 35,'Eletricidade e gas',                                             '507', NULL),
 ('E', 36, 39,'Agua, esgoto, residuos e descontaminacao',                       '507', NULL),
 ('F', 41, 43,'Construcao',                                                     '507', 'Construcao civil; conferir enquadramento especifico.'),
 ('G', 45, 47,'Comercio; reparacao de veiculos',                                '515', NULL),
 ('H', 49, 53,'Transporte, armazenagem e correio',                              '620', 'SEST/SENAT p/ transporte rodoviario; rever p/ outros modais.'),
 ('I', 55, 56,'Alojamento e alimentacao',                                       '515', NULL),
 ('J', 58, 63,'Informacao e comunicacao',                                       '515', NULL),
 ('K', 64, 66,'Atividades financeiras, de seguros e servicos relacionados',     '515', 'Setor financeiro pode ter FPAS proprio; validar.'),
 ('L', 68, 68,'Atividades imobiliarias',                                        '515', NULL),
 ('M', 69, 75,'Atividades profissionais, cientificas e tecnicas',               '515', NULL),
 ('N', 77, 82,'Atividades administrativas e servicos complementares',           '515', NULL),
 ('O', 84, 84,'Administracao publica, defesa e seguridade social',              '582', 'Sem contribuicao a terceiros; validar.'),
 ('P', 85, 85,'Educacao',                                                       '515', NULL),
 ('Q', 86, 88,'Saude humana e servicos sociais',                                '515', NULL),
 ('R', 90, 93,'Artes, cultura, esporte e recreacao',                            '515', NULL),
 ('S', 94, 96,'Outras atividades de servicos',                                  '515', NULL),
 ('T', 97, 97,'Servicos domesticos',                                            '515', 'Empregador domestico tem regime proprio; validar.'),
 ('U', 99, 99,'Organismos internacionais e instituicoes extraterritoriais',     '582', 'Isento/sem terceiros; validar.')
ON CONFLICT (secao) DO NOTHING;
