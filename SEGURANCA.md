# Segredos do Ajusta — inventário, rotação e procedimento

Quem abrir este repositório daqui a seis meses deve conseguir, só com este arquivo,
entender o que foi trocado em 01/11/2026, por quê, e como rotacionar de novo.

Nenhum valor de segredo aparece aqui, e nenhum deve ser acrescentado. Este arquivo
é versionado.

---

## 1. Por que houve rotação

Em **21/10/2026** a Railway divulgou um incidente de segurança: um terceiro pode
ter acessado variáveis de ambiente de clientes, em alguns casos já decifradas,
numa campanha dirigida a chaves de provedores de IA.

A API e o worker do Ajusta rodam na Railway (projeto `artistic-tenderness`,
ambiente `production`). **Toda variável que estava no cofre deles antes dessa data
foi tratada como vazada**, independentemente de haver ou não sinal de uso indevido.

Duas confirmações externas de que a exposição foi real:

- a **Anthropic revogou** por conta própria a chave `RadarPrevi`;
- o **OpenRouter desativou** a chave `sst-esocial` — era essa, e não a da Anthropic,
  a causa de a PrevIA estar fora do ar desde 21/10.

Não houve gasto fraudulento. OpenRouter: US$ 0,01 e 6 requisições no período,
nada depois de 21/10. ElevenLabs: cota intacta.

---

## 2. Onde cada segredo vive

A fonte da verdade é o painel da Railway, não o `.env` local — o `.env` é só o
ambiente de desenvolvimento e **não** reflete produção.

| Segredo | Serviço | Para que serve |
|---|---|---|
| `SECRET_KEY` | `web`, `jubilant-stillness` | Assina o JWT (HS256). Quem a tem forja login de qualquer usuário. |
| `POSTGRES_PASSWORD` | `Postgres` | Papel `postgres`, dono do banco, superusuário. Ignora RLS. |
| `APP_DB_PASSWORD` | `web` | Papel `radar_app`, com que a API conecta. Sujeito a RLS. |
| `OPENROUTER_API_KEY` | `web` | PrevIA: chat e transcrição Whisper. Pago. |
| `ANTHROPIC_API_KEY` | `web`, `jubilant-stillness` | Importação de LTCAT e `ai_layer`. Pago. |
| `ELEVENLABS_API_KEY` | `web` | Voz da PrevIA (text-to-speech). Pago. |
| senha do Redis | `Redis` | Fila do Celery. |

### Como a aplicação conecta ao banco — e por que importa

- No `web`, **`DATABASE_URL` e `DATABASE_URL_SYNC` estão VAZIAS de propósito.**
  Com elas vazias, `api/config.py` monta a URL a partir de
  `APP_DB_USER` + `APP_DB_PASSWORD` + `POSTGRES_HOST/PORT/DB`, e a API conecta
  como `radar_app`. **É isso que faz o RLS do Adendo 05 valer.** Preencher
  qualquer uma das duas com a URL do dono desliga o isolamento entre escritórios
  sem gerar erro nenhum.
- No worker (`jubilant-stillness`), a `DATABASE_URL` **referencia a do serviço
  Postgres** e portanto conecta como `postgres`, superusuário. O worker roda sem
  RLS. Não é vazamento, mas é assimetria conhecida — ver "Pendências".

Confira o estado real **no log da partida do serviço**: `_checar_papel_rls()` roda a cada
subida e imprime com que papel a aplicação conectou. `🔒 Isolamento por escritorio ativo` é
o estado correto; o aviso em moldura de `=` significa papel privilegiado e RLS sem efeito.
(Até 06/11 isso se conferia em `/api/debug/db`, removido por entregar a configuração do
banco sem autenticação.)

---

## 3. O que foi feito em 01/11/2026

Ordem por raio de alcance, não por facilidade. Cada item só foi dado por concluído
depois de um teste que **também provou a recusa do valor antigo** — guarda que não
foi vista falhando é guarda que se supõe que existe.

| # | Item | Verificação |
|---|---|---|
| 1 | Senha do papel `postgres` | `psql` com a nova conecta; com a sabotada, `password authentication failed`. |
| 2 | `SECRET_KEY` nos dois serviços | Sessões caíram; `/api/empresas/` devolve 401 sem token e com token forjado. |
| 3 | `OPENROUTER_API_KEY` | PrevIA voltou a responder; painel mostra uso na chave nova. |
| 4 | `ELEVENLABS_API_KEY` | Voz voltou; a chave antiga foi desativada **depois** e a voz seguiu funcionando. |
| 5 | Senha do `radar_app` | `/api/debug/db` com `rls_aplicavel: true` (endpoint removido em 06/11; hoje se confere no log da partida); `psql` recusa a sabotada. |
| 6 | Acesso público do Redis **removido** | Ver abaixo. |

### O Redis saiu da internet

O serviço tinha TCP Proxy público. As três variáveis que consomem o Redis
(`REDIS_URL` no `web`, `CELERY_BROKER_URL` e `CELERY_RESULT_BACKEND` nos dois
serviços) apontam para a rede **interna**, então remover o proxy não quebrou nada.

Isso vale mais do que rotacionar a senha: sem porta externa, a credencial vazada
só serve de dentro do próprio projeto. A rotação da senha do Redis ficou como
arremate (ver "Pendências").

---

## 4. Procedimento para rotacionar de novo

### Regras que valem para todos

1. **Gere o valor num arquivo, não na tela.** `umask 077` antes, para o arquivo
   nascer 600. Passe a senha ao `psql` por `stdin` ou por `PGPASSWORD`, nunca na
   linha de comando — ela ficaria visível em `ps` e no histórico.
2. **Senhas alfanuméricas** (`tr -dc 'A-Za-z0-9'`). Símbolo dentro de URL de
   conexão precisa de codificação e é fonte de erro bobo.
3. **Teste quebrando.** Para cada troca, prove que o valor novo funciona **e** que
   um valor errado é recusado. Se a sabotagem passar, o teste é que está furado.
4. **Apague os arquivos de senha** quando terminar.

### `SECRET_KEY`

Troca direta, **sem transição**. Derrubar todas as sessões é a finalidade: quem
tem a chave antiga forja login. Nenhum dado em repouso depende dela.

```bash
umask 077 && openssl rand -base64 64 | tr -dc 'A-Za-z0-9' | cut -c1-64 > ~/sk.txt
```

Cole o valor em `SECRET_KEY` no `web` **e** no `jubilant-stillness` — os dois
precisam ser idênticos — e faça Deploy nos dois.

### Senha do `postgres` (dono)

**Mudar a variável `POSTGRES_PASSWORD` no painel NÃO troca a senha.** A imagem do
Postgres lê essa variável só quando cria o cluster; num banco que já existe ela é
decorativa. Quem troca só a variável acha que rotacionou e não rotacionou nada.

A ordem correta é: primeiro o banco, depois a variável.

```bash
umask 077 && openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-40 > ~/pg.txt
printf "ALTER USER postgres WITH PASSWORD '%s';\n" "$(cat ~/pg.txt)" \
  | psql "<URL atual>" -v ON_ERROR_STOP=1 -q -f -
```

Depois, no serviço `Postgres`, atualize **`POSTGRES_PASSWORD`**. As variáveis
`DATABASE_URL`, `DATABASE_PUBLIC_URL` e `PGPASSWORD` são templates que se montam
a partir dela — **não** as edite à mão. Ao publicar, segure **Alt** no botão
Deploy: isso grava sem reiniciar o banco, e reiniciar aqui não serve para nada.

A Railway avisa que "a configuração do banco não será atualizada". O aviso está
certo e não se aplica, porque o banco já foi alterado antes.

Não afeta a aplicação: ela conecta como `radar_app`.

### Senha do `radar_app`

Esta **afeta a aplicação**. Para reduzir a janela de indisponibilidade:

1. gere o valor num arquivo;
2. **engatilhe** `APP_DB_PASSWORD` no `web` (salvar na Railway engatilha; só o
   Deploy publica) — e **não** publique ainda;
3. rode o `ALTER ROLE`;
4. clique em Deploy imediatamente.

```bash
printf "ALTER ROLE radar_app WITH PASSWORD '%s';\n" "$(cat ~/ra.txt)" \
  | PGPASSWORD=$(cat ~/pg.txt) psql -h <host> -p <porta> -U postgres -d railway \
    -v ON_ERROR_STOP=1 -q -f -
```

Só o `web` precisa mudar — o worker não usa esse papel.

### Senha do Redis

**Não** edite `REDISPASSWORD` à mão nem rode `CONFIG SET requirepass`: cada um
muda só um lado e deixa variável e banco fora de sincronia. O caminho suportado é
o botão **Regenerate**, em `Redis → Database → Config → Connection`. Ele reinicia
só o banco; `web` e worker continuam com a senha velha até serem redeployados.

### Chaves de provedor (OpenRouter, Anthropic, ElevenLabs)

Sempre **sobreposição**: cria a nova, põe em produção, confirma funcionando, e só
então revoga a antiga. Revogar antes deixa sem as duas se algo der errado.

Tetos configurados em 01/11/2026, e eles são hoje o **único** limite de gasto que
existe — o código não tem nenhum:

- **OpenRouter**: US$ 10 por mês, com reinício mensal.
- **ElevenLabs**: 5.000 créditos por período, e a chave restrita **apenas** a
  *Text to Speech*. A transcrição de áudio não passa pelo ElevenLabs — vai pelo
  Whisper do OpenRouter —, então nenhuma outra permissão é necessária.

Sobre expiração automática de chave: foi deliberadamente **não** ativada. Uma
chave que expira sozinha derruba a funcionalidade em silêncio, e a PrevIA já ficou
dez dias fora sem ninguém notar. Reavaliar quando existir verificação ativa das
dependências externas.

---

## 5. O que NÃO precisou de tratamento especial

- **Não há cifra de dados em repouso.** Não existe Fernet, AES nem `pgcrypto` em
  uso para dados. O `pgcrypto` está criado na migration 001, mas só pelo
  `gen_random_uuid()`. Senhas de usuário são hash bcrypt, que é via única.
  **Consequência: trocar qualquer chave não torna nenhum dado ilegível**, e não é
  preciso lista de chaves aposentadas nem comando de recriptografia.
- **O histórico do git está limpo.** Varredura em todos os objetos de todas as
  refs: nunca houve `.env`, `.env.production`, `.pem` ou `.key` versionado, e
  nenhum blob casa com padrão de chave. O único arquivo dessa família que entrou
  foi o `.env.example`, com placeholders. Não é preciso reescrever histórico.

---

## 6. Pendências

**Alta — tirar o Postgres da internet.** O banco ainda tem TCP Proxy público
(`Postgres → Settings → Networking`). Com a senha trocada o risco caiu, mas a
porta continua lá. A Railway oferece `railway connect Postgres`, um túnel que
abre o `psql` da máquina local sem exposição pública — ou seja, dá para remover o
proxy **sem perder o caminho de aplicar migrations**. Testar o túnel antes de
remover.

**Média — o worker roda como superusuário.** A `DATABASE_URL` do
`jubilant-stillness` referencia a do serviço Postgres e conecta como `postgres`.
O isolamento por escritório no worker depende só das cláusulas `WHERE` do código,
não do RLS. Alinhar com o `web` (URL vazia + `APP_DB_*`) exige conferir que todo
caminho síncrono funciona sob RLS.

**Média — a trava de isolamento da tabela `usuarios`.** Migration 058, escrita e
não aplicada; as funções `auth_usuario_por_email` e `auth_usuario_por_id`
(migrations 057 e 059) já estão em produção. Assunto separado deste incidente.

**Baixa — arremates.** Rotacionar a senha do Redis pelo `Regenerate`; apagar
`MINIO_ACCESS_KEY` e `MINIO_SECRET_KEY` do `web` (não existe serviço MinIO no
projeto — são variáveis mortas guardando valor vazado); criar chave nova da
Anthropic para restaurar a importação de LTCAT.

**Fora da Railway — `HACKFARM_API_KEY`.** Está no `.env` local do Ajusta e é de
outro projeto. Rotacionar lá e remover daqui: credencial de um projeto dentro de
outro transforma uma máquina comprometida em acesso a vários sistemas de uma vez.

---

## 7. Lacunas que esta rotação não resolve

Estas são de código e continuam abertas. Nenhuma é vazamento; todas são o motivo
de um vazamento futuro poder custar caro ou passar despercebido.

1. ~~**`/api/debug/db` responde sem autenticação** e entrega host, banco, usuário e
   versão do Postgres a qualquer um.~~ **CORRIGIDO em 06/11** — endpoint removido. A
   checagem de papel continua, no log da partida.
2. ~~**Todo erro 500 devolve o traceback completo ao cliente** (`api/main.py`).~~
   **CORRIGIDO em 06/11** — resposta genérica com código de referência; o traceback
   fica no log, ligado à resposta pelo mesmo código.

   Corrigidos na mesma leva, e que não constavam desta lista:
   - **`/api/docs`, `/api/redoc` e `/api/openapi.json` eram públicos.** Fechados fora
     de desenvolvimento (`DOCS_PUBLICAS` reabre de propósito).
   - **CORS era `allow_origins=["*"]` fixo no código**, e a lista do `config.py` não
     era lida por ninguém. Agora restrito aos domínios do sistema.
   - **`APP_ENV` governava o `echo` do SQL e o SSL do banco juntos.** Separados:
     `DB_SSL` é chave própria. O `echo` gravava toda consulta **com os parâmetros**
     (CNPJ, razão social, nº de processo, autoria) no log do serviço.
3. **Não há teto de tokens nem de chamadas** em lugar nenhum do código. O chat da
   PrevIA encaminha ao provedor o que o cliente mandar, sem validar tamanho; a
   importação de LTCAT faz uma chamada por pedaço do PDF, sem limite de pedaços, e
   a task do Celery repete o documento inteiro até 3 vezes em caso de erro.
4. **Não há registro de consumo.** Nenhum token, modelo ou custo é gravado em log.
   Em `importacao_pdf.py` há uma linha que calcula `model_dump()` e **descarta** o
   resultado. Sem isso, "quanto deste gasto é do app?" não tem resposta.
5. **Prompt caching não é pedido em lugar nenhum** — confirmado pelo painel do
   OpenRouter, com *cache hit rate* de 0,0%.
6. **`settings.llm_model` e `llm_fallback_model` não são usados.** Os modelos estão
   escritos à mão em cada chamada; mudar a configuração não muda o modelo.
7. **CORS com `allow_origins=["*"]` e `allow_credentials=True`.**
8. **Token de acesso com validade padrão de 43.200 minutos — 30 dias.**
