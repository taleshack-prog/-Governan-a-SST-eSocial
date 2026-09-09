-- ==============================================================
-- SST ESOCIAL GOV — Migração 014: Tabela de Achados (Etapa 3 do v2, fase 3A-3)
-- Base: v2 seção 7 (achado unifica crédito e passivo) + regra de reputação (seção 8).
-- Natureza: ADITIVA.
-- ==============================================================

CREATE TABLE IF NOT EXISTS achado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estabelecimento_id UUID NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    tipo VARCHAR(12) NOT NULL,
    origem_tipo VARCHAR(20) NOT NULL DEFAULT 'rubrica',
    origem_id UUID,
    descricao VARCHAR(300) NOT NULL,
    valor_mensal NUMERIC(14,2),
    valor_retroativo NUMERIC(14,2),
    aliquota_aplicada NUMERIC(6,4),
    grau_seguranca VARCHAR(15),
    data_prescricao_proxima DATE,
    esfera VARCHAR(20),
    prazo_dias INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'aberto',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_achado_tipo CHECK (tipo IN ('credito','passivo','alerta')),
    CONSTRAINT chk_achado_status CHECK (status IN ('aberto','em_analise','encerrado'))
);

CREATE INDEX IF NOT EXISTS idx_achado_estab ON achado(estabelecimento_id);
CREATE INDEX IF NOT EXISTS idx_achado_tipo ON achado(tipo);
CREATE INDEX IF NOT EXISTS idx_achado_status ON achado(status);

COMMENT ON TABLE achado IS 'SST-ESOCIAL-GOV: achados (credito/passivo/alerta) do comparador. Persistido para regua de prescricao (v2 Alt. 5).';
COMMENT ON COLUMN achado.aliquota_aplicada IS 'Aliquota efetiva usada (cota+RATxFAP+Terceiros). Guardada para auditabilidade.';
