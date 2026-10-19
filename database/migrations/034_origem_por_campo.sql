-- 034_origem_por_campo.sql
-- Revisao da Carolina (item 1): a origem do dado passa a ser POR CAMPO, nao por cadastro.
--
-- O PROBLEMA: 'empresas.origem_cadastro' e um rotulo unico ('consultado' | 'declarado'). Quando
-- o usuario consulta o CNPJ e depois corrige um campo a mao, o cadastro inteiro segue marcado
-- como consultado. A memoria de enquadramento cita a origem dos dados — e passaria a afirmar
-- que o CNAE principal ou a data de abertura vieram da Receita Federal quando vieram do
-- usuario. Afirmacao falsa em peca que pode ser lida por autoridade fiscal.
--
-- A SOLUCAO: uma coluna JSONB em 'empresas' com, por campo, a origem atual, o valor que a
-- consulta devolveu e os horarios. Campo consultado e depois editado vira 'declarado'
-- PRESERVANDO o valor consultado — a diferenca entre os dois e, ela propria, um achado: se o
-- cliente troca o CNAE principal a mao para algo diferente do cadastro oficial, isso fica
-- registrado.
--
-- POR QUE JSONB E NAO TABELA NOVA: a coluna vive dentro de 'empresas' e herda automaticamente a
-- policy de RLS do Adendo 05. Uma tabela nova exigiria repetir escritorio_id, trigger, NOT NULL
-- e policy — mais superficie para o isolamento falhar em silencio, sem ganho nenhum aqui.
--
-- Formato de cada entrada:
--   { "cnae_principal": { "origem": "consultado",
--                         "valor_consultado": "4321500",
--                         "consultado_em": "2026-10-16T20:15:00Z",
--                         "alterado_em": null } }
--
-- A coluna antiga 'origem_cadastro' NAO e removida: segue como resumo grosseiro e e lida por
-- telas que ainda nao conhecem o mapa. Some na migration de limpeza das colunas depreciadas.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS campos_origem JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN empresas.campos_origem IS
    'Origem por campo: {campo: {origem, valor_consultado, consultado_em, alterado_em}}. '
    'Campo consultado e depois editado vira declarado, preservando o valor consultado.';

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT razao_social, campos_origem FROM empresas LIMIT 3;
