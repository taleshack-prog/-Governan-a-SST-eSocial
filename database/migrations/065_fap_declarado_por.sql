-- 065_fap_declarado_por.sql — AJUSTA
-- O FAP PASSA A TER AUTOR (revisao da Carolina, 03/11, ponto 3 do bloco FAP).
--
-- NAS PALAVRAS DELA: "Como em Atividades, o bloco precisa mostrar 'Declarado por... em... as...'".
--
-- O QUE FALTAVA, E NAO ERA SO A TELA. 'estabelecimento_fap' ja gravava 'origem' ('declarado') e
-- 'declarado_em', mas nunca QUEM — a coluna nao existia. E havia um segundo buraco, invisivel na
-- revisao: o endpoint de leitura devolvia apenas {ano, fap}, de modo que ate a data, que ja
-- estava gravada, nunca chegava a tela. Os dois sao corrigidos no mesmo commit.
--
-- POR QUE O NOME E NAO O E-MAIL. _autor() em routers/estabelecimentos.py prefere o nome desde
-- 24/10, e a razao esta escrita la: a mesma pessoa saiu como "Tales Hack" na declaracao do
-- regime e como e-mail na conferencia, e numa peca lida por fiscal duas grafias do mesmo autor
-- sao duas pessoas. 160 caracteres e o mesmo limite de estabelecimento_atividade.declarado_por.
--
-- AS LINHAS ANTIGAS FICAM COM NULL, DE PROPOSITO. Foram gravadas sem autor; nao ha de onde tirar
-- quem as declarou. Preencher com o usuario atual, ou com "sistema", seria atribuir a alguem uma
-- declaracao que nao e dele — dentro de um campo que existe justamente para dizer de quem e. A
-- tela mostra a data sozinha nesses casos, e e a resposta honesta.
--
-- NAO E NULLABLE POR COMODIDADE: e nullable porque "nao se sabe" e um estado real desta coluna, e
-- diferente de "ninguem declarou". Linha nova sempre nasce com autor, pelo codigo.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

ALTER TABLE estabelecimento_fap
    ADD COLUMN IF NOT EXISTS declarado_por VARCHAR(160);

COMMENT ON COLUMN estabelecimento_fap.declarado_por IS
    'Nome de quem declarou o FAP do ano (não o e-mail; ver _autor em routers/estabelecimentos.py). '
    'NULL nas linhas anteriores à migration 065, que foram gravadas sem autor — não se preenche '
    'retroativamente.';

COMMIT;

-- Conferencia depois de aplicar:
--
-- (1) A coluna existe, com o tipo certo e aceitando nulo.
--     esperado: declarado_por | character varying | 160 | YES
--
--   SELECT column_name, data_type, character_maximum_length, is_nullable
--     FROM information_schema.columns
--    WHERE table_name = 'estabelecimento_fap' AND column_name = 'declarado_por';
--
-- (2) Quantas linhas ficaram sem autor (as anteriores a esta migration). Qualquer numero aqui
--     esta certo, inclusive zero; serve para saber o que a tela vai mostrar sem nome.
--
--   SELECT count(*) FILTER (WHERE declarado_por IS NULL) AS sem_autor,
--          count(*) FILTER (WHERE declarado_por IS NOT NULL) AS com_autor,
--          count(*) AS total
--     FROM estabelecimento_fap;
--
-- (3) Depois de salvar um FAP pela tela, a linha daquele ano tem de vir com nome e data:
--
--   SELECT ano_vigencia, valor_fap, origem, declarado_por, declarado_em
--     FROM estabelecimento_fap ORDER BY ano_vigencia;
