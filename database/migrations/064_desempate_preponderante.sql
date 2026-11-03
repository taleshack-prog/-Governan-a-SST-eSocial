-- 064_desempate_preponderante.sql — AJUSTA
-- A REGRA DE EMPATE GANHA FUNDAMENTACAO VERSIONADA (decisao da Carolina, 03/11).
--
-- O QUE ELA CORRIGIU. A tela e a memoria ja diziam que, no empate de quantitativo, prevalece o
-- maior grau de risco — mas diziam isso SEM CITAR NADA, e eu havia chamado aquilo de "escolha do
-- sistema". Nao e: e norma. Nas palavras dela, "as duas INs dizem a mesma coisa, entao cada
-- periodo cita a sua".
--
-- POR QUE CAMPO PROPRIO, E NAO DENTRO DE 'atividade_preponderante'.
-- A citacao de 'atividade_preponderante' e impressa SEMPRE. Se o inciso do desempate entrasse
-- nela, a memoria passaria a citar a regra de empate em documento onde empate nenhum houve —
-- afirmar que uma regra foi aplicada quando nao foi, dentro de peca assinada. A exigencia dela e
-- a oposta: "a frase aparece so quando houver empate de fato". Condicao de exibicao diferente
-- pede campo diferente.
--
-- O GANHO DE LER PELA DATA, e nao por uma citacao unica esticada sobre a serie: se houve empate
-- em 09/2022 e outro em 11/2022, 'citacoes_do_periodo' devolve as DUAS citacoes, cada uma
-- governando os seus meses. Uma citacao so, sobre os dois, estaria errada em metade deles.
--
-- AS DUAS VIGENCIAS. Sao as mesmas de 'rat_devido' e 'atividade_preponderante' — corte em
-- 16/10 / 17/10/2022 —, de proposito: campos impressos lado a lado que se partissem em datas
-- diferentes produziriam, dentro do mesmo documento, dois recortes do mesmo periodo.
--
-- PROCEDENCIA DO INCISO NOVO. A duvida dela era se o art. 43, § 1º, II da IN 2.110/2022 e texto
-- de 2022 ou alteracao posterior — o arquivo consultado e a versao vigente, com alteracoes ate a
-- IN 2.321/2026. Conferido no texto consolidado da Receita
-- (normasinternet2.receita.fazenda.gov.br, consulta "vigente", pag. 37/130): aquele texto MARCA
-- alteracoes, 45 vezes, no formato "[Redacao dada pelo(a) IN RFB nº XXXX]", e a IN 2.321/2026
-- alterou QUATRO trechos dentro deste mesmo art. 43 — todos marcados. O inciso II do § 1º nao
-- tem marca nenhuma: so a indicacao de fonte "(Regulamento da Previdencia Social, de 1999,
-- art. 202, § 3º)". E inferencia a partir da convencao de anotacao, nao leitura do DOU de
-- 19/10/2022 — fica registrado como o que e.
--
-- [A CONFIRMAR] COMPETENCIA ANTERIOR A 01/07/2020. A vigencia antiga comeca em 01/07/2020 para
-- acompanhar os campos irmaos, mas a regra de empate existe na IN 971/2009 desde 2009. Numa
-- empresa cujo periodo de apuracao comece antes de 07/2020 e que tenha empate nesses meses, o
-- resolvedor devolvera None — LACUNA — e a frase simplesmente nao sai (nunca texto de reserva).
-- Estender a vigencia para tras exige a data de inicio de vigencia da IN 971/2009, que eu NAO
-- confirmei e por isso nao escrevo aqui. Decisao e data sao dela; e um UPDATE de uma linha.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

-- ---- (1) As duas vigencias do campo ----
--
-- 'dispositivo' (legado) fica NULL de proposito: a citacao desta linha nasce decomposta, que e a
-- forma que a 045 estabeleceu. Quem escreve string montada no banco desfaz o que aquela tabela
-- existe para resolver.
--
-- 'observacao' guarda a PROSA da frase, exatamente como ela a escreveu. Fica no banco, e nao no
-- Python, pelo mesmo motivo que a citacao: no dia em que a redacao mudar, muda-se a linha. O
-- codigo monta "<observacao> (<citacao>)." e nada mais.

INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
SELECT 'desempate_preponderante',
       NULL,
       'IN RFB 971/2009, art. 72, §1º, II, "a"',
       NULL,
       'Empate: prevalece o maior grau de risco',
       DATE '2020-07-01',
       DATE '2022-10-16'
 WHERE NOT EXISTS (
     SELECT 1 FROM fundamentacao_campo
      WHERE campo = 'desempate_preponderante' AND vigencia_inicio = DATE '2020-07-01'
 );

INSERT INTO fundamentacao_campo
    (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
SELECT 'desempate_preponderante',
       NULL,
       'IN RFB 2.110/2022, art. 43, §1º, II',
       NULL,
       'Empate: prevalece o maior grau de risco',
       DATE '2022-10-17',
       NULL
 WHERE NOT EXISTS (
     SELECT 1 FROM fundamentacao_campo
      WHERE campo = 'desempate_preponderante' AND vigencia_inicio = DATE '2022-10-17'
 );

-- ---- (2) Os dispositivos, em campos separados ----
--
-- O montador (api/services/fundamentacao.py) produz, destas partes:
--   antigo:  IN RFB 971/2009, art. 72, § 1º, II, alínea "a"
--   vigente: IN RFB 2.110/2022, art. 43, § 1º, II
-- O formato 'alínea "a"' e o padrao do montador, aprovado por ela em 03/11 — nao o 'a' entre
-- apostrofos da mensagem dela, que era grafia de mensagem, nao de documento.
--
-- 'nota' fica NULL nas duas. A procedencia do inciso vigente esta no cabecalho desta migration,
-- onde e rastro de engenharia; 'nota' imprime dentro da lista de fundamentacao, e la ela
-- qualificaria o dispositivo perante o leitor juridico — nao e o caso.

INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 1, 'IN RFB 971/2009', '72', '1º', 'II', 'a', NULL, NULL
  FROM fundamentacao_campo f
 WHERE f.campo = 'desempate_preponderante'
   AND f.vigencia_inicio = DATE '2020-07-01'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 1
   );

INSERT INTO fundamentacao_dispositivo (campo_id, ordem, ato, artigo, paragrafo, inciso, alinea, anexo, nota)
SELECT f.id, 1, 'IN RFB 2.110/2022', '43', '1º', 'II', NULL, NULL, NULL
  FROM fundamentacao_campo f
 WHERE f.campo = 'desempate_preponderante'
   AND f.vigencia_inicio = DATE '2022-10-17'
   AND NOT EXISTS (
       SELECT 1 FROM fundamentacao_dispositivo d
        WHERE d.campo_id = f.id AND d.ordem = 1
   );

COMMIT;

-- ---- Conferencia depois de aplicar ----
--
-- (1) As duas vigencias, contiguas, sem buraco e sem sobreposicao.
--     esperado: 01/07/2020 a 16/10/2022  e  17/10/2022 vigente
--
--   SELECT to_char(vigencia_inicio,'DD/MM/YYYY') AS desde,
--          coalesce(to_char(vigencia_fim,'DD/MM/YYYY'),'vigente') AS ate,
--          observacao, ato_normativo
--     FROM fundamentacao_campo
--    WHERE campo = 'desempate_preponderante'
--    ORDER BY vigencia_inicio;
--
-- (2) A citacao montada, que e o que sai no documento. Esperado, exatamente:
--     IN RFB 971/2009, art. 72, § 1º, II, alínea "a"
--     IN RFB 2.110/2022, art. 43, § 1º, II
--
--   SELECT to_char(f.vigencia_inicio,'DD/MM/YYYY') AS desde,
--          d.ato || ', art. ' || d.artigo || ', § ' || d.paragrafo || ', ' || d.inciso ||
--          coalesce(', alínea "' || d.alinea || '"', '') AS citacao_esperada
--     FROM fundamentacao_campo f
--     JOIN fundamentacao_dispositivo d ON d.campo_id = f.id
--    WHERE f.campo = 'desempate_preponderante'
--    ORDER BY f.vigencia_inicio;
--
--   A montagem de verdade e a do Python; este SELECT so confere as PARTES gravadas. Quem valida
--   o montador e o teste de sabotagem descrito no commit.
