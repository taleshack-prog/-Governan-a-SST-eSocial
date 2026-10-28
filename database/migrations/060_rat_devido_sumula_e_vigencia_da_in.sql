-- 060_rat_devido_sumula_e_vigencia_da_in.sql — AJUSTA
-- A FUNDAMENTACAO DO RAT DEVIDO NA PAGINA DO ESTABELECIMENTO (Carolina, 28/10).
--
-- Ela, lendo a tela: "as duas linhas citam a mesma coisa, só a Lei 8.212 e o Decreto 3.048. A
-- segunda ainda diz que o Decreto tem 'redação vigente desde 17/10/2022', o que é falso: o que
-- mudou nessa data foi a Instrução Normativa."
--
-- DUAS CAUSAS, E SO UMA E DE DADO.
--
-- A primeira e de EXIBICAO e se corrige na tela: a IN de cada periodo sempre esteve cadastrada,
-- no campo ato_normativo, e o Anexo V no campo anexo. A pagina lia apenas 'dispositivo' e
-- imprimia so a Lei e o Decreto — por isso as duas vigencias sairam identicas. O dado estava
-- certo; faltava mostra-lo.
--
-- A segunda e de dado, e e o que esta migration resolve:
--   1) a Sumula 351 do STJ entra nas duas vigencias de 'rat_devido'. Ela ja estava em
--      'atividade_preponderante' (migration 050) e faltava aqui, embora a tela do enquadramento
--      cite as duas coisas lado a lado.
--   2) a data de vigencia passa a acompanhar a IN, dentro do proprio campo. "Vigente desde
--      17/10/2022" e verdade sobre a IN 2.110/2022, que entrou em vigor nessa data, e falso
--      sobre o Decreto 3.048/99, que nao foi alterado entao. Com a data escrita junto da IN, a
--      tela nao precisa mais imprimir uma nota generica de vigencia — e era a nota generica,
--      colada ao fim de uma citacao que comecava pelo Decreto, que produzia a afirmacao falsa.
--
-- POR QUE NAO DECOMPUS EM fundamentacao_dispositivo. Seria o caminho mais limpo para ordenar os
-- quatro elementos, mas a Sumula nao tem artigo, paragrafo, inciso nem anexo, e o CHECK daquela
-- tabela (migration 045) exige ao menos um deles. Decompor exigiria relaxar uma constraint
-- aplicada para acomodar um enunciado de sumula, e isso e uma decisao maior do que a correcao
-- pede. Os tres campos existentes dao conta, e a tela passa a imprimi-los em linhas separadas,
-- como a memoria de calculo ja faz.
--
-- Idempotente.
BEGIN;

-- (1) A Sumula nas duas vigencias de rat_devido.
UPDATE fundamentacao_campo
   SET dispositivo = dispositivo || '; Súmula 351 do STJ'
 WHERE campo = 'rat_devido'
   AND dispositivo NOT LIKE '%Súmula 351%';

-- (2) A data de vigencia junto da IN que de fato comecou naquela data.
UPDATE fundamentacao_campo
   SET ato_normativo = 'IN RFB 2.110/2022, art. 43 (vigente desde 17/10/2022)'
 WHERE campo = 'rat_devido'
   AND vigencia_inicio = DATE '2022-10-17'
   AND ato_normativo = 'IN RFB 2.110/2022, art. 43';

COMMIT;

-- Conferencia depois de aplicar (esperado: duas linhas, com INs DIFERENTES e a Sumula nas duas):
--   SELECT vigencia_inicio, vigencia_fim, dispositivo, ato_normativo, anexo
--     FROM fundamentacao_campo WHERE campo = 'rat_devido' ORDER BY vigencia_inicio;
--
--   11/2021 a 09/2022 -> ... §§ 3º e 4º; Súmula 351 do STJ | IN RFB 971/2009, art. 72, §1º, I e II
--   10/2022 em diante -> ... §§ 3º e 4º; Súmula 351 do STJ | IN RFB 2.110/2022, art. 43 (vigente desde 17/10/2022)
