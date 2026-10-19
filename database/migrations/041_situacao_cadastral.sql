-- 041_situacao_cadastral.sql
-- Carolina, 19/10, item 8: a situacao cadastral deixa de ser recado de tela e passa a ser DADO
-- DE CALCULO, delimitando a janela de apuracao ao lado da abertura e do encerramento.
--
-- O DEFEITO. A consulta publica ja devolvia a situacao ("ATIVA") e a exibia dentro de uma
-- mensagem TRANSITORIA, que desaparece ao salvar. O dado se perdia. E empresa BAIXADA, SUSPENSA
-- ou INAPTA tem a janela limitada do mesmo modo que a encerrada — nao faz sentido apurar
-- competencia posterior a baixa.
--
-- DUAS DATAS, de proposito:
--   situacao_cadastral_data — a data DA SITUACAO, informada pela Receita (quando a empresa foi
--                             baixada/suspensa/declarada inapta). E dado da fonte.
--   situacao_cadastral_em   — quando NOS apuramos isso. E a procedencia, no mesmo espirito do
--                             consultado_em: o laudo precisa dizer de quando e a informacao.
--
-- NADA PRESUMIDO. Se a situacao nao for ATIVA e a Receita nao informar a data, a janela NAO e
-- recortada por adivinhacao: a competencia vai a conferencia. Fechar a janela numa data inventada
-- produziria omissao de competencias devidas, que e tao grave quanto apurar competencia indevida.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS situacao_cadastral      VARCHAR(40),
    ADD COLUMN IF NOT EXISTS situacao_cadastral_data DATE,
    ADD COLUMN IF NOT EXISTS situacao_cadastral_em   TIMESTAMPTZ;

COMMENT ON COLUMN empresas.situacao_cadastral IS
    'Situacao na Receita: ATIVA | BAIXADA | SUSPENSA | INAPTA | NULA. Delimita a janela de '
    'apuracao quando diferente de ATIVA.';
COMMENT ON COLUMN empresas.situacao_cadastral_data IS
    'Data da situacao, informada pela fonte. Limite superior da janela quando a situacao nao e '
    'ATIVA. Ausente => a competencia vai a conferencia, nunca a uma data presumida.';
COMMENT ON COLUMN empresas.situacao_cadastral_em IS
    'Quando a situacao foi apurada por nos (procedencia, como consultado_em).';

-- ---- Fundamentacao do campo novo, na tabela versionada (nao no codigo da tela) ----
INSERT INTO fundamentacao_campo (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('situacao_cadastral',
  'Lei 5.172/1966 (CTN), art. 142; Decreto 3.048/99, art. 225',
  'IN RFB 2.119/2022 (CNPJ)',
  NULL,
  'Empresa baixada, suspensa ou inapta tem a janela de apuração limitada pela data da situação, do mesmo modo que a encerrada. Situação diferente de ATIVA sem data informada vai à conferência.',
  '2022-12-06', NULL),
 -- Item 4: os campos do enquadramento que vao ao laudo passam a ter icone proprio.
 ('atividade_preponderante',
  'Decreto 3.048/99, art. 202, § 3º; Súmula 351 do STJ',
  'IN RFB 2.110/2022, art. 43',
  'Anexo I (grau por subclasse CNAE)',
  'Preponderante é a atividade que ocupa o maior número de segurados empregados e trabalhadores avulsos NO ESTABELECIMENTO, apurada mês a mês — não a CNAE do cartão CNPJ.',
  '2022-10-17', NULL),
 ('aliquota_efetiva',
  'Lei 8.212/91, art. 22, II; Lei 10.666/2003, art. 10',
  'eSocial, evento S-1005 (aliqRatAjust)',
  NULL,
  'Alíquota efetiva é o RAT devido multiplicado pelo FAP. É a base do recolhimento do GILRAT e o termo correto de comparação com o que a empresa aplicou.',
  '2010-01-01', NULL)
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT campo FROM fundamentacao_campo
--    WHERE campo IN ('situacao_cadastral','atividade_preponderante','aliquota_efetiva')
--    ORDER BY campo;
