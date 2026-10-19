-- 035_fundamentacao_versionada.sql
-- Revisao da Carolina (item 3): a fundamentacao normativa dos campos derivados sai do codigo
-- da interface e passa a ser lida de tabela VERSIONADA.
--
-- O PROBLEMA: hoje as citacoes estao escritas como texto fixo — no .tsx da tela e em literais
-- espalhados no Python. O conteudo esta correto HOJE. A legislacao da CPRB mudou tres vezes em
-- cinco anos; no dia em que mudar de novo, ninguem vai lembrar de editar aquela frase, e o
-- sistema vai exibir fundamento revogado com aparencia de vigente. Isso e pior do que nao
-- exibir fundamento nenhum, porque induz confianca indevida.
--
-- MODELO: uma linha por (campo, vigencia). A consulta pede campo + data e recebe o dispositivo
-- em vigor NAQUELA data. Quando a lei mudar, acrescenta-se uma linha nova e fecha-se a antiga —
-- o historico fica, e documento gerado para competencia antiga continua citando o que valia.
--
-- TABELA DE REFERENCIA (RN-26): global, da curadoria, compartilhada por todos os escritorios.
-- Por isso SEM RLS e SEM escritorio_id, igual a cnae_enquadramento, tabela_fpas e
-- cprb_transicao. Nao contem dado de cliente.
--
-- ONDE ESTA O RESTO: grau de risco e RAT devido NAO entram aqui. A fundamentacao deles ja e
-- gravada na propria linha apurada (estabelecimento_enquadramento.fund_*), que e a mesma tabela
-- versionada que produziu o valor — exatamente o que o pedido exige. Esta tabela cobre os
-- campos cujo valor nao vem do motor: CPRB, regime tributario, FPAS/Terceiros, periodo.
--
-- Idempotente: pode rodar duas vezes.
BEGIN;

CREATE TABLE IF NOT EXISTS fundamentacao_campo (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campo           VARCHAR(40)  NOT NULL,   -- chave usada pela interface (ex.: 'cprb')
    dispositivo     VARCHAR(300) NOT NULL,   -- lei e artigo
    ato_normativo   VARCHAR(300),            -- IN/decreto que regulamenta
    anexo           VARCHAR(120),            -- anexo aplicavel, quando houver
    observacao      VARCHAR(500),            -- nota curta exibida junto, quando util
    vigencia_inicio DATE NOT NULL,
    vigencia_fim    DATE,                    -- NULL = em vigor
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_fund_campo_ordem CHECK (vigencia_fim IS NULL OR vigencia_fim >= vigencia_inicio)
);

CREATE INDEX IF NOT EXISTS idx_fund_campo ON fundamentacao_campo(campo, vigencia_inicio);

-- Unicidade por (campo, vigencia_inicio) para que o seed seja reexecutavel sem duplicar.
CREATE UNIQUE INDEX IF NOT EXISTS uq_fund_campo_vigencia
    ON fundamentacao_campo(campo, vigencia_inicio);

-- ---- Seed: exatamente as citacoes que hoje estao chumbadas no codigo ----
-- CPRB: duas vigencias, que e justamente o caso que motivou o pedido.
INSERT INTO fundamentacao_campo (campo, dispositivo, ato_normativo, anexo, observacao, vigencia_inicio, vigencia_fim)
VALUES
 ('cprb',
  'Lei 12.546/2011, art. 8º e art. 9º, §13',
  NULL, NULL,
  'Opção anual e irretratável por ano-calendário. Até 12/2024 a CPRB substitui integralmente a cota patronal sobre a folha.',
  '2011-12-14', '2024-12-31'),
 ('cprb',
  'Lei 12.546/2011, art. 9º, §13; Lei 14.973/2024, art. 22',
  NULL, NULL,
  'Transição: a partir de 01/2025 a CPRB coexiste com cota patronal parcial e é extinta a partir de 2028. RAT e Terceiros permanecem devidos em qualquer cenário.',
  '2025-01-01', NULL),

 ('regime_tributario',
  'Lei Complementar 123/2006, art. 13 e art. 18, §5º-C',
  NULL, 'Anexo IV',
  'No Simples Nacional a contribuição patronal está incluída no documento único de arrecadação, salvo no Anexo IV, em que é devida separadamente.',
  '2007-07-01', NULL),

 ('fpas',
  'Lei 8.212/91, art. 94; Decreto 3.048/99, art. 274',
  'IN RFB 2.110/2022',
  'Anexo III',
  'O código FPAS determina a composição das contribuições a Terceiros.',
  '2022-10-17', NULL),

 ('periodo_apuracao',
  'Decreto 20.910/1932, art. 1º; CTN, art. 168',
  NULL, NULL,
  'Prazo decadencial/prescricional de cinco anos para repetição do indébito.',
  '1932-01-06', NULL)
ON CONFLICT (campo, vigencia_inicio) DO NOTHING;

-- Leitura para a role da aplicacao. Guardado porque esta migration tambem precisa rodar em
-- banco que ainda nao tenha o Adendo 05 (a tabela e de referencia e nao depende dele).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'radar_app') THEN
        GRANT SELECT ON fundamentacao_campo TO radar_app;
    END IF;
END $$;

COMMIT;

-- Conferencia depois de aplicar (esperado: 2 linhas de CPRB, uma delas com vigencia_fim NULL):
--   SELECT campo, dispositivo, vigencia_inicio, vigencia_fim
--     FROM fundamentacao_campo ORDER BY campo, vigencia_inicio;
