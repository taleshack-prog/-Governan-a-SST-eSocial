-- 049_fundamentacao_periodo_anterior.sql — AJUSTAPREV
-- CITACAO DO PERIODO ANTERIOR A 17/10/2022 (decisao da Carolina, 24/10).
--
-- O PROBLEMA. 'rat_devido' e 'atividade_preponderante' so tinham vigencia a partir de
-- 17/10/2022 — data da IN RFB 2.110/2022, que as duas citacoes invocam. A janela de apuracao
-- da KRETA comeca em 11/2021, entao todas as competencias anteriores ficavam SEM citacao
-- vigente e a memoria de calculo era recusada na emissao, nomeando os meses que faltavam.
--
-- A DECISAO DELA, nas palavras dela: "Para novembro/2021 a 16/10/2022, a citacao e a IN RFB
-- 971/2009, art. 72, §1º, incisos I e II — o inciso I poe o enquadramento como responsabilidade
-- da empresa, mensal, pela atividade preponderante; o inciso II define preponderante pelo maior
-- numero de segurados empregados e trabalhadores avulsos no estabelecimento, com o maior grau
-- prevalecendo no empate. E o mesmo criterio que a IN 2.110/2022 passou a trazer no art. 43:
-- mudou o numero da norma, nao a regra."
--
-- ONDE CADA PARTE ENTRA. A Carolina ditou a citacao como uma frase unica. A tabela separa:
-- 'dispositivo' guarda lei e decreto, 'ato_normativo' guarda a instrucao normativa — e e assim
-- que a linha de 17/10/2022 ja esta cadastrada. Seguir o mesmo padrao faz o texto impresso sair
-- exatamente como ela ditou, e mantem os dois periodos comparaveis entre si.
--
-- VIGENCIA INICIAL — 01/07/2020, e a razao e dela: "O Decreto 10.410/2020 e de 30 de junho de
-- 2020 e a janela da KRETA comeca em novembro de 2021: a redacao do §3º que fala 'em cada
-- estabelecimento' vale do primeiro ao ultimo mes da serie." E essa redacao que o sistema aplica
-- ao apurar por estabelecimento; antes dela o §3º dizia "na empresa", que e outra regra. Comecar
-- antes seria afirmar esta citacao sobre um periodo que ela nao governa. Mesmo inicio ja usado
-- no campo 'obra_cno'.
--
-- DOIS PONTOS REGISTRADOS PARA CONFERENCIA DELA, nao resolvidos aqui:
--
--   1) A SUMULA 351 DO STJ NAO ENTRA NO PERIODO ANTERIOR. A linha vigente de
--      'atividade_preponderante' cita "Decreto 3.048/99, art. 202, § 3º; Sumula 351 do STJ". A
--      redacao que ela ditou para o periodo anterior nao traz a sumula, e traz a Lei 8.212/91 e
--      o § 4º, que a linha vigente nao tem. Gravado COMO ELA ESCREVEU: a citacao e dela, e
--      completar por conta propria seria decidir no lugar de quem assina. Se foi descuido de
--      redacao — a sumula e de 2008 e vale nos dois periodos —, corrige-se com um UPDATE de uma
--      linha. Deixado visivel aqui exatamente para que ela possa dizer.
--
--   2) ANEXO NAO CADASTRADO. A linha vigente aponta "Anexo I (grau por subclasse CNAE)". O anexo
--      correspondente na IN 971/2009 tem outro numero, e a Carolina disse sobre esse ponto:
--      "Prefiro te deixar esperando um dia a te dar um anexo errado dentro de documento
--      assinado." Fica NULL ate ela confirmar.
--
-- FPAS FICA DE FORA DESTA MIGRATION. Ela confirmou que a Lei 8.212/91, art. 94, e o Decreto
-- 3.048/99, art. 274, valem nos dois periodos, e que muda so o anexo da tabela de codigos — que
-- e justamente o numero que ela esta conferindo. Como o FPAS nao participa da recusa de emissao
-- da memoria, nao ha ganho em cadastrar agora uma linha que nascera incompleta: entra inteira
-- quando o anexo vier.
--
-- Idempotente: reaplicar nao duplica linha.
BEGIN;

-- RAT devido
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
SELECT 'rat_devido',
       'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º',
       'IN RFB 971/2009, art. 72, §1º, I e II',
       NULL,
       NULL,
       DATE '2020-07-01',
       DATE '2022-10-16'
 WHERE NOT EXISTS (
     SELECT 1 FROM fundamentacao_campo
      WHERE campo = 'rat_devido' AND vigencia_inicio = DATE '2020-07-01'
 );

-- Atividade preponderante
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
SELECT 'atividade_preponderante',
       'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º',
       'IN RFB 971/2009, art. 72, §1º, I e II',
       NULL,
       NULL,
       DATE '2020-07-01',
       DATE '2022-10-16'
 WHERE NOT EXISTS (
     SELECT 1 FROM fundamentacao_campo
      WHERE campo = 'atividade_preponderante' AND vigencia_inicio = DATE '2020-07-01'
 );

COMMIT;

-- Conferencia 1: as duas vigencias ficam contiguas, sem buraco e sem sobreposicao.
--   esperado, por campo: 01/07/2020 a 16/10/2022  e  17/10/2022 em diante
--
--   SELECT campo, to_char(vigencia_inicio,'DD/MM/YYYY') AS desde,
--          coalesce(to_char(vigencia_fim,'DD/MM/YYYY'),'vigente') AS ate, dispositivo, ato_normativo
--     FROM fundamentacao_campo
--    WHERE campo IN ('rat_devido','atividade_preponderante')
--    ORDER BY campo, vigencia_inicio;
--
-- Conferencia 2 (a que importa): a competencia mais antiga da serie passa a ter citacao.
--
--   SELECT to_char(min(competencia),'MM/YYYY') AS primeira_competencia
--     FROM estabelecimento_enquadramento;
--
--   -- e, para essa data, deve existir UMA linha vigente de rat_devido:
--   SELECT count(*) FROM fundamentacao_campo
--    WHERE campo = 'rat_devido'
--      AND vigencia_inicio <= (SELECT min(competencia) FROM estabelecimento_enquadramento)
--      AND (vigencia_fim IS NULL
--           OR vigencia_fim >= (SELECT min(competencia) FROM estabelecimento_enquadramento));
--   -- esperado: 1
