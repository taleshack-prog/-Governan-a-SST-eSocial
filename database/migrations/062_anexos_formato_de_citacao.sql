-- 062_anexos_formato_de_citacao.sql — AJUSTA
-- UM SO FORMATO PARA OS ANEXOS, COM O NOME OFICIAL (decisao da Carolina, 29/10).
--
-- Duas decisoes dela, depois de ver as seis linhas da tela:
--
--   1) FORMATO DE CITACAO: primeiro a norma, depois o anexo. Os dois periodos escreviam o MESMO
--      Anexo V de jeitos diferentes — "Anexo V do Decreto 3.048/99 (...)" num, "Decreto 3.048/99,
--      Anexo V" no outro —, e lado a lado, dentro da mesma caixa, isso parece inconsistencia de
--      sistema.
--
--   2) NOME OFICIAL COMPLETO. O titulo do Anexo V do RPS e "Relacao de Atividades Preponderantes e
--      CORRESPONDENTES Graus de Risco". O texto gravado comia a palavra "Correspondentes": citava
--      um anexo por um nome que nao e o dele.
--
--   3) ANEXO SEMPRE COM O NOME DA NORMA. 'atividade_preponderante' vigente trazia so "Anexo I
--      (grau por subclasse CNAE)". Ela: "uma citacao sem a norma nao diz a qual ato pertence o
--      anexo — e importa ainda mais porque a mesma linha tambem menciona o Decreto, que tem
--      anexos proprios".
--
-- A COLUNA PRECISA CRESCER, E E POR ISSO QUE ESTA MIGRATION COMECA COM UM ALTER.
-- A citacao do periodo vigente do RAT devido, com o nome oficial completo, tem 151 caracteres;
-- 'anexo' e VARCHAR(120) desde a 035. Sem o ALTER o UPDATE nao trunca: ele FALHA, e a migration
-- aborta. Alargar o limite de um varchar no Postgres (>= 9.2) e mudanca so de catalogo — nao
-- reescreve a tabela —, e o modelo em api/models/fundamentacao_campo.py sobe junto, no mesmo
-- commit, para os dois nao divergirem.
--
-- ALCANCE — O QUE ELA PEDIU E O QUE EU ESTENDI. Ela deu o texto exato de tres linhas: as duas de
-- 'rat_devido' e a vigente de 'atividade_preponderante'. A QUARTA — 'atividade_preponderante' no
-- periodo anterior — ela nao citou, e eu apliquei nela o mesmo texto da primeira, pela regra que
-- ela mesma enunciou ("o padrao e o formato de citacao"). As duas sao impressas lado a lado na
-- memoria de calculo: deixar uma no formato antigo recriaria, dentro do documento, exatamente a
-- inconsistencia que esta migration existe para tirar da tela. Fica dito para ela vetar na
-- conferencia, se discordar — e um UPDATE de volta.
--
-- Idempotente: cada UPDATE so alcanca a linha que ainda esta com o texto antigo.
BEGIN;

-- (0) Espaco para a citacao completa.
ALTER TABLE fundamentacao_campo ALTER COLUMN anexo TYPE VARCHAR(200);

COMMENT ON COLUMN fundamentacao_campo.anexo IS
    'Anexo aplicável, no formato de citação: norma primeiro, anexo depois, com o nome oficial. '
    'Quando um período tem dois anexos de normas diferentes, ambos são citados, separados por '
    'ponto e vírgula. 200 caracteres: a citação do RAT devido vigente usa 151.';

-- (1) Periodo anterior dos DOIS campos — mesma fonte, mesmo texto.
--     Antes: 'Anexo V do Decreto 3.048/99 (Relação de Atividades Preponderantes e Graus de Risco)'
UPDATE fundamentacao_campo
   SET anexo = 'Decreto 3.048/99, Anexo V (Relação de Atividades Preponderantes e Correspondentes Graus de Risco)'
 WHERE campo IN ('rat_devido', 'atividade_preponderante')
   AND vigencia_inicio = DATE '2020-07-01'
   AND anexo = 'Anexo V do Decreto 3.048/99 (Relação de Atividades Preponderantes e Graus de Risco)';

-- (2) RAT devido vigente — os dois anexos, no formato novo.
--     Antes: 'Decreto 3.048/99, Anexo V; IN RFB 2.110/2022, Anexo I (grau por subclasse CNAE)' (061)
UPDATE fundamentacao_campo
   SET anexo = 'Decreto 3.048/99, Anexo V (Relação de Atividades Preponderantes e Correspondentes Graus de Risco); IN RFB 2.110/2022, Anexo I (grau por subclasse CNAE)'
 WHERE campo = 'rat_devido'
   AND vigencia_inicio = DATE '2022-10-17'
   AND anexo = 'Decreto 3.048/99, Anexo V; IN RFB 2.110/2022, Anexo I (grau por subclasse CNAE)';

-- (3) Atividade preponderante vigente — a norma na frente do anexo.
--     Texto dela, literal. Sem o parentese do grau: este campo responde por QUAL atividade
--     prepondera, nao pelo grau que dela decorre — o grau e assunto do campo de cima.
--     Antes: 'Anexo I (grau por subclasse CNAE)'
UPDATE fundamentacao_campo
   SET anexo = 'IN RFB 2.110/2022, Anexo I'
 WHERE campo = 'atividade_preponderante'
   AND vigencia_inicio = DATE '2022-10-17'
   AND anexo = 'Anexo I (grau por subclasse CNAE)';

COMMIT;

-- Conferencia depois de aplicar (esperado: UPDATE 2, UPDATE 1, UPDATE 1, e quatro linhas):
--   SELECT campo, to_char(vigencia_inicio,'DD/MM/YYYY') AS desde,
--          coalesce(to_char(vigencia_fim,'DD/MM/YYYY'),'vigente') AS ate, anexo
--     FROM fundamentacao_campo
--    WHERE campo IN ('rat_devido','atividade_preponderante') ORDER BY campo, vigencia_inicio;
--
--   atividade_preponderante  01/07/2020 a 16/10/2022  Decreto 3.048/99, Anexo V (Relação de
--                                                     Atividades Preponderantes e Correspondentes
--                                                     Graus de Risco)
--   atividade_preponderante  17/10/2022 vigente       IN RFB 2.110/2022, Anexo I
--   rat_devido               01/07/2020 a 16/10/2022  (igual a primeira)
--   rat_devido               17/10/2022 vigente       (a primeira) + "; IN RFB 2.110/2022,
--                                                     Anexo I (grau por subclasse CNAE)"
