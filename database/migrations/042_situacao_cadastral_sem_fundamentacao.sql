-- 042_situacao_cadastral_sem_fundamentacao.sql
-- Carolina, 20/10, item 2: tirar o (§) da situacao cadastral.
--
-- O ERRO ERA MEU, e esta na 041. Eu criei fundamentacao para 'situacao_cadastral' citando
-- CTN art. 142 e Decreto 3.048/99 art. 225. Nenhum dos dois fundamenta a situacao cadastral:
-- o art. 142 do CTN define LANCAMENTO tributario, e a IN RFB 2.119/2022 regula o PROCEDIMENTO
-- do cadastro. Situacao cadastral e FATO do cadastro da Receita — a empresa esta ativa ou nao
-- esta —, nao e numero que decorra de norma.
--
-- POR QUE ISSO IMPORTA e nao e preciosismo de rotulo: o § precisa significar UMA coisa so —
-- "este valor vem de uma norma, clique para ver qual". Se ele tambem aparecer onde nao ha norma,
-- perde o valor exatamente onde ele e prova: nos campos do enquadramento (grau, RAT devido, RAT
-- aplicado, FAP, aliquota efetiva), que vao ao laudo e precisam exibir o dispositivo vigente.
--
-- O campo ja tem o marcador certo, "(consultada)", que e o que ele e: dado de procedencia.
--
-- A REGRA DE APURACAO NAO SE PERDE. O conteudo util daquele seed era a regra ("situacao
-- diferente de ATIVA limita a janela; sem data vai a conferencia"), e ela vive onde deve:
-- em motor_enquadramento.apurar_estabelecimento e no aviso em tela. Regra de apuracao nao e
-- fundamentacao de campo.
--
-- Idempotente. Nao mexe nos demais campos da tabela.
BEGIN;

DELETE FROM fundamentacao_campo WHERE campo = 'situacao_cadastral';

-- Conferencia: deve sobrar SO o enquadramento e o regime; nenhuma linha de situacao_cadastral.
--   SELECT campo, vigencia_inicio, vigencia_fim FROM fundamentacao_campo ORDER BY campo, vigencia_inicio;
--   SELECT count(*) FROM fundamentacao_campo WHERE campo = 'situacao_cadastral';   -- esperado: 0

COMMIT;
