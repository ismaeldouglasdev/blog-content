#!/usr/bin/env python3
"""Backfill read-only por padrão para posts sem cover_meta.

Não altera imagens, URLs ou conteúdo. Use --apply explicitamente para gravar.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def build_legacy_meta(post: dict) -> dict:
    return {
        "strategy": "legacy",
        "source": "historical",
        "review_status": "unreviewed",
        "relevance_score": None,
        "cover": post.get("cover"),
        "note": "Existing asset preserved; regenerate through review workflow before approval.",
    }


def backfill_meta(workspace: Path, apply: bool = False) -> dict:
    meta_path = workspace / "posts" / "_meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(meta_path)
    original_bytes = meta_path.read_bytes()
    document = json.loads(original_bytes.decode("utf-8"))
    posts = document.get("posts", [])
    updated: list[str] = []
    skipped: list[str] = []
    for post in posts:
        slug = post.get("slug", "")
        if isinstance(post.get("cover_meta"), dict):
            skipped.append(slug)
            continue
        post["cover_meta"] = build_legacy_meta(post)
        updated.append(slug)
    backup_path = None
    if apply and updated:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = meta_path.with_name(f"_meta.json.bak-cover-meta-{stamp}")
        backup_path.write_bytes(original_bytes)
        meta_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "workspace": str(workspace),
        "applied": apply,
        "updated": updated,
        "skipped": skipped,
        "backup": str(backup_path) if backup_path else None,
        "posts": len(posts),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Registra cover_meta legacy sem alterar imagens.")
    parser.add_argument("workspace", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--apply", action="store_true", help="Grava as mudanças; sem esta flag é dry-run.")
    args = parser.parse_args(argv)
    result = backfill_meta(args.workspace, args.apply)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
