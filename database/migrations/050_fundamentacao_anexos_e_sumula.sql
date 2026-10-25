-- 050_fundamentacao_anexos_e_sumula.sql — AJUSTA
-- QUATRO CORRECOES DE CITACAO (decisoes da Carolina, 24/10, itens a, b e c).
--
-- Fecha o que a 049 deixou em aberto de proposito: a sumula que faltava, os anexos que nao foram
-- cadastrados sem confirmacao, a linha do FPAS inteira, e a citacao do regime, que estava larga.
--
-- Idempotente: reaplicar nao duplica nem reescreve o que ja esta correto.
BEGIN;

-- ---------------------------------------------------------------------------------------------
-- (a) SUMULA 351 DO STJ no periodo anterior.
--
-- Ela: "A sumula e de 2008, anterior as duas instrucoes normativas, e interpreta o sistema do
-- SAT/RAT, nao a IN. Foi corte meu na frase, nao decisao."
--
-- Enunciado: "A aliquota de contribuicao para o Seguro de Acidente do Trabalho (SAT) e aferida
-- pelo grau de risco desenvolvido em cada empresa, individualizada pelo seu CNPJ, ou pelo grau de
-- risco da atividade preponderante quando houver apenas um registro."
--
-- A linha vigente (desde 17/10/2022) ja a traz; entra so na linha anterior, criada pela 049.
UPDATE fundamentacao_campo
   SET dispositivo = 'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º; Súmula 351 do STJ'
 WHERE campo = 'atividade_preponderante'
   AND vigencia_inicio = DATE '2020-07-01'
   AND dispositivo NOT LIKE '%Súmula 351%';

-- ---------------------------------------------------------------------------------------------
-- (b1) ANEXO DO RAT NO PERIODO ANTERIOR — e do DECRETO, nao da IN.
--
-- Ela: "A IN 971/2009 nao tinha tabela propria de CNAE para grau de risco: o art. 72, §1º, I,
-- remete a 'Relacao de Atividades Preponderantes e Correspondentes Graus de Risco', que e o
-- Anexo V do RPS. Foi a IN 2.110/2022 que trouxe essa tabela para dentro de si, no Anexo I."
--
-- Por isso as duas linhas de vigencia do MESMO campo citam anexos de normas DIFERENTES — e esta
-- certo assim. Quem ler as duas lado a lado vai estranhar; o comentario existe para que nao seja
-- "uniformizado" depois por quem nao souber disso.
UPDATE fundamentacao_campo
   SET anexo = 'Anexo V do Decreto 3.048/99 (Relação de Atividades Preponderantes e Graus de Risco)'
 WHERE campo IN ('rat_devido', 'atividade_preponderante')
   AND vigencia_inicio = DATE '2020-07-01'
   AND anexo IS NULL;

-- ---------------------------------------------------------------------------------------------
-- (b2) FPAS NO PERIODO ANTERIOR — a linha que a 049 deixou de fora esperando este numero.
--
-- Ela: "Para FPAS, ate 16/10/2022, e a IN RFB 971/2009, Anexo II — Tabela de Aliquotas por
-- Codigos FPAS." E a diferenca estrutural que a tabela precisa comportar: "na IN 971 o codigo e a
-- aliquota estavam juntos no mesmo Anexo II; na IN 2.110/2022 foram separados em Anexo II, que
-- sao os codigos, e Anexo III, que sao as aliquotas. Um periodo cita um anexo, o outro cita dois."
--
-- A lei e o decreto valem nos dois periodos e nao mudam: muda so o anexo da tabela de codigos.
--
-- VIGENCIA INICIAL — 13/11/2009, a DATA DO ATO, que consta do nome da propria norma ("IN RFB nº
-- 971, de 13 de novembro de 2009"). NAO e a data de publicacao no DOU, que nao foi confirmada em
-- fonte oficial na hora de escrever isto. A distincao nao afeta nenhuma competencia que o sistema
-- apura — a janela mais antiga comeca em 11/2021, onze anos depois —, mas fica registrada para
-- nao virar um fato presumido: se a Carolina preferir a data de publicacao, e um UPDATE.
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
SELECT 'fpas',
       'Lei 8.212/91, art. 94; Decreto 3.048/99, art. 274',
       'IN RFB 971/2009',
       'Anexo II (Tabela de Alíquotas por Códigos FPAS — códigos e alíquotas no mesmo anexo)',
       NULL,
       DATE '2009-11-13',
       DATE '2022-10-16'
 WHERE NOT EXISTS (
     SELECT 1 FROM fundamentacao_campo
      WHERE campo = 'fpas' AND vigencia_inicio = DATE '2009-11-13'
 );

-- ---------------------------------------------------------------------------------------------
-- (c) CITACAO DO REGIME — estreita o que estava largo demais.
--
-- Estava: "Lei Complementar 123/2006, art. 13 e art. 18, §5º-C".
--
-- Ela: "O art. 13 tem varios incisos tratando de outros tributos, e o que sustenta a afirmacao e
-- o inciso VI, que poe a contribuicao patronal do art. 22 da Lei 8.212/91 dentro do DAS, com a
-- ressalva das atividades do §5º-C. E o §3º nao pode faltar: e ele que dispensa as contribuicoes
-- a Terceiros. Sem o §3º, a citacao fundamenta METADE da frase que o sistema imprime."
--
-- A frase impressa e "nao ha RAT NEM contribuicoes a Terceiros a apurar neste periodo": o inciso
-- VI responde pelo RAT, o §3º responde por Terceiros, e o §5º-C e a ressalva que separa o Anexo
-- IV. Tres dispositivos para tres afirmacoes.
--
-- NAO e nova vigencia, e correcao da citacao: a norma nao mudou em 2026, a referencia e que
-- apontava largo. Por isso UPDATE na linha existente, e nao uma linha nova.
UPDATE fundamentacao_campo
   SET dispositivo = 'Lei Complementar 123/2006, art. 13, VI e §3º, c/c art. 18, §5º-C'
 WHERE campo = 'regime_tributario'
   AND dispositivo = 'Lei Complementar 123/2006, art. 13 e art. 18, §5º-C';

COMMIT;

-- Conferencia — esperado, por campo:
--
--   atividade_preponderante  01/07/2020 a 16/10/2022   ... §§ 3º e 4º; Súmula 351 do STJ
--                                                      anexo: Anexo V do Decreto 3.048/99
--   atividade_preponderante  17/10/2022 vigente        ... § 3º; Súmula 351 do STJ
--                                                      anexo: Anexo I (grau por subclasse CNAE)
--   rat_devido               01/07/2020 a 16/10/2022   anexo: Anexo V do Decreto 3.048/99
--   rat_devido               17/10/2022 vigente        anexo: Anexo I (grau por subclasse CNAE)
--   fpas                     13/11/2009 a 16/10/2022   IN RFB 971/2009, Anexo II (um anexo)
--   fpas                     17/10/2022 vigente        IN RFB 2.110/2022, Anexos II c/c III (dois)
--   regime_tributario        01/07/2007 vigente        art. 13, VI e §3º, c/c art. 18, §5º-C
--
--   SELECT campo, to_char(vigencia_inicio,'DD/MM/YYYY') AS desde,
--          coalesce(to_char(vigencia_fim,'DD/MM/YYYY'),'vigente') AS ate,
--          dispositivo, coalesce(ato_normativo,'—') AS ato, coalesce(anexo,'—') AS anexo
--     FROM fundamentacao_campo
--    WHERE campo IN ('rat_devido','atividade_preponderante','fpas','regime_tributario')
--    ORDER BY campo, vigencia_inicio;
