-- 055_contato_papel.sql — AJUSTA
-- O PAPEL DO CONTATO no bloco Contato (revisao da Carolina, Cadastro).
--
-- O bloco guardava nome, e-mail e telefone — e nada que dissesse QUEM e aquela pessoa em relacao
-- a empresa. A diferenca importa no uso: a peca e os pedidos de documento vao para o contador, a
-- confirmacao de quantitativo para quem responde pelo RH, e uma decisao sobre o enquadramento
-- para o socio. Sem o papel, quem abre o cadastro depois tem um telefone e nenhuma pista de para
-- que serve.
--
-- VOCABULARIO FECHADO, como nas demais tabelas de evento do projeto (047, 054). Quatro opcoes,
-- definidas por ela: Contador, Socio, Responsavel pelo RH, Outro. Texto livre aqui produziria
-- "contadora", "Contador(a)", "cont." e nenhuma consulta possivel depois.
--
-- NULL CONTINUA VALIDO: ha empresa cadastrada antes desta coluna existir, e nenhuma delas sera
-- preenchida por adivinhacao. O campo fica em branco ate alguem informar.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS contato_papel VARCHAR(30);

-- O CHECK vai em comando proprio e condicional: ADD CONSTRAINT nao aceita IF NOT EXISTS, e
-- reaplicar a migration sem esta guarda derrubaria tudo no segundo uso.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_contato_papel'
    ) THEN
        ALTER TABLE empresas
            ADD CONSTRAINT ck_empresas_contato_papel
            CHECK (contato_papel IS NULL
                   OR contato_papel IN ('contador', 'socio', 'rh', 'outro'));
    END IF;
END $$;

COMMENT ON COLUMN empresas.contato_papel IS
    'Papel do contato na empresa: contador, socio, rh ou outro. Vocabulario fechado; o rotulo '
    'exibido vive na aplicacao, nao no banco.';

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) a coluna existe (esperado: contato_papel | character varying | 30)
--   SELECT column_name, data_type, character_maximum_length
--     FROM information_schema.columns
--    WHERE table_name = 'empresas' AND column_name = 'contato_papel';
--
--   -- 2) o vocabulario esta fechado (esperado: 1 linha, com as quatro opcoes no texto)
--   SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conname = 'ck_empresas_contato_papel';
