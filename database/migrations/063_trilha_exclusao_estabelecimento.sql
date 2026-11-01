-- 063_trilha_exclusao_estabelecimento.sql — AJUSTA
-- EXCLUIR ESTABELECIMENTO PASSA A EXISTIR, E A TRILHA PRECISA SABER DIZE-LO (Carolina, 01/11).
--
-- O QUE ELA DECIDIU. "Estabelecimento que fechou de verdade e encerrado pela data, nao excluido.
-- Excluir fica para cadastro feito por engano, com as mesmas travas da empresa: recusado se
-- houver competencia conferida ou memoria emitida; restrito ao titular; confirmacao digitando o
-- CNPJ; registrado na trilha do escritorio — quem excluiu, quando, nome e CNPJ. A matriz nao pode
-- ser excluida enquanto houver filial ou obra cadastrada. Nao precisa de 'arquivar'."
--
-- POR QUE NAO HA 'ARQUIVAR' AQUI, e a assimetria com empresa e proposital: o estabelecimento ja
-- tem um caminho para o fechamento real, que e a data de encerramento (e, desde 29/10, o status
-- deriva dela). Arquivar seria um segundo jeito de dizer a mesma coisa — exatamente o defeito que
-- ela apontou quando 'status' e 'data_encerramento' podiam se contradizer.
--
-- DUAS MUDANCAS NA TABELA, as duas aditivas:
--
--   1) O VOCABULARIO. 'evento' e fechado por CHECK desde a 054, de proposito: evento e dado de
--      maquina, nao texto livre. Acrescentar um valor exige recriar a constraint.
--
--   2) DUAS COLUNAS NOVAS, em vez de reaproveitar 'razao_social' e 'cnpj'. Aquelas duas respondem
--      "qual EMPRESA", e continuam respondendo isso tambem nas linhas de exclusao de
--      estabelecimento — sem elas, a linha nao diria de qual cliente se tratava. O nome e o CNPJ
--      do estabelecimento sao outro fato e ganham campo proprio. Enfiar os dois nas mesmas
--      colunas produziria uma trilha em que 'cnpj' as vezes e da empresa e as vezes nao, e quem
--      ler daqui a cinco anos nao teria como saber qual e qual.
--
-- A COLUNA 'evento' CRESCE de 24 para 32. 'estabelecimento_excluido' tem exatamente 24 caracteres
-- e caberia sem folga nenhuma; preferir um apelido curto ('estab_excluido') economizaria o ALTER
-- e custaria clareza na leitura da trilha. O ALTER de ampliacao de varchar no Postgres e mudanca
-- so de catalogo: nao reescreve a tabela.
--
-- Idempotente.
BEGIN;

ALTER TABLE escritorio_evento ALTER COLUMN evento TYPE VARCHAR(32);

ALTER TABLE escritorio_evento
    ADD COLUMN IF NOT EXISTS estabelecimento_nome VARCHAR(300);
ALTER TABLE escritorio_evento
    ADD COLUMN IF NOT EXISTS estabelecimento_cnpj VARCHAR(20);

COMMENT ON COLUMN escritorio_evento.estabelecimento_nome IS
    'Nome do estabelecimento excluído, copiado no ato. Nulo nos eventos de empresa.';
COMMENT ON COLUMN escritorio_evento.estabelecimento_cnpj IS
    'CNPJ (ou matrícula CNO/CAEPF) do estabelecimento excluído, copiado no ato. '
    'Nulo nos eventos de empresa. Não confundir com a coluna cnpj, que é sempre a da empresa.';

ALTER TABLE escritorio_evento
    DROP CONSTRAINT IF EXISTS ck_escritorio_evento_vocabulario;
ALTER TABLE escritorio_evento
    ADD CONSTRAINT ck_escritorio_evento_vocabulario
    CHECK (evento IN ('arquivada', 'restaurada', 'excluida', 'estabelecimento_excluido'));

COMMIT;

-- Conferencia depois de aplicar:
--
--   -- (1) o vocabulario aceita os quatro
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conname = 'ck_escritorio_evento_vocabulario';
--
--   -- (2) as duas colunas existem e o tipo de 'evento' cresceu
--   SELECT column_name, data_type, character_maximum_length
--     FROM information_schema.columns
--    WHERE table_name = 'escritorio_evento'
--      AND column_name IN ('evento', 'estabelecimento_nome', 'estabelecimento_cnpj')
--    ORDER BY column_name;
--
--   esperado: evento varchar(32), estabelecimento_cnpj varchar(20),
--             estabelecimento_nome varchar(300)
--
-- ROLLBACK (se precisar desfazer ANTES de existir linha com o evento novo):
--   BEGIN;
--   ALTER TABLE escritorio_evento DROP CONSTRAINT ck_escritorio_evento_vocabulario;
--   ALTER TABLE escritorio_evento ADD CONSTRAINT ck_escritorio_evento_vocabulario
--       CHECK (evento IN ('arquivada', 'restaurada', 'excluida'));
--   ALTER TABLE escritorio_evento DROP COLUMN estabelecimento_nome;
--   ALTER TABLE escritorio_evento DROP COLUMN estabelecimento_cnpj;
--   COMMIT;
-- Reduzir 'evento' de volta a VARCHAR(24) nao esta aqui de proposito: isso reescreve a tabela e
-- falharia se ja houvesse valor mais longo. Deixar em 32 nao causa dano.
