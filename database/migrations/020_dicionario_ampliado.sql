-- 020_dicionario_ampliado.sql
-- Amplia o dicionario de rubricas nas 3 caixas do salario de contribuicao.
-- Caixa 1 (incide/consolidado)   -> TRAVA contra falso positivo (nunca gera credito)
-- Caixa 2 (nao_incide/consolidado)-> CREDITO automatico (jurisprudencia firme)
-- Caixa 3 (condicional/provavel)  -> ALERTA / fila manual (depende da forma de pagamento)
-- Constraints: tratamento_correto in (incide,nao_incide,condicional)
--              grau_seguranca    in (consolidado,provavel,controvertido)
--              natureza_juridica in (remuneratoria,indenizatoria,nao_salarial)

-- ===================== CAIXA 2 : NAO INCIDE (credito) =====================
INSERT INTO dicionario_rubrica
  (slug, descricao, natureza_juridica, tratamento_correto, grau_seguranca, fundamento, condicao, ativo, versao)
VALUES
 ('ferias_indenizadas',
  'Ferias indenizadas e respectivo terco constitucional pagas na rescisao',
  'indenizatoria','nao_incide','consolidado',
  'Art. 28, par. 9, d, Lei 8.212/91; STJ, natureza indenizatoria das ferias nao gozadas convertidas em rescisao. Distingue-se de terco sobre ferias GOZADAS (Tema 985/STF, que incide).',
  NULL, true, 1),

 ('abono_pecuniario_ferias',
  'Abono pecuniario de ferias (venda de 1/3 - art. 143 CLT)',
  'indenizatoria','nao_incide','consolidado',
  'Art. 28, par. 9, e, 6, Lei 8.212/91; art. 143 CLT; STJ - abono de ferias tem natureza indenizatoria.',
  NULL, true, 1),

 ('diarias_viagem',
  'Diarias para viagem',
  'indenizatoria','nao_incide','consolidado',
  'Art. 457, par. 2, CLT (redacao Lei 13.467/2017) - diarias nao integram a remuneracao, independente do valor.',
  NULL, true, 1),

 ('salario_familia',
  'Salario-familia (cota do beneficio previdenciario)',
  'nao_salarial','nao_incide','consolidado',
  'Art. 28, par. 9, a, Lei 8.212/91 - beneficio previdenciario, nao integra salario de contribuicao.',
  NULL, true, 1),

 ('auxilio_creche',
  'Auxilio-creche / reembolso-creche dentro dos parametros legais',
  'indenizatoria','nao_incide','consolidado',
  'Art. 28, par. 9, s, Lei 8.212/91; Sumula 310/STJ - reembolso-creche nao integra o salario de contribuicao.',
  'Somente ate os limites/idade legais e mediante comprovacao de despesa.', true, 1),

 ('indenizacao_rescisoria',
  'Indenizacoes rescisorias (multa 40% FGTS e verbas indenizatorias da rescisao)',
  'indenizatoria','nao_incide','consolidado',
  'Art. 28, par. 9, e, Lei 8.212/91 - verbas de natureza indenizatoria na rescisao nao integram salario de contribuicao.',
  NULL, true, 1)
ON CONFLICT (slug) DO NOTHING;

-- ===================== CAIXA 1 : INCIDE (trava) =====================
INSERT INTO dicionario_rubrica
  (slug, descricao, natureza_juridica, tratamento_correto, grau_seguranca, fundamento, condicao, ativo, versao)
VALUES
 ('decimo_terceiro',
  'Decimo terceiro salario (gratificacao natalina)',
  'remuneratoria','incide','consolidado',
  'Art. 28, par. 7, Lei 8.212/91; Sumula 688/STF - 13o integra o salario de contribuicao (contribuicao em separado).',
  NULL, true, 1),

 ('hora_extra',
  'Horas extras',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91 - contraprestacao pelo trabalho, integra o salario de contribuicao.',
  NULL, true, 1),

 ('adicional_noturno',
  'Adicional noturno',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91 - natureza salarial, integra o salario de contribuicao.',
  NULL, true, 1),

 ('adicional_insalubridade',
  'Adicional de insalubridade',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91; STJ - adicional de insalubridade tem natureza salarial e integra o salario de contribuicao.',
  NULL, true, 1),

 ('adicional_periculosidade',
  'Adicional de periculosidade',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91; STJ - adicional de periculosidade tem natureza salarial e integra o salario de contribuicao.',
  NULL, true, 1),

 ('comissoes',
  'Comissoes e percentagens',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91; art. 457 CLT - integram a remuneracao.',
  NULL, true, 1),

 ('ferias_gozadas',
  'Ferias gozadas e respectivo terco constitucional',
  'remuneratoria','incide','consolidado',
  'Art. 28, I, Lei 8.212/91; Tema 985/STF - o terco de ferias GOZADAS integra o salario de contribuicao (trava; ver rubrica terco_ferias).',
  NULL, true, 1)
ON CONFLICT (slug) DO NOTHING;

-- ===================== CAIXA 3 : CONDICIONAL (alerta / fila manual) =====================
INSERT INTO dicionario_rubrica
  (slug, descricao, natureza_juridica, tratamento_correto, grau_seguranca, fundamento, condicao, ativo, versao)
VALUES
 ('auxilio_alimentacao',
  'Auxilio-alimentacao',
  'nao_salarial','condicional','provavel',
  'Art. 457, par. 2, CLT; art. 28, par. 9, c, Lei 8.212/91 - pago in natura ou via PAT NAO incide; pago em dinheiro/habitual, incide. Analisar forma de pagamento.',
  'NAO incide se in natura ou ticket/PAT. INCIDE se pago em dinheiro.', true, 1),

 ('plr',
  'Participacao nos lucros e resultados (PLR)',
  'nao_salarial','condicional','provavel',
  'Art. 7, XI, CF; Lei 10.101/2000; art. 28, par. 9, j, Lei 8.212/91 - NAO incide se houver acordo previo e ate 2 pagamentos/ano; fora dos requisitos, incide.',
  'NAO incide com acordo previo valido e periodicidade legal (max 2x/ano). INCIDE se mensal/sem acordo.', true, 1),

 ('premios',
  'Premios e gratificacoes',
  'nao_salarial','condicional','provavel',
  'Art. 457, par. 2 e par. 4, CLT (Lei 13.467/2017) - premios por desempenho superior, de forma eventual, NAO integram; se habituais, incide.',
  'NAO incide se eventual e por desempenho. INCIDE se habitual/ajustado.', true, 1),

 ('acordo_trabalhista',
  'Verbas pagas em acordo/reclamatoria trabalhista',
  'remuneratoria','condicional','provavel',
  'Art. 43, par. 1, Lei 8.212/91 - a incidencia segue a natureza das verbas discriminadas; sem discriminacao, presume-se salarial sobre o total. Exige analise manual.',
  'Depende da discriminacao das verbas no acordo. Sem discriminacao -> fila manual (presuncao salarial).', true, 1)
ON CONFLICT (slug) DO NOTHING;
