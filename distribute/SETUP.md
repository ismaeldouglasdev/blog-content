# Distribuição Social Automática (Threads + Bluesky + Telegram)

Runbook de configuração do pipeline que publica cada post novo do blog nas
três redes sociais automaticamente, sem IA no meio do caminho.

## 1. Visão geral e arquitetura

```
merge na main (PR do generate-post.py)
        │
        ▼
GitHub Actions: .github/workflows/distribute.yml
        │  (push: branches: [main] + workflow_dispatch)
        ▼
distribute/distribute-post.py
        │  determinístico, sem LLM
        ├── Threads  (Graph API, corpo + link no primeiro comentário)
        ├── Bluesky  (AT Protocol, versão EN quando existe)
        └── Telegram (Bot API, HTML)
        │
        ▼
distribute/state/distributed.json  (commitado de volta no repo)
```

- O script só considera posts **master** (PT) de `posts/_meta.json` dentro da
  janela `--days` (padrão 3). A versão `-en` é usada apenas como fonte de
  conteúdo para o Bluesky.
- Cada plataforma é entregue de forma independente: se uma falhar, as outras
  seguem e a falha é retentada na próxima execução.
- Nenhuma chamada de IA: o texto é montado a partir do frontmatter
  (title/excerpt/tags) com truncamento e sanitização determinísticos.

## 2. Credenciais (3 passos manuais, no navegador)

> Estes passos exigem conta e navegador. Não é possível automatizar a criação
> das credenciais.

### 2.1 Threads (Graph API)

1. Crie uma conta de desenvolvedor em https://developers.facebook.com
   (dev account).
2. Crie um app e adicione o **use case "Threads"**.
3. Conecte a conta do Threads/Instagram que vai publicar (a sua própria).
4. No **Graph API Explorer**, gere um token com as permissões
   `threads_basic` + `threads_content_publish`. O modo de teste (testing mode)
   é suficiente para publicar na SUA própria conta.
5. Obtenha o **Threads user ID**: `GET /v1.0/me` com o token (o campo `id`
   retornado é o `THREADS_USER_ID`).
6. **Token de longa duração (60 dias)**: o token curto pode ser trocado por um
   long-lived via o endpoint de exchange da Graph API. Anote como tarefa
   recorrente renovar o token antes de expirar (o pipeline falha com erro de
   auth quando expira).

> ⚠️ Detalhes exatos de criação de app, permissões e exchange de token mudam
> com frequência. Se algum passo estiver diferente, siga a documentação
> oficial: https://developers.facebook.com/docs/threads

### 2.2 Telegram (Bot API)

1. No Telegram, abra o **@BotFather** e envie `/newbot`.
2. Escolha um nome e um username para o bot; o BotFather devolve o **token**
   (formato `123456:ABC-DEF...`). Guarde como `TELEGRAM_BOT_TOKEN`.
3. Crie um **canal** no Telegram.
4. Adicione o bot como **administrador** do canal com o direito de
   "postar mensagens" (post messages).
5. O `TELEGRAM_CHAT_ID`:
   - Canal **público**: username com `@` na frente (ex.: `@meucanal`).
   - Canal **privado** (sem username, link de convite): o ID numérico
     `-100...`. Resolva assim: depois de adicionar o bot como admin, rode
     `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` — o update
     `my_chat_member` retorna o `chat.id` do canal (número negativo).

### 2.3 Bluesky (AT Protocol)

1. Crie uma conta em https://bsky.app (ou use uma existente).
2. Vá em **Settings → App Passwords**.
3. Crie um app password com escopo apenas de **Post** (o mínimo necessário).
4. Copie o app password (formato `xxxx-xxxx-xxxx-xxxx`) como
   `BLUESKY_APP_PASSWORD`.
5. O `BLUESKY_HANDLE` é o handle completo, ex.: `meuhandle.bsky.social`
   (sem o `@`).

## 3. Secrets do GitHub

No repositório: **Settings → Secrets and variables → Actions → New repository
secret**.

| Secret | De onde vem |
|--------|-------------|
| `THREADS_TOKEN` | Token da Graph API do Threads (passo 2.1) |
| `THREADS_USER_ID` | ID numérico da conta Threads (`GET /v1.0/me`) |
| `TELEGRAM_BOT_TOKEN` | Token do bot criado no @BotFather (passo 2.2) |
| `TELEGRAM_CHAT_ID` | `@username` do canal (passo 2.2) |
| `BLUESKY_HANDLE` | Handle da conta Bluesky (passo 2.3) |
| `BLUESKY_APP_PASSWORD` | App password do Bluesky (passo 2.3) |
| `BLOG_URL` (opcional) | Base do blog; padrão `https://blog.ismaeltech.com` |

## 4. Teste local antes de habilitar

Sem credenciais configuradas, o script roda em modo plano (dry-run) sem
nenhuma chamada de rede:

```bash
cd ~/blog-content
python3 distribute/distribute-post.py --dry-run --days=3
```

Isso imprime, para cada post pendente, o texto exato que seria publicado em
cada plataforma (para revisar os hooks). Nenhum arquivo de state é criado.

Para simular a execução real sem credenciais (deve avisar "configure secrets"
e sair com código 0):

```bash
python3 distribute/distribute-post.py --days=3
```

## 5. Primeiro run (importante)

O `--days` padrão é **3**, então a primeira execução após habilitar o
workflow **não** vai spammar os posts históricos (65 entradas no `_meta.json`,
33 posts master PT): só os posts dos últimos 3 dias entram. Se um dia você
quiser um backfill deliberado, rode `--days 365` (ou o valor desejado)
manualmente com o argumento ajustado, ou localmente com credenciais.

## 5.1 `share_hook`: o texto que vai pra rede social

O campo opcional `share_hook` no frontmatter e o texto usado no Telegram,
Threads e Bluesky. Ele deve dizer **o que a pessoa leva do post**, sem
repetir o titulo.

```yaml
title: "Vitest: como testar React com testes que realmente ajudam"
excerpt: "Vitest: como testar React com testes que realmente ajudam."
share_hook: "Setup, mocking, testes de integracao e coverage no CI: o fluxo completo de testes com Vitest em React."
```

Sem `share_hook`, o script usa o `excerpt` cortado em fronteira de frase.
Com ele, o post social deixa de ser um paragrafo de blog e vira
compartilhamento de link. Vale revisar o tom de vez em quando.

## 5.2 Ritmo de publicacao (rate limiting)

- `POST_DELAY_SECONDS` (20s): espaco entre plataformas do mesmo post
- `POSTS_GAP_SECONDS` (45s): espaco entre posts diferentes
- `MAX_POSTS_PER_RUN` (2): teto de posts por execucao

Publicar tudo de uma vez faz as plataformas tratarem como spam. O que passa
do teto fica pendente no state e sai na proxima execucao.

## 5.3 Deduplicacao

Ha posts com o mesmo conteudo e datas diferentes (ex.: 2026-09-01 e
2026-09-17 sao o mesmo artigo). O script publica **so o mais recente** e
ignora os demais, para o canal publico nao receber o mesmo texto duas vezes.

## 6. Retry e arquivo de state

- `distribute/state/distributed.json` guarda, por slug master:
  `url`, `posted_at` e `platforms` com o id retornado por cada plataforma
  (`threads`, `bsky`, `telegram`).
- Uma plataforma que falhou fica **sem id** no state; na próxima execução o
  script tenta **somente** essa plataforma para aquele post (as já entregues
  são puladas).
- O state é gravado atomicamente (arquivo temporário + `os.replace`) e
  commitado de volta pelo workflow. O commit do state dispara o workflow de
  novo, mas como não há posts pendentes, nada muda e o loop termina.
- Para "esquecer" um post e republicar, remova a entrada dele do
  `distributed.json`.