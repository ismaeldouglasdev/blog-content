#!/usr/bin/env python3
"""
Distribui posts do blog para Threads, Bluesky e Telegram.

Deterministico (sem LLM). Roda no GitHub Actions apos merge na main.
Estado de entrega fica em distribute/state/distributed.json.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import time

from channels import BlueskyClient, TelegramClient, ThreadsClient

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
META_PATH = os.path.join(REPO_DIR, "posts", "_meta.json")
STATE_DIR = os.path.join(SCRIPT_DIR, "state")
STATE_PATH = os.path.join(STATE_DIR, "distributed.json")

PLATFORMS = ("threads", "bsky", "telegram")

ENV_VARS = (
    "THREADS_TOKEN",
    "THREADS_USER_ID",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "BLUESKY_HANDLE",
    "BLUESKY_APP_PASSWORD",
)

# Limite do Bluesky para o texto do post (graphemes). O corpo e truncado para
# caber nesse orcamento SEM tocar na URL, que sempre vai no fim, inteira.
BSKY_MAX = 300

# Rate limiting: as plataformas nao gostam de rajada. Publicar varios posts
# seguidos pode ser tratado como spam. Dorme entre cada publicacao e tambem
# entre posts diferentes.
POST_DELAY_SECONDS = 20

# Gap entre posts diferentes (segundos) e teto de posts por execucao.
POSTS_GAP_SECONDS = 45
MAX_POSTS_PER_RUN = 2



def read_env():
    """Le credenciais do ambiente (vazias quando ausentes)."""
    env = {name: os.environ.get(name, "").strip() for name in ENV_VARS}
    env["BLOG_URL"] = os.environ.get("BLOG_URL", "").strip() or "https://blog.ismaeltech.com"
    return env


def load_meta():
    """Carrega posts/_meta.json; levanta RuntimeError se ilegivel."""
    with open(META_PATH, encoding="utf-8") as f:
        data = json.load(f)
    posts = data.get("posts", [])
    if not isinstance(posts, list):
        raise RuntimeError("posts/_meta.json: chave 'posts' nao e uma lista")
    return posts


def load_state():
    """Carrega o state de distribuicao; dict vazio se ainda nao existe."""
    if not os.path.exists(STATE_PATH):
        return {"posts": {}}
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """Grava o state atomicamente (arquivo temporario + os.replace)."""
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STATE_PATH)


def parse_frontmatter(path):
    """Extrai title/excerpt/tags do frontmatter YAML simples de um .md."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        content = f.read()
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.startswith("[") and value.endswith("]"):
            value = re.findall(r'"([^"]*)"', value) or [
                v.strip() for v in value[1:-1].split(",") if v.strip()
            ]
        fm[key] = value
    return fm


def sanitize(text):
    """Troca em/en dash por hifen simples e colapsa espacos (house style)."""
    text = text.replace("—", " - ").replace("–", " - ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate(text, limit):
    """Corta em `limit` chars adicionando reticencias quando necessario."""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def sentence_hook(text, limit=180):
    """Recorta o excerpt em fronteira de frase, para o post social nao
    virar um paragrafo de blog. Nao inventa texto: so corta o que ja existe."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # ultima pontuacao de fim de frase antes do corte
    best = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "),
               cut.rfind(".\n"), cut.rfind("!\n"), cut.rfind("?\n"))
    if best > limit * 0.4:
        return cut[: best + 1].strip()
    return cut.rstrip() + "…"


def build_hashtags(tags, max_tags=4):
    """Converte ate 4 tags em hashtags capitalizadas (#Node, #Javascript)."""
    out = []
    for tag in (tags or [])[:max_tags]:
        word = re.sub(r"[^a-zA-Z0-9]", "", str(tag))
        if not word:
            continue
        out.append("#" + word.capitalize())
    return " ".join(out)


def build_variants(post, blog_url):
    """Monta as variantes por plataforma a partir do frontmatter PT/EN.

    Returns dict com texto por plataforma mais `bsky_url` (usado pelo
    cliente Bluesky para criar o facet clicavel).
    """
    slug = post["slug"]
    fm = parse_frontmatter(os.path.join(REPO_DIR, "posts", "%s.md" % slug))
    title = fm.get("title") or post.get("title", "")
    excerpt = fm.get("excerpt") or post.get("excerpt", "")
    tags = fm.get("tags") or post.get("tags", [])
    en_fm = parse_frontmatter(os.path.join(REPO_DIR, "posts", "%s-en.md" % slug))
    en_title = en_fm.get("title") or post.get("title_en") or title
    en_excerpt = en_fm.get("excerpt") or post.get("excerpt_en") or excerpt

    post_url = "%s/%s" % (blog_url, slug)
    bsky_slug = post.get("translation_slug") or ("%s-en" % slug if en_fm else slug)
    bsky_url = "%s/%s" % (blog_url, bsky_slug)

    # Formato de compartilhamento: gancho curto + link.
    # `share_hook` no frontmatter e o texto autorado pra rede social (diz o que
    # a pessoa leva do post, sem repetir o titulo). Sem ele, cai no excerpt
    # cortado em fronteira de frase.
    hook = sentence_hook(sanitize(fm.get("share_hook") or excerpt))
    en_hook = sentence_hook(sanitize(en_fm.get("share_hook") or en_excerpt))

    threads = "💡 %s\n\n%s" % (truncate(sanitize(title), 120), hook)
    hashtags = build_hashtags(tags)
    if hashtags:
        threads += "\n\n%s" % hashtags

    # Trunca o corpo, nunca a URL: cortar o texto montado quebrava o link
    # em posts com titulo+excerpt longos (a URL ficava cortada com reticencias).
    # O limite do Bluesky e de 300 graphemes para o post inteiro.
    bsky_title = truncate(sanitize(en_title), 120)
    overhead = len(bsky_title) + len("\n\n") + len("\n\n🔗 ") + len(bsky_url)
    bsky_body = truncate(en_hook, max(BSKY_MAX - overhead, 40))
    bsky = "%s\n\n%s\n\n🔗 %s" % (bsky_title, bsky_body, bsky_url)

    telegram = "<b>%s</b>\n\n%s\n\n<a href=\"%s\">Ler no blog</a>" % (
        html.escape(truncate(sanitize(title), 120)),
        html.escape(hook),
        html.escape(post_url),
    )

    return {
        "threads": truncate(threads, 430),
        "threads_comment": "Artigo completo: %s" % post_url,
        "bsky": bsky,
        "bsky_url": bsky_url,
        "telegram": telegram,
    }


def find_undelivered(meta_posts, days, state, active=None):
    """Retorna posts master nao totalmente entregues, mais recentes primeiro.

    `active` = plataformas com credenciais configuradas. So elas contam para
    decidir se o post esta completo: uma plataforma sem credencial (ex.: Threads
    hoje) nunca sera entregue, e se ela contasse, nenhum post seria considerado
    pronto e o lote seria sempre preenchido com no-ops -- o backlog nunca drena.

    Deduplica por conteudo: quando o mesmo post existe com datas diferentes
    (ex.: 2026-09-01 e 2026-09-17 sao o mesmo artigo), so o mais recente entra.
    Sem isso o canal publico receberia o mesmo texto duas vezes.
    """
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    delivered = state.get("posts", {})
    candidates = []
    for post in meta_posts:
        if post.get("lang") == "en":
            continue
        slug = post.get("slug")
        if not slug:
            continue
        entry = delivered.get(slug)
        if entry:
            recorded = entry.get("platforms", {})
            if active:
                # so as plataformas configuradas contam
                if all(recorded.get(n) for n in active):
                    continue
            elif recorded:
                # sem credencial nao ha o que publicar: ja entregou o que dava
                continue
        try:
            post_date = datetime.date.fromisoformat(post["date"])
        except (KeyError, ValueError):
            continue
        if post_date >= cutoff:
            candidates.append(post)
    candidates.sort(key=lambda p: p["date"], reverse=True)
    # primeiro vence: mantem a versao mais recente de cada conteudo.
    # O `seen` ja nasce com o que ja foi ENTREGUE: se o mesmo artigo ja foi
    # publicado numa data anterior, a copia antiga nao deve sair de novo.
    seen = {re.sub(r"^\d{4}-\d{2}-\d{2}-", "", s) for s in delivered}
    out = []
    for post in candidates:
        base = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", post["slug"])
        if base in seen:
            print("SKIP: '%s' - conteudo ja saiu no canal (copy anterior do mesmo artigo)" % post["slug"][:60])
            continue
        seen.add(base)
        out.append(post)
    return out


def build_clients(env):
    """Instancia clientes para plataformas com credenciais; avisa as ausentes."""
    clients = {}
    specs = (
        ("threads", "Threads", ("THREADS_TOKEN", "THREADS_USER_ID"),
         lambda e: ThreadsClient(e["THREADS_TOKEN"], e["THREADS_USER_ID"])),
        ("bsky", "Bluesky", ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"),
         lambda e: BlueskyClient(e["BLUESKY_HANDLE"], e["BLUESKY_APP_PASSWORD"])),
        ("telegram", "Telegram", ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"),
         lambda e: TelegramClient(e["TELEGRAM_BOT_TOKEN"])),
    )
    for name, display, vars_, factory in specs:
        if all(env[v] for v in vars_):
            clients[name] = factory(env)
        else:
            missing = [v for v in vars_ if not env[v]]
            print("WARNING: %s nao sera usado - faltam: %s" % (display, ", ".join(missing)))
    return clients


def print_dry_run(post, env):
    """Imprime o plano de distribuicao de um post (sem rede, sem state)."""
    blog_url = env["BLOG_URL"]
    post_url = "%s/%s" % (blog_url, post["slug"])
    variants = build_variants(post, blog_url)
    print("[DRY-RUN] %s (%s) -> %s" % (post["slug"], post["date"], post_url))
    print("  threads:  %r" % variants["threads"])
    print("  threads comment: %r" % variants["threads_comment"])
    print("  bsky:     %r" % variants["bsky"])
    print("  bsky url: %s" % variants["bsky_url"])
    print("  telegram: %r" % variants["telegram"])


def _threads_post(client, variants):
    """Publica no Threads e tenta o link no primeiro comentario (best-effort)."""
    post_id = client.post_text(variants["threads"])
    client.reply_to(post_id, variants["threads_comment"])
    return post_id


def distribute_post(post, clients, env, state):
    """Publica um post nas plataformas configuradas; True se o state mudou."""
    slug = post["slug"]
    blog_url = env["BLOG_URL"]
    post_url = "%s/%s" % (blog_url, slug)
    variants = build_variants(post, blog_url)
    entry = state["posts"].setdefault(
        slug, {"url": post_url, "posted_at": None, "platforms": {}}
    )
    entry.setdefault("platforms", {})
    changed = False
    results = {}

    def attempt(name, fn):
        """Tenta publicar em uma plataforma e registra o resultado."""
        nonlocal changed
        if name not in clients or entry["platforms"].get(name):
            return
        try:
            result = fn()
            entry["platforms"][name] = result
            results[name] = "ok (%s)" % result
            changed = True
        except Exception as exc:
            print("    [ERRO] %s: %s" % (name, exc))
            results[name] = "falhou"

    for platform in PLATFORMS:
        if platform in clients and not entry["platforms"].get(platform):
            # Espaco entre plataformas: rajada seguida parece spam.
            time.sleep(POST_DELAY_SECONDS)
        if platform == "threads":
            attempt(platform, lambda: _threads_post(clients["threads"], variants))
        elif platform == "bsky":
            attempt(platform, lambda: clients["bsky"].post_text(variants["bsky"], link_url=variants["bsky_url"]))
        else:
            attempt(platform, lambda: str(clients["telegram"].send_message(env["TELEGRAM_CHAT_ID"], variants["telegram"])))

    if changed and not entry["posted_at"]:
        entry["posted_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for name in PLATFORMS:
        if name not in results:
            if entry["platforms"].get(name):
                results[name] = "ja entregue"
            elif name not in clients:
                results[name] = "sem credenciais"

    detail = " | ".join("%s: %s" % (k, v) for k, v in results.items())
    print("[POST] %s -> %s" % (slug, detail))
    return changed


def main(argv=None):
    """Ponto de entrada: parseia args, roda o pipeline, retorna exit code."""
    parser = argparse.ArgumentParser(description="Distribui posts do blog para redes sociais")
    parser.add_argument("--dry-run", action="store_true", help="apenas mostra o plano, sem postar")
    parser.add_argument("--days", type=int, default=3, help="janela em dias (0 = so hoje)")
    args = parser.parse_args(argv)

    env = read_env()
    try:
        meta_posts = load_meta()
    except Exception as exc:
        print("ERRO fatal: nao foi possivel ler posts/_meta.json: %s" % exc)
        return 2
    try:
        state = load_state()
    except Exception as exc:
        print("ERRO fatal: nao foi possivel ler %s: %s" % (STATE_PATH, exc))
        return 2

    clients = build_clients(env)
    undelivered = find_undelivered(meta_posts, args.days, state, active=tuple(clients))

    if args.dry_run:
        if not undelivered:
            print("[DRY-RUN] nenhum post pendente na janela de %d dias." % args.days)
        for post in undelivered:
            print_dry_run(post, env)
        return 0

    if not clients:
        print("Nenhuma credencial configurada. Configure os secrets (ver distribute/SETUP.md).")
        return 0

    changed = False
    # Teto por execucao: evita rajada. O que sobrar fica no state como
    # pendente e sai na proxima execucao (ou no proximo workflow_dispatch).
    batch = undelivered[:MAX_POSTS_PER_RUN]
    skipped = len(undelivered) - len(batch)
    if skipped > 0:
        print("LIMITE: %d post(s) adiado(s) para a proxima execucao (teto %d/-run)."
              % (skipped, MAX_POSTS_PER_RUN))
    for index, post in enumerate(batch):
        if index > 0:
            time.sleep(POSTS_GAP_SECONDS)
        changed |= distribute_post(post, clients, env, state)
    if changed:
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())