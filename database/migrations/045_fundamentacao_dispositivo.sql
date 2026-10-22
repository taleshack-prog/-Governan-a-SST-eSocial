-- 045_fundamentacao_dispositivo.sql
-- Carolina, 21/10: a tabela guarda ato, artigo, paragrafo, inciso e anexo em campos separados,
-- nunca string montada. "E a string que faz os dois art. 202 colidirem."
--
-- O PROBLEMA DA STRING. 'fundamentacao_campo.dispositivo' guarda hoje coisas como
-- "Lei 8.212/91, art. 22, II; Decreto 3.048/99, art. 202, §§ 3o e 4o". Dentro de um unico
-- texto ha DOIS dispositivos de atos diferentes, e nada permite ao sistema saber disso. Duas
-- consequencias praticas, as duas ja observadas neste projeto:
--
--   1) Colisao. Existem dois "art. 202" no vocabulario do projeto — o do Decreto 3.048/99, que
--      e o nosso, e o da IN RFB 2.110/2022 (alterada pela 2.321/2026), que trata de outra
--      coisa. Em string os dois sao iguais; em campos, nunca se confundem.
--   2) Nada e consultavel. Nao da para perguntar "onde citamos o art. 22 da Lei 8.212?" quando
--      o artigo so existe no meio de uma frase.
--
-- MODELO. Uma citacao tem VARIOS dispositivos, entao e relacao um-para-muitos: a linha de
-- 'fundamentacao_campo' continua sendo a unidade de vigencia (campo + periodo + observacao) e
-- os dispositivos passam a ser linhas filhas, com ordem de exibicao. Montar a string e tarefa
-- da exibicao; o banco guarda as partes.
--
-- O QUE ESTA MIGRATION NAO FAZ: nao fatia as citacoes que ja existem. Separar "§§ 3o e 4o" em
-- dois dispositivos, ou decidir a que artigo o "II" pertence, e leitura juridica — e errar
-- nisso e exatamente o que a estrutura existe para impedir. As dez linhas atuais seguem com o
-- texto como esta, no campo 'dispositivo', que passa a ser LEGADO: a exibicao usa o decomposto
-- quando houver e cai no legado enquanto nao houver. A decomposicao e trabalho da Carolina e
-- nao bloqueia nada.
--
-- POR QUE A COLUNA ANTIGA NAO FOI RENOMEADA: renomear nao e reexecutavel e quebraria a 043,
-- que insere citando o nome atual. A coluna fica, documentada como legado, e perde o NOT NULL
-- para que linha nova possa nascer so com dispositivos estruturados.
--
-- Tabela de REFERENCIA, como a mae: global, da curadoria, sem RLS e sem escritorio_id — nao
-- contem dado de cliente. (Diferente da tabela de historico, que vem depois e nasce com chave
-- de escritorio desde a primeira linha.)
--
-- Idempotente.
BEGIN;

-- Linha nova nasce sem string montada; a antiga continua valendo ate ser decomposta.
ALTER TABLE fundamentacao_campo
    ALTER COLUMN dispositivo DROP NOT NULL;

COMMENT ON COLUMN fundamentacao_campo.dispositivo IS
    'LEGADO (migration 045): citacao como texto corrido, anterior a decomposicao. Exibida '
    'apenas enquanto a linha nao tiver dispositivos em fundamentacao_dispositivo. Linha nova '
    'nao deve usar este campo.';

CREATE TABLE IF NOT EXISTS fundamentacao_dispositivo (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campo_id    UUID NOT NULL REFERENCES fundamentacao_campo(id) ON DELETE CASCADE,
    ordem       SMALLINT NOT NULL DEFAULT 1,     -- ordem de exibicao dentro da citacao
    ato         VARCHAR(120) NOT NULL,           -- "Lei 8.212/1991", "Decreto 3.048/1999"
    artigo      VARCHAR(20),                     -- "22", "202", "13"
    paragrafo   VARCHAR(20),                     -- "3o", "5o-C", "unico"
    inciso      VARCHAR(20),                     -- "II", "VI"
    alinea      VARCHAR(10),                     -- "a", "b"
    anexo       VARCHAR(60),                     -- "Anexo I", "Anexo III"
    nota        VARCHAR(200),                    -- "red. 10.410/2020", quando a redacao importa
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Ato sozinho nao e citacao: sem nenhuma parte abaixo dele nao ha o que apontar.
    CONSTRAINT ck_fund_disp_parte CHECK (
        artigo IS NOT NULL OR paragrafo IS NOT NULL OR inciso IS NOT NULL OR anexo IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_fund_disp_campo ON fundamentacao_dispositivo(campo_id, ordem);
-- Responde "onde citamos o art. 22 da Lei 8.212?", que a string nao respondia.
CREATE INDEX IF NOT EXISTS idx_fund_disp_ato_art ON fundamentacao_dispositivo(ato, artigo);

COMMENT ON TABLE fundamentacao_dispositivo IS
    'Dispositivos de uma citacao, um por linha, em campos separados (migration 045). A string '
    'exibida e montada na leitura.';

COMMIT;

-- Conferencia depois de aplicar:
--   SELECT f.campo, f.dispositivo IS NOT NULL AS legado,
--          (SELECT count(*) FROM fundamentacao_dispositivo d WHERE d.campo_id = f.id) AS dispositivos
--     FROM fundamentacao_campo f ORDER BY f.campo, f.vigencia_inicio;
--   esperado: dez linhas, todas com legado = t e dispositivos = 0 — nada foi fatiado por codigo.
