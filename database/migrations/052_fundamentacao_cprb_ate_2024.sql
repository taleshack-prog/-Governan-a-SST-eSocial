-- 052_fundamentacao_cprb_ate_2024.sql — AJUSTA
-- AS DUAS DECISOES QUE A 051 DEIXOU EM ABERTO (Carolina, 26/10, à noite).
--
-- Nenhuma mexe em codigo: a tabela e versionada por data e a tela ja resolve cada § no ano da
-- linha. Corrigida a tabela, a tela e a memoria passam a exibir o certo sozinhas.
--
-- Idempotente: reaplicar nao duplica linha nem dispositivo, e o UPDATE so alcanca a linha que
-- ainda tiver a citacao antiga.
BEGIN;

-- ---------------------------------------------------------------------------------------------
-- (a) SAI O "Lei 14.973/2024, art. 22" DO § DA OPCAO ANUAL.
--
-- Ela: "A opcao anual e irretratavel esta toda no art. 9º, §13, da Lei 12.546/2011. Se voce tiver
-- o texto desse art. 22 e ele tratar da opcao, me manda que eu reavalio."
--
-- CONSULTADO O TEXTO, e o caso e pior do que citacao sobrando. O art. 22 da Lei 14.973/2024 NAO
-- trata da CPRB e NAO altera a Lei 12.546/2011: dispoe sobre creditos nao tributarios de
-- autarquias e fundacoes publicas federais. Quem inclui o art. 9º-A na Lei 12.546/2011 e o art.
-- 1º daquela lei. A citacao apontava para materia alheia dentro de peca assinada por advogado.
--
-- Nao se cadastra "art. 1º" aqui no lugar: a frase fundamentada e a da OPCAO ANUAL, que e o art.
-- 9º, §13, e so. A lei que incluiu o 9º-A ja aparece como nota dos dispositivos da 051, onde ela
-- qualifica o dispositivo citado — que e o lugar dela.
UPDATE fundamentacao_campo
   SET dispositivo = 'Lei 12.546/2011, art. 9º, §13'
 WHERE campo = 'cprb'
   AND vigencia_inicio = DATE '2025-01-01'
   AND dispositivo LIKE '%14.973%';

-- ---------------------------------------------------------------------------------------------
-- (b) O § DAS PROPORCOES PASSA A APARECER NOS ANOS ATE 2024.
--
-- Ela: "Nos anos ate 2024 o § tem que aparecer. Ate 31/12/2024 a substituicao dos incisos I e III
-- e integral, pelos arts. 7º e 8º da Lei 12.546/2011. O 100% e valor que decorre de norma, entao
-- leva § com essa citacao."
--
-- O caput do art. 7º, na redacao vigente: "Ate 31/12/2024, poderao contribuir, com aplicacao das
-- aliquotas previstas no art. 7º-A, sobre o valor da receita bruta [...] em substituicao TOTAL as
-- contribuicoes previstas nos incisos I e III do caput do art. 22 da Lei 8.212/91". E dessa
-- substituicao total que vem o 100% exibido na coluna, e a palavra "total" e o que distingue este
-- periodo do art. 9º-A, que fala em substituicao PARCIAL.
--
-- VIGENCIA EM UMA LINHA SO, de proposito e com ressalva. O art. 7º teve redacoes sucessivas, que
-- foram prorrogando o prazo final ate a Lei 14.973/2024 fixa-lo em 31/12/2024. A citacao — os
-- arts. 7º e 8º — e a mesma em todas elas; o que mudava era a data de encerramento. Se a
-- distincao entre as redacoes vier a importar, sao linhas novas nesta mesma tabela, sem alterar
-- esta: e exatamente para isso que ela e versionada.
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('cprb_proporcao',
  NULL,                      -- decomposta, como a linha de 2025 criada pela 051
  NULL, NULL,
  'Até 31/12/2024 a CPRB substitui integralmente as contribuições dos incisos I e III do art. 22 '
  'da Lei 8.212/91 — é daí que vem o percentual de 100%. RAT e Terceiros permanecem devidos.',
  DATE '2011-12-14', DATE '2024-12-31')
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 1, 'Lei 12.546/2011', '7º e 8º', NULL, NULL, NULL, NULL,
       'substituição total das contribuições dos incisos I e III do art. 22 da Lei 8.212/91'
  FROM fundamentacao_campo f
 WHERE f.campo = 'cprb_proporcao'
   AND f.vigencia_inicio = DATE '2011-12-14'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 1
   );

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT f.campo, f.vigencia_inicio, f.vigencia_fim, f.dispositivo, d.ordem, d.ato, d.artigo
--     FROM fundamentacao_campo f
--     LEFT JOIN fundamentacao_dispositivo d ON d.campo_id = f.id
--    WHERE f.campo LIKE 'cprb%'
--    ORDER BY f.campo, f.vigencia_inicio, d.ordem;
--
-- esperado:
--   cprb                 2011-12-14..2024-12-31  Lei 12.546/2011, art. 8º e art. 9º, §13
--   cprb                 2025-01-01..            Lei 12.546/2011, art. 9º, §13      <- sem o art. 22
--   cprb_decimo_terceiro 2025-01-01..2027-12-31  (decomposta, 2 dispositivos)
--   cprb_proporcao       2011-12-14..2024-12-31  (decomposta, arts. 7º e 8º)        <- nova
--   cprb_proporcao       2025-01-01..2027-12-31  (decomposta, art. 9º-A)
--
-- NOTA PARA A CAROLINA, nao resolvida aqui: a observacao da linha 'cprb' de 2025 ainda descreve a
-- transicao ("a partir de 01/2025 a CPRB coexiste com cota patronal parcial..."). Com o
-- dispositivo reduzido ao art. 9º, §13, e com a transicao tendo campo proprio desde a 051, aquele
-- texto ficou deslocado — mas e redacao dela, e nao se reescreve sem pedido.
