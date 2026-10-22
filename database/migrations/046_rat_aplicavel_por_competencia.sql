-- 046_rat_aplicavel_por_competencia.sql
-- Carolina, 21 e 22/10: o regime decide se existe alguma coisa a calcular, e o motor nunca
-- consultou o regime. Teste dela em 22/10: empresa gravada como Simples Nacional, Anexo III,
-- cobrindo toda a janela, e o enquadramento seguiu apurando RAT devido de 3,00%, efetiva de
-- 1,50% e concluindo "a empresa recolheu acima do devido, ha valor a recuperar". Cinquenta e
-- oito competencias afirmando credito que nao existe.
--
-- A REGRA (confirmada por ela): no Simples Nacional a contribuicao patronal do art. 22 da Lei
-- 8.212/91 integra o documento unico de arrecadacao nos Anexos I, II, III e V — e o RAT vai
-- junto, por ser o inciso II daquele artigo —, por forca do art. 13, VI, da LC 123/2006. So as
-- atividades do art. 18, §5o-C, o Anexo IV, ficam de fora, e nelas a patronal e recolhida pela
-- legislacao geral, com RAT e FAP. Nenhum optante deve contribuicoes a Terceiros, em anexo
-- nenhum, por forca do art. 13, §3o.
--
-- Logo: Simples fora do Anexo IV = NAO HA RAT A APURAR naquela competencia. Nao e divergencia
-- zero; e ausencia de alfandega — nao ha aliquota devida a comparar com a aplicada.
--
-- O QUE ESTAS COLUNAS GUARDAM. A competencia passa a registrar se o modulo se aplica e QUAL
-- regime decidiu isso. O regime vai gravado na propria linha, e nao so consultado na hora de
-- exibir, porque a peca precisa dizer o fato e a fonte: "a empresa consta como optante pelo
-- Simples Nacional, Anexo III, conforme ...". Se a linha so soubesse "nao auditada", a peca
-- nao teria o que afirmar.
--
-- O QUE NAO MUDA: a aliquota APLICADA continua gravada mesmo quando o modulo nao se aplica.
-- Empresa do Anexo III que declarou RAT no S-1005 e achado por si so — pode estar recolhendo o
-- que nao deve. O que fica nulo e a devida e a efetiva, e por consequencia a divergencia: nao
-- ha o que comparar.
--
-- A ORIGEM DO REGIME ainda nao entra aqui. A frase da peca muda conforme o regime tenha sido
-- declarado pelo contribuinte ou consultado na base publica, e hoje 'empresa_regime' nao guarda
-- origem, autor nem data. Entra na rodada da procedencia; ate la toda declaracao e do
-- contribuinte, que e a verdade atual, e a coluna abaixo nasce preparada para receber.
--
-- Idempotente.
BEGIN;

ALTER TABLE estabelecimento_enquadramento
    -- TRUE = ha RAT a apurar. FALSE = regime afasta a apuracao naquela competencia.
    -- Default TRUE porque e o caso geral e porque as linhas ja existentes foram apuradas sob a
    -- regra antiga; a reapuracao e que grava o valor correto.
    ADD COLUMN IF NOT EXISTS rat_aplicavel BOOLEAN NOT NULL DEFAULT TRUE,
    -- Regime e anexo VIGENTES na competencia, congelados na linha: e o que a peca cita.
    ADD COLUMN IF NOT EXISTS regime_competencia VARCHAR(30),
    ADD COLUMN IF NOT EXISTS anexo_competencia VARCHAR(10),
    -- consultado | declarado — preenchida quando a procedencia do regime existir.
    ADD COLUMN IF NOT EXISTS regime_origem VARCHAR(16),
    -- Por que nao se aplica, em texto, para a tela e para a peca.
    ADD COLUMN IF NOT EXISTS motivo_inaplicavel VARCHAR(300);

COMMENT ON COLUMN estabelecimento_enquadramento.rat_aplicavel IS
    'FALSE quando o regime afasta a apuracao do RAT na competencia (Simples fora do Anexo IV). '
    'Nao confundir com em_fila: em_fila e pendencia, isto e ausencia de objeto a apurar.';
COMMENT ON COLUMN estabelecimento_enquadramento.regime_competencia IS
    'Regime vigente na competencia, congelado na apuracao: simples|lucro_real|lucro_presumido.';
COMMENT ON COLUMN estabelecimento_enquadramento.anexo_competencia IS
    'Anexo do Simples vigente na competencia (I..V), quando o regime for simples.';
COMMENT ON COLUMN estabelecimento_enquadramento.regime_origem IS
    'Origem da declaracao de regime: consultado|declarado. Decide o tempo verbal da peca — '
    'afirmar que nada era devido so e possivel sobre dado consultado na base publica.';

COMMIT;

-- Conferencia depois de aplicar e de reapurar:
--   SELECT rat_aplicavel, regime_competencia, anexo_competencia, count(*)
--     FROM estabelecimento_enquadramento GROUP BY 1,2,3 ORDER BY 1,2,3;
--   Para a empresa do teste da Carolina (Simples, Anexo III, 11/2021 a 10/2026), esperado:
--   rat_aplicavel = f em todas as competencias da janela, com aliquota_devida NULL.
