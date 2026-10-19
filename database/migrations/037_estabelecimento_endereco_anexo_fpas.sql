-- 037_estabelecimento_endereco_anexo_fpas.sql
-- Revisao da Carolina — tela Estabelecimentos, itens 5 e 2.
--
-- ITEM 5 — ENDERECO ESTRUTURADO. No estabelecimento o endereco era um campo de texto unico,
-- enquanto a tela da empresa ja tinha CEP, logradouro, numero, complemento, bairro, cidade e UF
-- com preenchimento automatico pelo CEP. Alem da inconsistencia entre telas, o campo unico
-- impede o preenchimento automatico — e o endereco do estabelecimento ENTRA na memoria de
-- enquadramento, que e peca com peso juridico.
-- As colunas 'endereco' (logradouro), 'cidade' e 'uf' ja existiam e sao reaproveitadas.
--
-- ITEM 2 — CITACAO DO ANEXO DO FPAS. Os codigos FPAS vem do ANEXO II; o ANEXO III traz as
-- aliquotas de Terceiros. O seed da 035 citava so o Anexo III, e a tela exibe os dois dados
-- juntos no dropdown (codigo 507 e 5,80%) — logo a citacao correta menciona ambos. Corrigido
-- aqui, na tabela versionada, que e justamente o motivo de a fundamentacao ter saido do codigo:
-- texto normativo se conserta com UPDATE, nao com deploy.
--
-- Idempotente.
BEGIN;

-- ---- Item 5: endereco estruturado ----
ALTER TABLE estabelecimentos
    ADD COLUMN IF NOT EXISTS cep         VARCHAR(9),
    ADD COLUMN IF NOT EXISTS numero      VARCHAR(20),
    ADD COLUMN IF NOT EXISTS complemento VARCHAR(120),
    ADD COLUMN IF NOT EXISTS bairro      VARCHAR(120);

COMMENT ON COLUMN estabelecimentos.endereco IS
    'Logradouro. Mesma estrutura da tela da empresa; o endereco do estabelecimento entra na '
    'memoria de enquadramento.';

-- ---- Item 2: anexo correto do FPAS ----
UPDATE fundamentacao_campo
   SET anexo = 'Anexo II (códigos) c/c Anexo III (alíquotas)'
 WHERE campo = 'fpas'
   AND anexo = 'Anexo III';

-- ---- Fundamentacao dos campos derivados da tela Estabelecimentos ----
-- Base legal GERAL de cada campo, para o icone na tela. NAO substitui a fundamentacao gravada
-- por competencia em estabelecimento_enquadramento.fund_*: aquela registra a VERSAO exata da
-- tabela que produziu cada valor, e e a que vai na memoria. Esta responde "com base em que
-- este campo existe", na tela, sem ninguem escrever a citacao no codigo da interface.
INSERT INTO fundamentacao_campo (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('rat_devido',
  'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º',
  'IN RFB 2.110/2022, art. 43',
  'Anexo I (grau por subclasse CNAE)',
  'O grau de risco deriva da atividade preponderante — a CNAE com o maior número de segurados empregados e trabalhadores avulsos, apurada mês a mês. Não é campo de escolha.',
  '2022-10-17', NULL),
 ('rat_aplicado',
  'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, § 5º',
  'eSocial, evento S-1005 (aliqRat, fap, aliqRatAjust)',
  NULL,
  'A empresa declara a alíquota RAT e o FAP; o ajustado é o produto dos dois e o próprio eSocial valida essa relação. Alíquota diversa da prevista só é admitida com processo administrativo ou judicial informado.',
  '2018-01-01', NULL),
 ('fap_aplicado',
  'Lei 10.666/2003, art. 10; Decreto 3.048/99, art. 202-A',
  'Portaria interministerial do FAP do exercício [A CONFIRMAR]',
  NULL,
  'Fator de 0,5000 a 2,0000, multiplicador da alíquota RAT. Divulgado anualmente; o extrato é obtido no FAPWeb. Campo vazio não equivale a 1,0000.',
  '2010-01-01', NULL),
 ('obra_cno',
  'Decreto 3.048/99, art. 202, § 3º-A',
  NULL, NULL,
  'A obra de construção civil é estabelecimento por determinação expressa, com matrícula CNO própria — não se enquadra pelo CNPJ da construtora.',
  '2020-07-01', NULL)
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT campo, anexo FROM fundamentacao_campo WHERE campo = 'fpas';
--   SELECT column_name FROM information_schema.columns
--    WHERE table_name = 'estabelecimentos'
--      AND column_name IN ('cep','numero','complemento','bairro','endereco','cidade','uf');
