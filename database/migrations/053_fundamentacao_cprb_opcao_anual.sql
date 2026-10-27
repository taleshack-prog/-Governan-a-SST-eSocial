-- 053_fundamentacao_cprb_opcao_anual.sql — AJUSTA
-- O ART. 8º SAI DA LINHA DA OPCAO ANUAL ATE 2024 (Carolina, 26/10, à noite).
--
-- Ela, lendo a fundamentacao no fim da memoria: "'Opcao anual (anos 2023, 2024)' cita 'art. 8º e
-- art. 9º, §13'. A opcao anual e so o art. 9º, §13, em qualquer ano, como saiu em 2025. O art. 8º
-- sai dessa linha."
--
-- DE ONDE VEIO O ART. 8º. A linha nasceu no seed da 035, que copiou para a tabela as citacoes que
-- estavam chumbadas no codigo da tela. Naquele texto, "art. 8º e art. 9º, §13" cobria duas coisas
-- ao mesmo tempo: QUEM pode optar e substituir a cota patronal (art. 8º) e COMO a opcao se
-- manifesta e por quanto tempo vale (art. 9º, §13). Enquanto havia um § unico para o bloco
-- inteiro, a mistura passava despercebida.
--
-- POR QUE AGORA ELA APARECE. Desde a 051 cada frase tem o seu campo, e a substituicao — total
-- ate 2024, parcial de 2025 a 2027 — passou a ser fundamentada em 'cprb_proporcao', que ja cita
-- os arts. 7º e 8º no periodo antigo. O art. 8º seguir aqui faz o documento cita-lo em duas
-- linhas, para duas afirmacoes diferentes, e deixa a linha da opcao anual dizendo mais do que a
-- frase que ela fundamenta. A linha de 2025 ja ficou so com o art. 9º, §13 pela 052; esta e a
-- mesma correcao no periodo anterior.
--
-- Idempotente: o UPDATE so alcanca a linha que ainda citar o art. 8º.
BEGIN;

UPDATE fundamentacao_campo
   SET dispositivo = 'Lei 12.546/2011, art. 9º, §13'
 WHERE campo = 'cprb'
   AND vigencia_inicio = DATE '2011-12-14'
   AND dispositivo LIKE '%art. 8º%';

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT campo, vigencia_inicio, vigencia_fim, dispositivo
--     FROM fundamentacao_campo WHERE campo = 'cprb' ORDER BY vigencia_inicio;
--
-- esperado: as duas linhas com 'Lei 12.546/2011, art. 9º, §13' — a mesma citacao em qualquer ano,
-- que e o que ela determinou. As vigencias continuam separadas porque o resto do bloco muda em
-- 2025, e e por elas que 'cprb_proporcao' e 'cprb_decimo_terceiro' se resolvem.
--
-- NOTA PARA A CAROLINA, nao resolvida aqui. As observacoes das duas linhas de 'cprb' — o texto
-- que aparece abaixo da citacao no popover — ainda descrevem a substituicao: a de ate 2024 diz
-- "Ate 12/2024 a CPRB substitui integralmente a cota patronal sobre a folha", e a de 2025 diz
-- "Transicao: a partir de 01/2025 a CPRB coexiste com cota patronal parcial...". Com o dispositivo
-- reduzido ao art. 9º, §13 nas duas, e com a substituicao tendo campo proprio desde a 051, os
-- dois textos ficaram deslocados: descrevem a regra do campo vizinho. Nao se reescreve redacao
-- dela sem pedido.
