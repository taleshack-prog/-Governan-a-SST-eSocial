-- 048_regime_autoria.sql — AJUSTAPREV
-- AUTORIA DO REGIME TRIBUTARIO (revisao da Carolina, 23/10).
--
-- POR QUE. Regime, anexo e as duas datas sao DADO DECLARADO — ninguem consulta isso em lugar
-- nenhum, alguem afirma. E o regime e premissa de calculo de toda a janela: no Simples fora do
-- Anexo IV nao ha RAT a apurar, e e essa afirmacao que decide se existe credito.
--
-- Nas palavras dela: "A memoria de calculo afirma o regime de 60 competencias sem dizer quem o
-- afirmou. Questionada a premissa, nao ha a quem atribuir a declaracao."
--
-- Mesmo padrao ja usado em estabelecimento_atividade, onde o quantitativo declarado guarda
-- declarado_por e declarado_em desde a 028.
--
-- empresa_regime ja esta sob RLS (consta da lista das migrations 032a/032b/039), entao aqui
-- so entram as colunas.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresa_regime
    ADD COLUMN IF NOT EXISTS declarado_por VARCHAR(200),
    ADD COLUMN IF NOT EXISTS declarado_em  TIMESTAMPTZ;

COMMENT ON COLUMN empresa_regime.declarado_por IS
    'Quem afirmou este periodo de regime. O regime nao vem de consulta: e declaracao, e a '
    'memoria de calculo se apoia nela para afirmar que ha ou nao RAT a apurar.';
COMMENT ON COLUMN empresa_regime.declarado_em IS
    'Quando a declaracao foi feita. PRESERVADO quando o periodo nao muda: o endpoint apaga e '
    'recria a lista inteira a cada salvamento, e sem preservar, salvar sem alterar nada '
    'reescreveria o nome de quem declarou pelo de quem apenas abriu a tela.';

-- Linhas que ja existem ficam com autoria nula — e e o correto. Nao houve quem declarasse
-- registrado, e preencher com o usuario de hoje seria inventar autor para uma declaracao
-- antiga. A tela mostra o rodape so quando ha autoria; sem ela, nao afirma nada.

COMMIT;

-- Conferencia:
--   SELECT column_name, data_type FROM information_schema.columns
--    WHERE table_name = 'empresa_regime' AND column_name LIKE 'declarado%';
--   -- esperado: declarado_por (character varying) e declarado_em (timestamp with time zone)
