-- 043_fundamentacao_enquadramento_versionada.sql
-- Tales, 21/10, item 2 da revisao da tela: tirar o (§) do RAT aplicado.
--
-- TRES COISAS. A primeira foi o pedido; as outras duas sao divida que o pedido revelou.
--
-- 1) DELETE de 'rat_aplicado'. O § significa UMA coisa so: "este valor vem de uma norma,
--    clique para ver qual". O RAT aplicado nao vem de norma: e o que a EMPRESA declarou no
--    S-1005, certo ou errado. Com o § ao lado, a tela afirma que a aliquota errada da empresa
--    tem fundamento legal — o contrario exato do que a peca vai sustentar. O marcador correto
--    naquele campo e a procedencia: "declarado no estabelecimento".
--
--    CORRIJO AQUI UMA LINHA MINHA. O comentario da 042 listou "RAT aplicado" entre os campos
--    onde o § caberia. Estava errado, e pelo mesmo motivo que a propria 042 deu para a situacao
--    cadastral: fato declarado nao e numero que decorra de norma. Fica escrito, para a 043 nao
--    revogar calada o fundamento da anterior.
--
--    A REGRA NAO SE PERDE. O conteudo util daquele seed era "aliquota diversa da prevista so e
--    admitida com processo administrativo ou judicial informado", e ela vive onde deve: em
--    enquadramento_situacao.divergencia_amparada(). Regra de validacao nao e fundamentacao de
--    campo — mesma separacao que a 042 fez com a regra de apuracao.
--
-- 2) RENAME de 'fap_aplicado' para 'fap_publicado'. A chave estava pendurada no FAP errado: as
--    duas telas que a usam (espelho da matriz e FAP por ano) exibem o FAP PUBLICADO, e o proprio
--    texto da linha fala de divulgacao anual e de extrato do FAPWeb. Com os dois FAPs lado a
--    lado — publicado e aplicado —, uma chave chamada "aplicado" sobre o valor publicado leva
--    alguem a "consertar" movendo o § para o campo declarado, que e onde ele nao pode estar.
--
--    No mesmo movimento SAI o ato_normativo "Portaria interministerial do FAP do exercicio
--    [A CONFIRMAR]". Marcador de rascunho dentro do icone que existe para ser prova e pior do
--    que icone nenhum. E a portaria do FAP e ANUAL: uma linha unica, com vigencia aberta desde
--    2010, nao consegue citar portaria nenhuma corretamente. Quem quiser a portaria em tela
--    acrescenta uma linha por exercicio — a tabela e versionada para isso. Fica o dispositivo,
--    que vale para qualquer ano.
--
-- 3) SEED das cinco linhas do enquadramento. Elas existiam SO no banco: nenhuma migration as
--    inseria, nao ha seeder em seeds/ nem em scripts/. Ambiente novo levantado a partir de
--    database/migrations/ nascia com as quatro linhas da 035 e SEM § justamente nos campos que
--    vao ao laudo — grau, RAT devido, FAP, aliquota efetiva. Ficam versionadas aqui, com o
--    texto exato que ja estava em uso. Nada reescrito de cabeca: fundamento inventado e pior
--    do que fundamento nenhum, que e a razao de o componente devolver 404 em silencio.
--
--    ESTE SEED CONTRARIA O QUE A 035 DECIDIU, e isso precisa estar escrito. O cabecalho da 035
--    diz: "grau de risco e RAT devido NAO entram aqui; a fundamentacao deles ja e gravada na
--    propria linha apurada (estabelecimento_enquadramento.fund_*)". Alguem inseriu essas linhas
--    a mao depois, fora de migration, e producao passou a ter DUAS fontes para a mesma citacao.
--    A 043 nao escolhe entre elas — so para de fingir que a segunda nao existe, versionando o
--    que ja esta em producao para que dev e prod deixem de divergir no que o laudo cita.
--
--    A ESCOLHA CONTINUA EM ABERTO, e tem consequencia pratica: fund_* fica CONGELADO na
--    competencia apurada e cita o que valia na epoca; fundamentacao_campo e consultada por data
--    e o componente nao envia 'em', entao mostra o dispositivo de HOJE mesmo sobre competencia
--    antiga. Para competencia de 2020 as duas fontes podem divergir — e a certa e a congelada.
--    Decidir isso e trabalho proprio, nao cabe nesta migration.
--
-- Idempotente nos dois sentidos: reexecutavel, e convergente tanto a partir do banco populado a
-- mao quanto de banco zerado. O ON CONFLICT usa uq_fund_campo_vigencia (campo, vigencia_inicio),
-- criado na 035.
BEGIN;

-- (1) Fato declarado nao tem fundamentacao de campo.
DELETE FROM fundamentacao_campo WHERE campo = 'rat_aplicado';

-- (2) A chave passa a dizer o que o campo e. Em banco zerado nao afeta linha nenhuma e o seed
--     abaixo ja cria 'fap_publicado' com ato_normativo nulo: os dois caminhos convergem.
UPDATE fundamentacao_campo
   SET campo = 'fap_publicado',
       ato_normativo = NULL
 WHERE campo = 'fap_aplicado';

-- (3) As cinco linhas do enquadramento, versionadas.
INSERT INTO fundamentacao_campo (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('atividade_preponderante',
  'Decreto 3.048/99, art. 202, § 3º; Súmula 351 do STJ',
  'IN RFB 2.110/2022, art. 43',
  'Anexo I (grau por subclasse CNAE)',
  'Preponderante é a atividade que ocupa o maior número de segurados empregados e trabalhadores avulsos NO ESTABELECIMENTO, apurada mês a mês — não a CNAE do cartão CNPJ.',
  '2022-10-17', NULL),

 ('rat_devido',
  'Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3º e 4º',
  'IN RFB 2.110/2022, art. 43',
  'Anexo I (grau por subclasse CNAE)',
  'O grau de risco deriva da atividade preponderante — a CNAE com o maior número de segurados empregados e trabalhadores avulsos, apurada mês a mês. Não é campo de escolha.',
  '2022-10-17', NULL),

 ('fap_publicado',
  'Lei 10.666/2003, art. 10; Decreto 3.048/99, art. 202-A',
  NULL, NULL,
  'Fator de 0,5000 a 2,0000, multiplicador da alíquota RAT. Divulgado anualmente; o extrato é obtido no FAPWeb. Campo vazio não equivale a 1,0000.',
  '2010-01-01', NULL),

 ('aliquota_efetiva',
  'Lei 8.212/91, art. 22, II; Lei 10.666/2003, art. 10',
  'eSocial, evento S-1005 (aliqRatAjust)',
  NULL,
  'Alíquota efetiva é o RAT devido multiplicado pelo FAP. É a base do recolhimento do GILRAT e o termo correto de comparação com o que a empresa aplicou.',
  '2010-01-01', NULL),

 ('obra_cno',
  'Decreto 3.048/99, art. 202, § 3º-A',
  NULL, NULL,
  'A obra de construção civil é estabelecimento por determinação expressa, com matrícula CNO própria — não se enquadra pelo CNPJ da construtora.',
  '2020-07-01', NULL)
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

-- Conferencia:
--   SELECT campo, vigencia_inicio, vigencia_fim FROM fundamentacao_campo ORDER BY campo, vigencia_inicio;
--     esperado: aliquota_efetiva, atividade_preponderante, cprb (2), fap_publicado, fpas,
--               obra_cno, periodo_apuracao, rat_devido, regime_tributario  -- 10 linhas
--   SELECT count(*) FROM fundamentacao_campo WHERE campo IN ('rat_aplicado','fap_aplicado');  -- esperado: 0
--   SELECT ato_normativo FROM fundamentacao_campo WHERE campo = 'fap_publicado';              -- esperado: NULL

COMMIT;
