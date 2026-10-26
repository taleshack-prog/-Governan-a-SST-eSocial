-- 051_fundamentacao_cprb_transicao.sql — AJUSTA
-- A CITACAO DE CADA § DO BLOCO CPRB (decisao da Carolina, 26/10).
--
-- O DEFEITO. O bloco CPRB tem quatro §, e os quatro perguntavam pelo mesmo campo, 'cprb'. Como a
-- tabela devolve UMA citacao por campo e data, os quatro exibiam a mesma coisa: "Lei 12.546/2011,
-- art. 9º, §13", que e a regra da OPCAO ANUAL. Dois deles fundamentam as proporcoes da transicao
-- e um fundamenta a regra do decimo terceiro — nenhuma das tres esta no art. 9º, §13.
--
-- Nas palavras dela: "O § do quadro do 13º precisa trazer as duas regras da frase: art. 9º-A, §1º
-- para o 13º, e arts. 7º e 8º para 'RAT e Terceiros sempre devidos'. As proporcoes de 2025 a 2027
-- citam o art. 9º-A, caput. O art. 9º, §13 fica so na frase da opcao anual."
--
-- POR QUE O 13º PRECISA DE DUAS CITACOES. A frase afirma duas coisas de origem distinta. A
-- primeira — os incisos I e III nao alcancam o 13º em 2025, 2026 e 2027 — vem do art. 9º-A, §1º.
-- A segunda — RAT e Terceiros continuam devidos — nao esta la: decorre dos arts. 7º e 8º, que
-- definem que a CPRB substitui APENAS os incisos I e III do art. 22 da Lei 8.212/91. Com uma
-- citacao so, metade da frase fica sem fundamento, na tela e na memoria de calculo, que imprime
-- a mesma frase dentro de peca assinada.
--
-- POR QUE ESTAS DUAS LINHAS NASCEM DECOMPOSTAS. As dez linhas existentes usam o campo legado
-- 'dispositivo', uma string. A 045 criou fundamentacao_dispositivo para o caso em que uma citacao
-- reune dispositivos distintos — e este e exatamente esse caso, declarado pela propria revisao.
-- Escrever "art. 9º-A, §1º; arts. 7º e 8º" numa string seria recriar o problema que aquela tabela
-- existe para resolver, no primeiro caso em que ele aparece de verdade. A leitura ja prefere o
-- decomposto e cai no legado quando nao ha: as dez linhas antigas seguem como estao.
--
-- O QUE ESTA MIGRATION NAO FAZ, de proposito:
--   1) Nao toca na linha 'cprb'. O quadro dela diz "Mantem" para a opcao anual. A linha vigente
--      guarda "Lei 12.546/2011, art. 9º, §13; Lei 14.973/2024, art. 22" — mais do que o quadro
--      mostra. Tirar o art. 22 por conta propria seria decidir leitura juridica sem pedido.
--   2) Nao cria fundamentacao para os anos ate 2024. A coluna "CPRB sobre a receita" tambem
--      aparece em ano antigo, onde mostra 100%, e 100% nao decorre do art. 9º-A. Ate haver
--      decisao, aquele § simplesmente nao aparece naqueles anos — que e a regra ja adotada no
--      projeto: melhor nenhum icone do que fundamento inventado.
--
-- VIGENCIA 01/01/2025 a 31/12/2027. As duas regras nascem com a Lei 14.973/2024 e morrem com a
-- extincao da CPRB em 2028. Fechar a vigencia em 31/12/2027 e o que faz a citacao sumir sozinha
-- quando o regime acabar, em vez de seguir exibida com aparencia de vigente.
--
-- Idempotente: reaplicar nao duplica linha nem dispositivo.
BEGIN;

-- ---------------------------------------------------------------------------------------------
-- (B e C) AS PROPORCOES — art. 9º-A, caput.
--
-- Um campo so para as duas colunas: os percentuais da CPRB e os dos incisos I e III sao as duas
-- metades da mesma regra, fixadas no mesmo caput. Dois campos com conteudo identico divergiriam
-- com o tempo, que e o defeito que esta tabela existe para evitar.
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('cprb_proporcao',
  NULL,                      -- nasce decomposta: ver fundamentacao_dispositivo abaixo
  NULL, NULL,
  'Proporções da transição: 2025 — 80% da alíquota da CPRB e 25% dos incisos I e III sobre a '
  'folha; 2026 — 60% e 50%; 2027 — 40% e 75%. A CPRB é extinta a partir de 2028.',
  DATE '2025-01-01', DATE '2027-12-31')
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

-- ---------------------------------------------------------------------------------------------
-- (D) O DECIMO TERCEIRO — art. 9º-A, §1º, mais os arts. 7º e 8º.
INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('cprb_decimo_terceiro',
  NULL,
  NULL, NULL,
  'A frase reúne duas regras. A não incidência dos incisos I e III sobre o décimo terceiro vale '
  'apenas em 2025, 2026 e 2027. A permanência do RAT e dos Terceiros não decorre dela: decorre '
  'de a CPRB substituir somente os incisos I e III do art. 22 da Lei 8.212/91.',
  DATE '2025-01-01', DATE '2027-12-31')
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

-- ---------------------------------------------------------------------------------------------
-- OS DISPOSITIVOS, em campos separados.
--
-- 'nota' guarda o que qualifica o dispositivo sem fazer parte do endereco dele: a lei que o
-- incluiu, e, no caso dos arts. 7º e 8º, a razao de estarem ali. A montagem da string e da
-- leitura (api/services/fundamentacao.py); aqui so entram as partes.

-- (B e C) art. 9º-A, caput
INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 1, 'Lei 12.546/2011', '9º-A', NULL, NULL, NULL, NULL,
       'caput, incluído pela Lei 14.973/2024'
  FROM fundamentacao_campo f
 WHERE f.campo = 'cprb_proporcao'
   AND f.vigencia_inicio = DATE '2025-01-01'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 1
   );

-- (D) primeiro dispositivo: a regra do 13º
INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 1, 'Lei 12.546/2011', '9º-A', '1º', NULL, NULL, NULL,
       'incluído pela Lei 14.973/2024'
  FROM fundamentacao_campo f
 WHERE f.campo = 'cprb_decimo_terceiro'
   AND f.vigencia_inicio = DATE '2025-01-01'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 1
   );

-- (D) segundo dispositivo: a permanencia do RAT e dos Terceiros
INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 2, 'Lei 12.546/2011', '7º e 8º', NULL, NULL, NULL, NULL,
       'a CPRB substitui apenas os incisos I e III do art. 22 da Lei 8.212/91'
  FROM fundamentacao_campo f
 WHERE f.campo = 'cprb_decimo_terceiro'
   AND f.vigencia_inicio = DATE '2025-01-01'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 2
   );

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT f.campo, f.vigencia_inicio, f.vigencia_fim, d.ordem, d.ato, d.artigo, d.paragrafo, d.nota
--     FROM fundamentacao_campo f
--     JOIN fundamentacao_dispositivo d ON d.campo_id = f.id
--    WHERE f.campo LIKE 'cprb%'
--    ORDER BY f.campo, d.ordem;
--
-- esperado: tres linhas.
--   cprb_proporcao       | 2025-01-01 | 2027-12-31 | 1 | Lei 12.546/2011 | 9º-A    |     | caput, incluido...
--   cprb_decimo_terceiro | 2025-01-01 | 2027-12-31 | 1 | Lei 12.546/2011 | 9º-A    | 1º  | incluido pela...
--   cprb_decimo_terceiro | 2025-01-01 | 2027-12-31 | 2 | Lei 12.546/2011 | 7º e 8º |     | a CPRB substitui...
--
-- e a citacao montada pela leitura:
--   cprb_proporcao       -> Lei 12.546/2011, art. 9º-A (caput, incluído pela Lei 14.973/2024)
--   cprb_decimo_terceiro -> Lei 12.546/2011, art. 9º-A, § 1º (incluído pela Lei 14.973/2024);
--                           Lei 12.546/2011, arts. 7º e 8º (a CPRB substitui apenas os incisos
--                           I e III do art. 22 da Lei 8.212/91)
