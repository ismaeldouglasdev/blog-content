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

    threads = "💡 %s\n\n%s" % (sanitize(title), sanitize(excerpt))
    hashtags = build_hashtags(tags)
    if hashtags:
        threads += "\n\n%s" % hashtags

    # Trunca o corpo, nunca a URL: cortar o texto montado quebrava o link
    # em posts com titulo+excerpt longos (a URL ficava cortada com reticencias).
    # O limite do Bluesky e de 300 graphemes para o post inteiro.
    bsky_title = truncate(sanitize(en_title), 120)
    overhead = len(bsky_title) + len("\n\n") + len("\n\n🔗 ") + len(bsky_url)
    bsky_body = truncate(sanitize(en_excerpt), max(BSKY_MAX - overhead, 40))
    bsky = "%s\n\n%s\n\n🔗 %s" % (bsky_title, bsky_body, bsky_url)

    telegram = "<b>%s</b>\n\n%s\n\n<a href=\"%s\">Leia no blog</a>" % (
        html.escape(sanitize(title)), html.escape(sanitize(excerpt)), html.escape(post_url)
    )

    return {
        "threads": truncate(threads, 430),
        "threads_comment": "Artigo completo: %s" % post_url,
        "bsky": bsky,
        "bsky_url": bsky_url,
        "telegram": telegram,
    }


def find_undelivered(meta_posts, days, state):
    """Retorna posts master nao totalmente entregues, mais recentes primeiro."""
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    delivered = state.get("posts", {})
    out = []
    for post in meta_posts:
        if post.get("lang") == "en":
            continue
        slug = post.get("slug")
        entry = delivered.get(slug)
        if not slug or (entry and all(entry.get("platforms", {}).get(n) for n in PLATFORMS)):
            continue
        try:
            post_date = datetime.date.fromisoformat(post["date"])
        except (KeyError, ValueError):
            continue
        if post_date >= cutoff:
            out.append(post)
    out.sort(key=lambda p: p["date"], reverse=True)
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

    undelivered = find_undelivered(meta_posts, args.days, state)
    clients = build_clients(env)

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