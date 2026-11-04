-- 066_rat_aplicado_declarado_por.sql — AJUSTA
-- O RAT APLICADO PASSA A TER AUTOR (revisao da Carolina, 04/11, ponto 2 do bloco RAT aplicado).
--
-- NAS PALAVRAS DELA: "A leitura nao mostra o processo nem a autoria. (...) Precisa mostrar
-- 'Proc. FAP nº…' quando houver, e 'Declarado por… em… as…'."
--
-- O QUE FALTAVA. Diferente do FAP publicado, que ja guardava 'declarado_em' e so nao guardava
-- quem, esta tabela nao tinha NENHUM dos dois: nem autor, nem data da declaracao. O 'created_at'
-- existe, mas e carimbo de insercao de linha — e a tabela e reescrita inteira a cada gravacao
-- (o endpoint apaga os periodos e regrava), entao o created_at de hoje nao diz quando aquele
-- periodo foi declarado, diz quando a lista foi salva pela ultima vez. Nao serve como autoria.
--
-- POR QUE ISTO IMPORTA MAIS AQUI DO QUE NOS OUTROS BLOCOS. Esta linha guarda a aliquota que a
-- empresa diz ter aplicado e o numero do processo que ampara a divergencia. As duas coisas
-- sustentam afirmacao em peca assinada: a primeira e a base do achado, a segunda e o que retira
-- a competencia da conta de credito. Quem declarou cada uma precisa estar escrito.
--
-- AS LINHAS ANTIGAS FICAM COM NULL, de proposito, pelo mesmo motivo da 065: nao ha de onde tirar
-- quem as declarou, e atribuir a alguem uma declaracao que nao e dele, dentro do campo que
-- existe para dizer de quem ela e, seria o pior resultado possivel. A tela omite o nome nesses
-- casos em vez de inventar um.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

ALTER TABLE estabelecimento_rat_aplicado
    ADD COLUMN IF NOT EXISTS declarado_por VARCHAR(160);

ALTER TABLE estabelecimento_rat_aplicado
    ADD COLUMN IF NOT EXISTS declarado_em TIMESTAMPTZ;

COMMENT ON COLUMN estabelecimento_rat_aplicado.declarado_por IS
    'Nome de quem declarou o RAT aplicado do período (não o e-mail; ver _autor em '
    'routers/estabelecimentos.py). NULL nas linhas anteriores à migration 066.';

COMMENT ON COLUMN estabelecimento_rat_aplicado.declarado_em IS
    'Quando o período foi declarado. Distinto de created_at, que é o carimbo de inserção da '
    'linha — a tabela é reescrita inteira a cada gravação, então created_at não data a '
    'declaração.';

COMMIT;

-- Conferencia depois de aplicar:
--
-- (1) As duas colunas existem, com o tipo certo e aceitando nulo.
--     esperado: declarado_em | timestamp with time zone | YES
--               declarado_por | character varying | 160 | YES
--
--   SELECT column_name, data_type, character_maximum_length, is_nullable
--     FROM information_schema.columns
--    WHERE table_name = 'estabelecimento_rat_aplicado'
--      AND column_name IN ('declarado_por','declarado_em')
--    ORDER BY column_name;
--
-- (2) Quantos periodos ficaram sem autor (os anteriores a esta migration):
--
--   SELECT count(*) FILTER (WHERE declarado_por IS NULL) AS sem_autor,
--          count(*) AS total
--     FROM estabelecimento_rat_aplicado;
--
-- (3) Depois de salvar o bloco pela tela, o periodo tem de vir com nome, data e o processo na
--     forma canonica (0000000-00.0000.0.00.0000):
--
--   SELECT inicio, fim, aliquota_rat, fap_aplicado, processo_rat, processo_fap,
--          declarado_por, declarado_em
--     FROM estabelecimento_rat_aplicado ORDER BY inicio;
