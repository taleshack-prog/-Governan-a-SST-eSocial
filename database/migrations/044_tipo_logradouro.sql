-- 044_tipo_logradouro.sql
-- Tales, 21/10, item 2 da revisao da tela: o endereco nao diz se e rua, avenida ou praca.
--
-- O DADO JA CHEGAVA E ERA DESCARTADO. A consulta publica devolve 'descricao_tipo_de_logradouro'
-- como campo PROPRIO, separado do logradouro — e o adaptador lia catorze dos quarenta e oito
-- campos da resposta, sem este. A tela exibia "ALMIRANTE TAMANDARE" e o laudo compunha endereco
-- sem o tipo.
--
-- POR QUE COLUNA NOVA E NAO CONCATENAR NO LOGRADOURO. A Receita separa os dois de proposito, e
-- juntar perde informacao que nao volta: no registro do Banco do Brasil o tipo e "QUADRA" e o
-- logradouro e "SAUN QUADRA 5 BLOCO B TORRE I, II, III" — o tipo nao e prefixo do logradouro,
-- e concatenar produziria "QUADRA SAUN QUADRA 5...". Separados, o laudo compoe o endereco na
-- ordem que quiser e a busca por logradouro nao precisa limpar prefixo.
--
-- RASTREADO COMO OS DEMAIS. O campo entra em CAMPOS_RASTREADOS e ganha marcador de procedencia
-- igual aos outros sete do bloco: consultado na Receita, declarado pelo usuario, ou alterado —
-- veio da consulta e foi editado. Sem isso seria mais um campo editavel sem dizer de onde veio,
-- que e exatamente o defeito que esta rodada fecha.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS tipo_logradouro VARCHAR(40);

COMMENT ON COLUMN empresas.tipo_logradouro IS
    'Tipo do logradouro (RUA, AVENIDA, QUADRA...), campo proprio da consulta publica '
    '(descricao_tipo_de_logradouro). Separado de empresas.endereco de proposito: a fonte '
    'separa, e o tipo nem sempre e prefixo do logradouro.';

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT column_name, data_type FROM information_schema.columns
--    WHERE table_name = 'empresas' AND column_name = 'tipo_logradouro';   -- esperado: 1 linha
