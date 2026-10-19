-- 036_rat_aplicado_desdobrado.sql
-- Revisao da Carolina — tela Estabelecimentos, item 1: o RAT aplicado deixa de ser UM numero e
-- passa a guardar as DUAS origens que o compoem.
--
-- POR QUE. No eSocial, evento S-1005, a empresa declara tres coisas por estabelecimento:
-- aliqRat, fap e aliqRatAjust — e o proprio eSocial valida que a terceira e o produto das duas.
-- Logo o erro NUNCA esta no ajustado: esta no grau de risco ou no fator. Guardando um numero so,
-- o sistema sabia que havia divergencia e nao sabia qual das duas origens a causou. E a pergunta
-- decide a defesa: grau errado se corrige com reenquadramento e memoria de atividade
-- preponderante; FAP errado se corrige com a portaria e o extrato do FAPWeb.
--
-- PROCESSOS. O leiaute do eSocial so aceita aliquota divergente da prevista se houver processo
-- administrativo ou judicial informado. Sem guardar esse dado, o sistema aponta divergencia onde
-- existe decisao amparando — achado falso ao contrario.
--
-- PRECISAO. 'aliquota' passa a ser a efetiva aplicada DERIVADA (RAT x FAP) e vai de NUMERIC(4,2)
-- para NUMERIC(6,4): com FAP de quatro casas, 2 x 0,7071 = 1,4142 era gravado como 1,41. O mesmo
-- alargamento vale para 'estabelecimento_enquadramento.aliquota_aplicada'. O devido ja estava
-- correto (aliquota_efetiva NUMERIC(6,4), fap NUMERIC(5,4)).
--
-- NADA E PRESUMIDO. As linhas que ja existem guardam apenas a efetiva (a Carolina lancou "3").
-- Esse valor NAO e desdobrado em rat=3 / fap=1,0: seria exatamente o valor presumido que o
-- produto proibe. A linha conserva a efetiva, os dois campos novos ficam NULL, e a tela pede o
-- desdobramento. O motor segue aceitando a linha antiga e marca a competencia como comparada
-- sem decomposicao de origem.
--
-- Idempotente.
BEGIN;

-- ---- 1) As duas origens, no RAT aplicado ----
ALTER TABLE estabelecimento_rat_aplicado
    ADD COLUMN IF NOT EXISTS aliquota_rat  NUMERIC(4,2),   -- 1,00 | 2,00 | 3,00 (grau aplicado)
    ADD COLUMN IF NOT EXISTS fap_aplicado  NUMERIC(5,4),   -- 0,5000 a 2,0000 (fator aplicado)
    ADD COLUMN IF NOT EXISTS processo_rat  VARCHAR(120),   -- processo adm./judicial do RAT
    ADD COLUMN IF NOT EXISTS processo_fap  VARCHAR(120);   -- processo adm./judicial do FAP

ALTER TABLE estabelecimento_rat_aplicado
    ALTER COLUMN aliquota TYPE NUMERIC(6,4);

COMMENT ON COLUMN estabelecimento_rat_aplicado.aliquota IS
    'Aliquota efetiva aplicada (S-1005 aliqRatAjust). Derivada de aliquota_rat x fap_aplicado '
    'quando o par existe; nas linhas antigas e o valor informado isolado.';

-- CHECKs nomeados, criados so se ainda nao existirem (idempotencia).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_ratap_grau') THEN
        ALTER TABLE estabelecimento_rat_aplicado
            ADD CONSTRAINT ck_ratap_grau
            CHECK (aliquota_rat IS NULL OR aliquota_rat IN (1, 2, 3));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_ratap_fap') THEN
        ALTER TABLE estabelecimento_rat_aplicado
            ADD CONSTRAINT ck_ratap_fap
            CHECK (fap_aplicado IS NULL OR fap_aplicado BETWEEN 0.5 AND 2.0);
    END IF;
    -- O par e tudo-ou-nada: meio desdobramento nao diz qual origem errou.
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_ratap_par_completo') THEN
        ALTER TABLE estabelecimento_rat_aplicado
            ADD CONSTRAINT ck_ratap_par_completo
            CHECK ((aliquota_rat IS NULL) = (fap_aplicado IS NULL));
    END IF;
END $$;

-- ---- 2) A serie apurada passa a registrar as duas origens aplicadas ----
-- Sem isso o painel e a memoria sabem que divergiu e nao sabem de onde.
ALTER TABLE estabelecimento_enquadramento
    ADD COLUMN IF NOT EXISTS rat_aplicado  NUMERIC(4,2),
    ADD COLUMN IF NOT EXISTS fap_aplicado  NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS processo_rat  VARCHAR(120),
    ADD COLUMN IF NOT EXISTS processo_fap  VARCHAR(120);

ALTER TABLE estabelecimento_enquadramento
    ALTER COLUMN aliquota_aplicada TYPE NUMERIC(6,4);

COMMENT ON COLUMN estabelecimento_enquadramento.aliquota_aplicada IS
    'Efetiva aplicada na competencia (RAT aplicado x FAP aplicado). Quatro casas: com FAP de '
    'quatro casas, duas truncariam o produto.';

COMMIT;

-- Conferencia depois de aplicar (esperado: numeric 6,4 nas duas aliquotas aplicadas):
--   SELECT table_name, column_name, numeric_precision, numeric_scale
--     FROM information_schema.columns
--    WHERE column_name IN ('aliquota','aliquota_aplicada','fap_aplicado','aliquota_rat')
--      AND table_name IN ('estabelecimento_rat_aplicado','estabelecimento_enquadramento')
--    ORDER BY table_name, column_name;
