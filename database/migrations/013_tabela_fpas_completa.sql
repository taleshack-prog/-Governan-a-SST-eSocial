-- ==============================================================
-- SST ESOCIAL GOV — Migração 013: Carga completa da Tabela FPAS (Etapa 3, fase 3A-2b+)
-- Fonte oficial: Anexo III da IN RFB nº 2.110/2022 (atualiza a IN 971/2009).
-- Coluna: TOTAL TERCEIROS. Prev.Social (20%) e GILRAT (RAT×FAP) sao tratados a parte.
-- Natureza: ADITIVA/UPSERT — completa o que a 012 iniciou.
-- ==============================================================

INSERT INTO tabela_fpas (codigo_fpas, descricao, aliquota_terceiros, fonte, confirmado)
VALUES
 ('507', 'Comercio e industria (regra geral)',                         5.80, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('515', 'Empregador urbano em geral (comercio)',                      5.80, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('523', 'Estabelecimento com atividade especifica (cod. 523)',        2.70, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('531', 'Estabelecimento com atividade especifica (cod. 531)',        5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('540', 'Estabelecimento com atividade especifica (cod. 540)',        5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('558', 'Estabelecimento com atividade especifica (cod. 558)',        5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('566', 'Estabelecimento com atividade especifica (cod. 566)',        4.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('574', 'Estabelecimento com atividade especifica (cod. 574)',        4.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('582', 'Estabelecimento sem contribuicao a terceiros (cod. 582)',    0.00, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('590', 'Estabelecimento com atividade especifica (cod. 590)',        2.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('604', 'Produtor rural pessoa juridica (Terceiros)',                 2.70, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('612', 'Estabelecimento com atividade especifica (cod. 612)',        5.80, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('620', 'Transporte (SEST/SENAT) (cod. 620)',                         2.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('647', 'Estabelecimento com atividade especifica (cod. 647)',        4.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('655', 'Trabalhador temporario (cod. 655)',                          2.50, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('680', 'Estabelecimento com atividade especifica (cod. 680)',        5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('736', 'Cooperativa de credito (cod. 736)',                          2.70, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('787', 'Cooperativa (cod. 787)',                                     5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('795', 'Cooperativa (cod. 795)',                                     7.70, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('825', 'Estabelecimento com atividade especifica (cod. 825)',        5.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('833', 'Estabelecimento com atividade especifica (cod. 833)',        5.80, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('639', 'Regime especial sem Terceiros sobre folha (cod. 639)',       0.00, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('744', 'Produtor rural PF / segurado especial (SENAR sobre receita)',0.20, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('779', 'Regime especial (cod. 779)',                                 0.00, 'IN RFB 2.110/2022 Anexo III', TRUE),
 ('876', 'Estabelecimento sem contribuicao a terceiros (cod. 876)',    0.00, 'IN RFB 2.110/2022 Anexo III', TRUE)
ON CONFLICT (codigo_fpas) DO UPDATE
   SET aliquota_terceiros = EXCLUDED.aliquota_terceiros,
       descricao = EXCLUDED.descricao,
       fonte = EXCLUDED.fonte,
       confirmado = TRUE;
