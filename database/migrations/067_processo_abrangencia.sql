-- 067_processo_abrangencia.sql — AJUSTA
-- O PROCESSO GANHA ALCANCE PROPRIO (decisao da Carolina, 05/11).
--
-- O PROBLEMA QUE ELA VIU: "o processo vale para o periodo inteiro do RAT aplicado. A contestacao
-- de FAP costuma ser de um ano de vigencia, e do jeito que esta, um processo sobre o FAP de 2025
-- ampararia tambem 2024 e 2026."
--
-- Era amparo em excesso, e silencioso: o sistema nao tinha como avisar, porque nao sabia que o
-- processo era de um ano so. Achado escondido dentro de peca assinada.
--
-- DUAS FORMAS DIFERENTES, DE PROPOSITO. Ela decidiu assim e a razao e do dominio, nao de
-- conveniencia:
--
--   FAP  -> ANOS de vigencia. O FAP e publicado por ano, e a contestacao e daquele ano. Pedir
--           datas aqui faria o usuario traduzir "contestei o FAP de 2025" em 01/01 a 31/12, com
--           chance de errar a borda.
--   RAT  -> DATAS (competencia inicial e final). Grau de risco nao e publicacao anual: decorre
--           da atividade preponderante, que muda de mes para mes. Um intervalo de meses e a
--           unidade certa.
--
-- O FIM E OPCIONAL nos dois: processo em curso ampara "de 2025 em diante" ou "de 03/2024 em
-- diante", e exigir um fim obrigaria a inventar uma data que ninguem conhece ainda.
--
-- AS COLUNAS SAO NULAVEIS, MAS A REGRA E OBRIGATORIA — e isso nao e contradicao.
-- No banco elas aceitam NULL porque as linhas que ja existem nao tem abrangencia e nao ha de
-- onde tira-la. Elas ficam PENDENTES, visiveis na tela como pendencia, que foi o que ela pediu:
-- "o processo de teste da KRETA nao tem abrangencia. Depois da migration, ele deve aparecer como
-- pendente na edicao. Nao preenchas por mim. Quero ver a trava funcionando."
--
-- A obrigatoriedade vale para QUEM GRAVA, e esta em dois lugares: a validacao da API, que da a
-- mensagem escrita por ela, e as CHECKs abaixo, criadas NOT VALID. NOT VALID e exatamente a
-- ferramenta deste caso: nao examina as linhas existentes, mas passa a exigir a regra em toda
-- insercao e atualizacao. Como o endpoint apaga e regrava os periodos a cada salvamento, a linha
-- pendente da KRETA so volta ao banco depois de preenchida — a trava que ela quer ver.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

ALTER TABLE estabelecimento_rat_aplicado
    ADD COLUMN IF NOT EXISTS processo_rat_inicio     DATE,
    ADD COLUMN IF NOT EXISTS processo_rat_fim        DATE,
    ADD COLUMN IF NOT EXISTS processo_fap_ano_inicio SMALLINT,
    ADD COLUMN IF NOT EXISTS processo_fap_ano_fim    SMALLINT;

-- As CHECKs sao recriadas a cada execucao: nao existe ADD CONSTRAINT IF NOT EXISTS.
ALTER TABLE estabelecimento_rat_aplicado DROP CONSTRAINT IF EXISTS chk_proc_rat_abrangencia;
ALTER TABLE estabelecimento_rat_aplicado DROP CONSTRAINT IF EXISTS chk_proc_fap_abrangencia;
ALTER TABLE estabelecimento_rat_aplicado DROP CONSTRAINT IF EXISTS chk_proc_rat_ordem;
ALTER TABLE estabelecimento_rat_aplicado DROP CONSTRAINT IF EXISTS chk_proc_fap_ordem;

-- Numero informado exige inicio da abrangencia. NOT VALID: as linhas de hoje ficam como estao.
ALTER TABLE estabelecimento_rat_aplicado
    ADD CONSTRAINT chk_proc_rat_abrangencia
    CHECK (processo_rat IS NULL OR processo_rat_inicio IS NOT NULL) NOT VALID;

ALTER TABLE estabelecimento_rat_aplicado
    ADD CONSTRAINT chk_proc_fap_abrangencia
    CHECK (processo_fap IS NULL OR processo_fap_ano_inicio IS NOT NULL) NOT VALID;

-- Fim antes do inicio e sempre erro, inclusive nas linhas antigas — por isso estas sao VALID.
ALTER TABLE estabelecimento_rat_aplicado
    ADD CONSTRAINT chk_proc_rat_ordem
    CHECK (processo_rat_fim IS NULL OR processo_rat_inicio IS NULL
           OR processo_rat_fim >= processo_rat_inicio);

ALTER TABLE estabelecimento_rat_aplicado
    ADD CONSTRAINT chk_proc_fap_ordem
    CHECK (processo_fap_ano_fim IS NULL OR processo_fap_ano_inicio IS NULL
           OR processo_fap_ano_fim >= processo_fap_ano_inicio);

COMMENT ON COLUMN estabelecimento_rat_aplicado.processo_fap_ano_inicio IS
    'Primeiro ano de vigência do FAP que o processo contesta. O FAP é publicado por ano, e a '
    'contestação é daquele ano — por isso ano, e não data.';
COMMENT ON COLUMN estabelecimento_rat_aplicado.processo_fap_ano_fim IS
    'Último ano contestado. NULL significa "em diante": processo ainda em curso.';
COMMENT ON COLUMN estabelecimento_rat_aplicado.processo_rat_inicio IS
    'Primeira competência que o processo do RAT alcança. Datas, e não anos: o grau de risco '
    'decorre da atividade preponderante, que muda de mês para mês.';
COMMENT ON COLUMN estabelecimento_rat_aplicado.processo_rat_fim IS
    'Última competência alcançada. NULL significa "em diante".';

COMMIT;

-- Conferencia depois de aplicar:
--
-- (1) As quatro colunas existem e aceitam nulo:
--
--   SELECT column_name, data_type, is_nullable
--     FROM information_schema.columns
--    WHERE table_name = 'estabelecimento_rat_aplicado'
--      AND column_name LIKE 'processo_%'
--    ORDER BY column_name;
--
-- (2) As quatro CHECKs existem, e as duas de abrangencia estao NOT VALID (convalidated = f):
--
--   SELECT conname, convalidated, pg_get_constraintdef(oid)
--     FROM pg_constraint
--    WHERE conrelid = 'estabelecimento_rat_aplicado'::regclass AND contype = 'c'
--      AND conname LIKE 'chk_proc_%'
--    ORDER BY conname;
--
-- (3) QUAIS LINHAS FICARAM PENDENTES — e o que a tela vai marcar. Na KRETA deve aparecer o
--     processo 5000001-48.2024.4.04.7100 sem abrangencia:
--
--   SELECT inicio, fim, processo_rat, processo_rat_inicio, processo_fap, processo_fap_ano_inicio
--     FROM estabelecimento_rat_aplicado
--    WHERE (processo_rat IS NOT NULL AND processo_rat_inicio IS NULL)
--       OR (processo_fap IS NOT NULL AND processo_fap_ano_inicio IS NULL)
--    ORDER BY inicio;
