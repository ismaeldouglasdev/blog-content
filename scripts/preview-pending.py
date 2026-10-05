#!/usr/bin/env python3
"""Pre-visualiza posts que estao em PRs abertos, sem os publicar.

Porque: o site le os posts de `main`, portanto nao ha forma de os ver no site
antes do merge. Isto monta uma pagina local com a versao **do branch do PR**, que
e o que vai ser publicado se o PR fundir.

Nao escreve nada no repo e nao faz push. Le os branches, renderiza o markdown e
serve em localhost.

Uso:
    python3 scripts/preview-pending.py            # porta 8099
    python3 scripts/preview-pending.py --port 9000
    python3 scripts/preview-pending.py --pr 53    # so um PR
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import pathlib
import re
import shutil
import socketserver
import subprocess
import tempfile

import markdown

REPO = pathlib.Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True,
        errors="replace", check=True
    ).stdout


def git_bytes(*args: str) -> bytes:
    """Para ficheiros binarios. `git show` de um JPEG em modo texto rebenta a
    descodificacao, que foi o primeiro bug disto."""
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, check=True
    ).stdout


def gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout


def open_prs() -> list[tuple[int, str, str]]:
    out = gh("pr", "list", "--state", "open", "--json",
             "number,headRefName,title").strip()
    if not out:
        return []
    return [(p["number"], p["headRefName"], p["title"]) for p in json.loads(out)]


def slug_of(path: str) -> str:
    return path.rsplit("/", 1)[-1][:-3]


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", raw, re.S)
    if not m:
        return {}, raw
    fm, body = m.group(1), m.group(2)
    meta: dict = {}
    key = None
    for line in fm.split("\n"):
        km = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if km:
            key = km.group(1)
            val = km.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                meta[key] = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
            else:
                meta[key] = val.strip('"')
        elif key and line.strip().startswith("-"):
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.strip().lstrip("- ").strip('"'))
    return meta, body


def render(body: str) -> str:
    body = re.sub(r"\n{3,}", "\n\n", body)
    return markdown.markdown(
        body, extensions=["fenced_code", "tables", "sane_lists", "nl2br"]
    )


def collect(only_pr: int | None) -> list[dict]:
    items: list[dict] = []
    for number, branch, title in open_prs():
        if only_pr and number != only_pr:
            continue
        git("fetch", "--quiet", "origin", branch)
        try:
            files = git("ls-tree", "-r", "--name-only", f"origin/{branch}", "posts/")
        except subprocess.CalledProcessError:
            continue
        md = [f for f in files.split() if f.startswith("posts/")
              and f.endswith(".md") and "_meta" not in f]
        # so posts que ainda nao estao em main
        main_files = set(git("ls-tree", "-r", "--name-only", "main", "posts/").split())
        for path in md:
            if path in main_files:
                continue
            raw = git("show", f"origin/{branch}:{path}")
            meta, body = parse_frontmatter(raw)
            items.append({
                "pr": number,
                "branch": branch,
                "pr_title": title,
                "path": path,
                "slug": slug_of(path),
                "meta": meta,
                "html": render(body),
                "words": len(re.sub(r"<[^>]+>", " ", body).split()),
            })
    return items


CSS = """
:root{--bg:#0f1115;--card:#171a21;--fg:#e6e8ee;--dim:#9aa3b2;--line:#2a2f3a;
      --pt:#7cc4ff;--en:#ffb37c;--new:#3ddc97}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:28px 24px;border-bottom:1px solid var(--line);position:sticky;top:0;
       background:var(--bg);z-index:5}
h1{margin:0 0 4px;font-size:22px}
.sub{color:var(--dim);font-size:14px}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
.post{background:var(--card);border:1px solid var(--line);border-radius:12px;
      margin-bottom:28px;overflow:hidden}
.bar{display:flex;gap:10px;align-items:center;padding:12px 16px;
     border-bottom:1px solid var(--line);flex-wrap:wrap}
.pr{background:var(--new);color:#06281c;font-weight:700;font-size:12px;
    padding:2px 8px;border-radius:20px}
.lang{font-weight:700;font-size:12px;padding:2px 8px;border-radius:4px}
.lang.pt{background:var(--pt);color:#04223a}
.lang.en{background:var(--en);color:#3a1e04}
.title{font-weight:600;flex:1;min-width:200px}
.cover{width:100%;max-height:300px;object-fit:cover;display:block;background:#0b0d11}
.meta{padding:10px 16px;color:var(--dim);font-size:13px;display:flex;gap:14px;flex-wrap:wrap}
.excerpt{padding:0 16px 12px;color:var(--dim);font-style:italic}
.body{padding:4px 20px 22px}
.body h1{font-size:24px;margin:18px 0 10px}
.body h2{font-size:19px;margin:22px 0 8px;border-bottom:1px solid var(--line);
         padding-bottom:5px}
.body h3{font-size:16px;margin:18px 0 6px}
.body pre{background:#0b0d11;border:1px solid var(--line);border-radius:8px;
          padding:12px;overflow:auto;font-size:13px}
.body code{background:#0b0d11;padding:1px 5px;border-radius:4px;font-size:14px}
.body pre code{background:none;padding:0}
.body blockquote{border-left:3px solid var(--line);margin:12px 0;padding:2px 14px;
                 color:var(--dim)}
.body a{color:var(--pt)}
.body img{max-width:100%;border-radius:6px}
.credit{font-size:13px;color:var(--dim);border-top:1px solid var(--line);
        margin-top:18px;padding-top:12px}
.tabs{display:flex;gap:6px}
.tab{background:#22262f;border:1px solid var(--line);color:var(--dim);
     padding:5px 12px;border-radius:6px;cursor:pointer;font-size:13px}
.tab.on{background:var(--fg);color:#0f1115;font-weight:600}
.hide{display:none}
"""

JS = """
function soUm(c){
  document.querySelectorAll('.post').forEach(p=>{
    const on=c.dataset.slug===p.dataset.slug;
    p.classList.toggle('hide',!on);
  });
  document.querySelectorAll('.tab').forEach(t=>
    t.classList.toggle('on',t.dataset.slug===c.dataset.slug));
}
"""


def build(items: list[dict], work: pathlib.Path, only_pr: int | None) -> pathlib.Path:
    (work / "assets").mkdir(parents=True, exist_ok=True)

    # agrupar por slug base (PT e EN do mesmo post)
    groups: dict[str, list[dict]] = {}
    for it in items:
        base = it["slug"][:-3] if it["slug"].endswith("-en") else it["slug"]
        groups.setdefault(base, []).append(it)

    # capas: extrair do branch do PR, para ser a imagem que vai ao vivo
    for base, group in groups.items():
        branch = group[0]["branch"]
        try:
            raw = git_bytes("show", f"origin/{branch}:posts/covers/{base}.jpg")
        except subprocess.CalledProcessError:
            continue
        (work / "assets" / f"{base}.jpg").write_bytes(raw)

    # _meta.json do branch, para o excerpt e o credit
    for base, group in groups.items():
        try:
            raw = git("show", f"origin/{group[0]['branch']}:posts/_meta.json")
            meta_all = json.loads(raw)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            meta_all = {"posts": []}
        byslug = {p.get("slug"): p for p in meta_all.get("posts", [])}
        for it in group:
            entry = byslug.get(it["slug"], {})
            it["_entry"] = entry

    html = [
        "<!doctype html><html lang=pt><head><meta charset=utf-8>",
        "<meta name=viewport content='width=device-width,initial-scale=1'>",
        "<title>Posts pendentes</title>",
        f"<style>{CSS}</style></head><body>",
        "<header><h1>Posts prontos a publicar, antes de publicar</h1>",
        f"<div class=sub>{len(groups)} post(s) em PRs abertos &middot; "
        "versao do branch, nao a de main</div></header><div class=wrap>",
    ]

    for base, group in sorted(groups.items(),
                             key=lambda kv: kv[1][0]["meta"].get("date", ""),
                             reverse=True):
        group.sort(key=lambda x: x["slug"].endswith("-en"))
        entry = group[0].get("_entry", {})
        title = entry.get("title") or group[0]["meta"].get("title", base)
        html.append(f'<article class=post data-slug="{base}">')
        html.append('<div class=bar>')
        html.append(f'<span class=pr>PR #{group[0]["pr"]}</span>')
        for it in group:
            lang = "EN" if it["slug"].endswith("-en") else "PT-BR"
            css = "en" if it["slug"].endswith("-en") else "pt"
            html.append(f'<span class="lang {css}">{lang}</span>')
        html.append(f'<span class=title>{title}</span>')
        html.append('<span class=tabs>')
        for i, it in enumerate(group):
            lang = "EN" if it["slug"].endswith("-en") else "PT-BR"
            on = "on" if i == 0 else ""
            html.append(f'<button class="tab {on}" data-slug="{base}">{lang}</button>')
        html.append("</span></div>")

        html.append(f'<img class=cover src="assets/{base}.jpg" alt="{title}">')
        date = group[0]["meta"].get("date", "")
        cat = group[0]["meta"].get("category", "")
        words = group[0]["words"]
        html.append(f'<div class=meta><span>{date}</span><span>{cat}</span>'
                    f'<span>{words} palavras</span>'
                    f'<span>{base}</span></div>')

        for i, it in enumerate(group):
            cls = "body" if i == 0 else "body hide"
            exc = entry.get("excerpt", "") if i == 0 else group[i].get("_entry", {}).get("excerpt", "")
            excerpt = (f'<div class=excerpt>{exc}</div>' if exc else "")
            credit = it.get("_entry", {}).get("cover_credit") or {}
            cred_html = ""
            if credit:
                cred_html = ("<div class=credit><b>Capa:</b> "
                             + (credit.get("file") or "?")
                             + (f" &middot; {credit.get('license')}" if credit.get("license") else "")
                             + "</div>")
            html.append(f'<div class="{cls}" id="{it["slug"]}">'
                        f"{excerpt}{it['html']}{cred_html}</div>")
        html.append("</article>")

    html.append("</div>")
    html.append(f"<script>{JS}</script>")
    html.append(
        "<script>document.querySelectorAll('.tab').forEach(t=>"
        "t.addEventListener('click',()=>soUm(t)));</script>"
    )
    html.append("</body></html>")

    out = work / "index.html"
    out.write_text("\n".join(html), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--pr", type=int, default=None)
    ap.add_argument("--no-serve", action="store_true")
    args = ap.parse_args()

    items = collect(args.pr)
    if not items:
        print("nenhum post pendente encontrado")
        return 0

    work = pathlib.Path(tempfile.mkdtemp(prefix="preview-pendentes-"))
    index = build(items, work, args.pr)

    bases = {it["slug"][:-3] if it["slug"].endswith("-en") else it["slug"] for it in items}
    print(f"{len(items)} ficheiro(s) markdown, {len(bases)} post(s)")
    for it in sorted(items, key=lambda x: x["slug"]):
        lang = "EN" if it["slug"].endswith("-en") else "PT"
        print(f"  PR #{it['pr']:>3}  {lang}  {it['words']:>5} palavras  {it['slug'][:56]}")
    print(f"\npagina: {index}")
    print(f"directorio: {work}")

    if args.no_serve:
        return 0

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(work))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"\nservir em http://127.0.0.1:{args.port}/   (Ctrl+C para sair)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nparado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())