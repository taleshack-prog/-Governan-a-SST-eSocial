-- 056_contato_papel_outro.sql — AJUSTA
-- O "QUAL?" DO PAPEL "OUTRO" (Carolina, 27/10): "'Outro' abre um campo 'Qual?', obrigatorio."
--
-- A 055 fechou o vocabulario em quatro opcoes, e 'outro' sozinho nao informa nada: e a resposta
-- que diz "nao e nenhuma das tres" e cala sobre o que e. Procurador, sindico, preposto — cada um
-- muda a quem se pede o que. Sem o detalhe, o campo Papel vira ruido na terceira empresa.
--
-- OBRIGATORIEDADE CONDICIONAL, no banco e nao so na tela. O CHECK exige o detalhe quando, e
-- somente quando, o papel for 'outro': as outras tres opcoes nao aceitam detalhe sobrando, e
-- papel nao informado continua valido, porque ha empresa cadastrada antes de tudo isto existir.
--
-- A GUARDA ANTES DA CONSTRAINT. A coluna contato_papel nasceu hoje (055) e alguem pode ter
-- gravado 'outro' nos minutos entre uma migration e outra. ADD CONSTRAINT sobre linha que viola
-- falha com mensagem de catalogo, dificil de ligar a causa; aqui a verificacao vem antes e diz
-- exatamente qual empresa corrigir. Falhar e o comportamento certo: criar a trava "quando der"
-- deixaria o banco sem ela e ninguem notaria.
--
-- Idempotente.
BEGIN;

ALTER TABLE empresas
    ADD COLUMN IF NOT EXISTS contato_papel_outro VARCHAR(100);

DO $$
DECLARE
    pendentes TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_empresas_contato_papel_outro') THEN
        RETURN;   -- ja criada numa passagem anterior
    END IF;

    SELECT string_agg(coalesce(razao_social, id::text), '; ')
      INTO pendentes
      FROM empresas
     WHERE contato_papel = 'outro'
       AND (contato_papel_outro IS NULL OR btrim(contato_papel_outro) = '');

    IF pendentes IS NOT NULL THEN
        RAISE EXCEPTION
            'Há empresa com papel "outro" e sem o detalhe: %. Informe o "Qual?" nessas empresas '
            '(ou troque o papel) e rode esta migration de novo.', pendentes;
    END IF;

    ALTER TABLE empresas
        ADD CONSTRAINT ck_empresas_contato_papel_outro
        CHECK (
            -- 'outro' exige o detalhe, e nao aceita espaco em branco passando por preenchimento
            (contato_papel = 'outro'
             AND contato_papel_outro IS NOT NULL AND btrim(contato_papel_outro) <> '')
            -- as outras opcoes nao carregam detalhe: guarda-lo seria dado que a tela nao mostra
            OR (contato_papel IS NOT NULL AND contato_papel <> 'outro' AND contato_papel_outro IS NULL)
            -- papel nao informado: nem papel, nem detalhe
            OR (contato_papel IS NULL AND contato_papel_outro IS NULL)
        );
END $$;

COMMENT ON COLUMN empresas.contato_papel_outro IS
    'Qual é o papel, quando contato_papel = outro. Obrigatório nesse caso e proibido nos demais, '
    'por CHECK.';

COMMIT;

-- Conferencia depois de aplicar:
--   -- 1) a coluna existe (esperado: contato_papel_outro | character varying | 100)
--   SELECT column_name, data_type, character_maximum_length FROM information_schema.columns
--    WHERE table_name = 'empresas' AND column_name = 'contato_papel_outro';
--
--   -- 2) a trava condicional existe (esperado: 1 linha)
--   SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conname = 'ck_empresas_contato_papel_outro';
