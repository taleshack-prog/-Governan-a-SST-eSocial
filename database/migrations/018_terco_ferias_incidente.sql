-- ==============================================================
-- SST ESOCIAL GOV — Migração 018: Terço constitucional de férias como INCIDENTE
-- Base: roteiro Carolina, Módulo 2 — "o terço precisa estar cadastrado como incidente
-- justamente como trava contra falso positivo". STF Tema 985 (RE 1.072.485): o terço
-- constitucional de férias INTEGRA a base de contribuição previdenciária.
-- Sem esta entrada, uma rubrica de terço poderia gerar crédito falso (o erro que mais
-- desmoraliza um relatório). Natureza: ADITIVA (seed de dicionário).
-- ==============================================================

INSERT INTO dicionario_rubrica (slug, descricao, natureza_juridica, tratamento_correto, grau_seguranca, fundamento, condicao)
VALUES (
    'terco_ferias',
    'Terço constitucional de férias (1/3)',
    'remuneratoria',
    'incide',
    'consolidado',
    'STF, Tema 985 (RE 1.072.485), com repercussão geral: o terço constitucional de férias integra a base de cálculo da contribuição previdenciária patronal. Tese perdida pelo contribuinte; NÃO gera crédito. Serve de trava contra falso positivo.',
    'Aplica-se ao terço (1/3) sobre férias gozadas. Não confundir com o abono pecuniário (venda de 1/3 das férias), que tem natureza distinta.'
)
ON CONFLICT (slug) DO NOTHING;
