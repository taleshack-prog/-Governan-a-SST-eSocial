-- 061_rat_devido_anexo_decreto_e_in.sql — AJUSTA
-- OS DOIS ANEXOS NO PERIODO VIGENTE (decisao da Carolina, 28/10).
--
-- O QUE A TELA DIZIA. A partir de 10/2022 a linha do grau trazia so "Anexo I (grau por subclasse
-- CNAE)", sem dizer de que norma. Logo acima, na mesma caixa, estava "IN RFB 2.110/2022, art. 43".
--
-- POR QUE ISSO E AFIRMACAO FALSA, nas palavras dela: "quem ler vai achar que o grau passou a vir
-- de uma Instrucao Normativa a partir de 10/2022, o que nao e verdade. A IN aplica o Decreto, nao
-- o substitui."
--
--   - O Anexo V do Decreto 3.048/99 e a FONTE NORMATIVA do grau. O art. 202, §4º remete a ele, e
--     esse paragrafo esta em vigor nos dois periodos: o Decreto nao mudou em 17/10/2022.
--   - O Anexo I da IN RFB 2.110/2022 e a TABELA OPERACIONAL da Receita, organizada por subclasse
--     do CNAE, com que a IN aplica aquele anexo.
--
-- Os dois passam a ser citados, cada um com o nome da sua norma.
--
-- POR QUE O PERIODO ANTERIOR NAO MUDA. Ate 16/10/2022 nao ha dois anexos a citar: a IN 971/2009
-- nao tinha tabela propria — o art. 72, §1º, I remetia a "Relacao de Atividades Preponderantes e
-- Correspondentes Graus de Risco", que e o proprio Anexo V do RPS (decisao dela em 24/10,
-- migration 050). Um periodo cita um anexo, o outro cita dois, e e assim que esta certo.
--
-- O QUE NAO ENTRA AQUI. A citacao do Decreto, na linha de cima, fica como esta: "art. 202, §§ 3º
-- e 4º", sem repetir o Anexo V. Ela descartou a propria proposta de embuti-lo ali depois de ver a
-- tela com a linha "Grau de risco" ja separada: "citar o Anexo V duas vezes nao acrescenta nada".
--
-- ALCANCE. A tela do enquadramento e a memoria de calculo imprimem este MESMO campo — a memoria
-- sob o rotulo "Grau de risco:", e a tela passou a usar o mesmo rotulo em 28/10. Nao ha segunda
-- redacao a sincronizar.
--
-- Idempotente: so altera a linha que ainda esta com o texto antigo.
BEGIN;

UPDATE fundamentacao_campo
   SET anexo = 'Decreto 3.048/99, Anexo V; IN RFB 2.110/2022, Anexo I (grau por subclasse CNAE)'
 WHERE campo = 'rat_devido'
   AND vigencia_inicio = DATE '2022-10-17'
   AND anexo = 'Anexo I (grau por subclasse CNAE)';

COMMIT;

-- Conferencia depois de aplicar (esperado: UM anexo no periodo antigo, DOIS no vigente):
--   SELECT to_char(vigencia_inicio,'DD/MM/YYYY') AS desde,
--          coalesce(to_char(vigencia_fim,'DD/MM/YYYY'),'vigente') AS ate, anexo
--     FROM fundamentacao_campo WHERE campo = 'rat_devido' ORDER BY vigencia_inicio;
--
--   01/07/2020 a 16/10/2022 -> Anexo V do Decreto 3.048/99 (Relação de Atividades Preponderantes
--                              e Graus de Risco)
--   17/10/2022 vigente      -> Decreto 3.048/99, Anexo V; IN RFB 2.110/2022, Anexo I (grau por
--                              subclasse CNAE)
--
-- EM ABERTO, para ela decidir (nao tocado aqui): o campo 'atividade_preponderante' tem, na linha
-- vigente, o mesmo 'Anexo I (grau por subclasse CNAE)' sem nome de norma. Esse campo nao aparece
-- na tela do enquadramento, mas e impresso na memoria de calculo, e a leitura ambigua e a mesma.
