#!/usr/bin/env python3
"""Verificador read-only de covers do blog.

Combina análise visual local com consistência de `_meta.json`, assets e pares
PT/EN. Não baixa imagens, não escreve arquivos e não depende da rede.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

THRESHOLDS = {
    "white_frac": 0.60,
    "black_frac": 0.60,
    "luma_std_min": 12.0,
    "unique_colors_min": 25,
}
MIN_PHOTO_SCORE = 0.62


def jpeg_dimensions(path: Path | str) -> tuple[int, int] | None:
    """Lê largura/altura de um JPEG só com a stdlib, percorrendo os marcadores SOF.

    Existe para que a checagem de integridade do asset (existe, e JPEG, e
    1200x630) funcione em maquina sem Pillow. A analise de pixel continua
    dependendo de Pillow, porque decidir "BRANCO 80%" exige decodificar a
    imagem. Um asset truncado ou corrompido nao tem marcador SOF e aqui
    retorna None, que e exatamente o sinal de erro que o chamador espera.
    """
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if len(data) < 4 or data[:2] != b"\xff\xd8":  # SOI
        return None
    i = 2
    n = len(data)
    while i + 3 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # marcadores SOF de frame, exceto os de codificacao(DHT/DAC/RST/SOI)
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if i + 9 >= n:
                return None
            h = (data[i + 5] << 8) | data[i + 6]
            w = (data[i + 7] << 8) | data[i + 8]
            return (w, h) if w and h else None
        # segmentos sem payload proprio
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        if i + 4 > n:
            return None
        seg_len = (data[i + 2] << 8) | data[i + 3]
        if seg_len < 2:
            return None
        i += 2 + seg_len
    return None


def analyze(path: Path | str) -> dict:
    """Analise de pixel. Exige Pillow: sem ele, o chamador usa jpeg_dimensions."""
    path = Path(path)
    if Image is None:
        raise RuntimeError("Pillow não está instalado")
    with Image.open(path) as source:
        image = source.convert("RGB")
    w, h = image.size
    pixels = image.load()
    step = max(1, w // 300)
    total = white = black = 0
    luma_sum = luma_sq = 0.0
    colors: set[tuple[int, int, int]] = set()
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = pixels[x, y]
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            total += 1
            luma_sum += luma
            luma_sq += luma * luma
            if luma > 245:
                white += 1
            elif luma < 10:
                black += 1
            colors.add((r >> 3, g >> 3, b >> 3))
    luma_std = (luma_sq / total - (luma_sum / total) ** 2) ** 0.5
    return {
        "file": path.name,
        "size": f"{w}x{h}",
        "width": w,
        "height": h,
        "white_frac": white / total,
        "black_frac": black / total,
        "luma_std": luma_std,
        "unique_colors": len(colors),
        "mean_luma": luma_sum / total,
    }


def _visual_flags(metrics: dict) -> list[str]:
    flags = []
    if metrics["white_frac"] > THRESHOLDS["white_frac"]:
        flags.append(f"BRANCO {metrics['white_frac'] * 100:.0f}%")
    if metrics["black_frac"] > THRESHOLDS["black_frac"]:
        flags.append(f"PRETO {metrics['black_frac'] * 100:.0f}%")
    if metrics["luma_std"] < THRESHOLDS["luma_std_min"]:
        flags.append(f"SEM-TEXTURA std={metrics['luma_std']:.1f}")
    if metrics["unique_colors"] < THRESHOLDS["unique_colors_min"]:
        flags.append(f"POUCAS-CORES {metrics['unique_colors']}")
    return flags


def _asset_name(url: str, slug: str) -> str:
    return Path(urlparse(url or "").path).name or f"{slug}.jpg"


def verify_workspace(workspace: Path) -> dict:
    posts_dir = workspace / "posts"
    covers_dir = posts_dir / "covers"
    meta_path = posts_dir / "_meta.json"
    findings: list[dict] = []
    files: list[dict] = []
    errors = warnings = 0

    def add(severity: str, code: str, slug: str, message: str) -> None:
        nonlocal errors, warnings
        findings.append({"severity": severity, "code": code, "slug": slug, "message": message})
        if severity == "error":
            errors += 1
        elif severity == "warning":
            warnings += 1

    if not meta_path.exists():
        add("error", "meta_missing", "", f"Não encontrado: {meta_path}")
        return {"workspace": str(workspace), "ok": False, "summary": {"posts": 0, "errors": 1, "warnings": 0}, "files": [], "findings": findings}
    try:
        posts = json.loads(meta_path.read_text(encoding="utf-8")).get("posts", [])
    except (json.JSONDecodeError, OSError) as exc:
        add("error", "meta_unreadable", "", str(exc))
        return {"workspace": str(workspace), "ok": False, "summary": {"posts": 0, "errors": 1, "warnings": 0}, "files": [], "findings": findings}

    by_cover: dict[str, list[str]] = {}
    for post in posts:
        slug = post.get("slug") or ""
        cover = post.get("cover") or ""
        asset = covers_dir / _asset_name(cover, slug)
        canonical_slug = slug[:-3] if slug.endswith("-en") else slug
        by_cover.setdefault(asset.name, []).append(canonical_slug)
        metrics = None
        if not cover:
            add("error", "cover_missing", slug, "Post sem URL de capa")
        elif asset.suffix.lower() != ".jpg":
            add("error", "cover_not_jpg", slug, f"Formato não-JPG: {asset.name}")
        elif not asset.exists():
            add("error", "asset_missing", slug, f"Asset ausente: {asset}")
        else:
            if Image is not None:
                try:
                    metrics = analyze(asset)
                    files.append({"slug": slug, "asset": str(asset), **metrics})
                    if (metrics["width"], metrics["height"]) != (1200, 630):
                        add("error", "wrong_dimensions", slug, f"{metrics['size']} != 1200x630")
                    for flag in _visual_flags(metrics):
                        add("warning", "visual_heuristic", slug, flag)
                except Exception as exc:  # asset corrompido não deve derrubar o relatório
                    add("error", "asset_unreadable", slug, str(exc))
            else:
                # Sem Pillow: a integridade do asset continua verificavel pelo
                # cabecalho JPEG. So a heuristica de pixel (BRANCO/PRETO/
                # SEM-TEXTURA) fica indisponivel -- e isso e ambiente, nao
                # defeito do post, entao vira UM aviso agregado, nao 1 erro
                # por post. Reportar 68 "asset_unreadable" antes dizia que os
                # 68 assets estavam corrompidos, o que era mentira.
                dims = jpeg_dimensions(asset)
                if dims is None:
                    add("error", "asset_unreadable", slug, "JPEG sem cabeçalho legível (truncado ou corrompido)")
                else:
                    w, h = dims
                    files.append({"slug": slug, "asset": str(asset), "width": w, "height": h, "size": f"{w}x{h}"})
                    if (w, h) != (1200, 630):
                        add("error", "wrong_dimensions", slug, f"{w}x{h} != 1200x630")

        meta = post.get("cover_meta")
        if not isinstance(meta, dict):
            add("warning", "cover_meta_legacy", slug, "Post sem cover_meta")
        else:
            strategy = meta.get("strategy")
            if strategy == "photo":
                score = meta.get("relevance_score")
                if not isinstance(score, (int, float)) or score < MIN_PHOTO_SCORE:
                    add("error", "photo_score_low", slug, f"Score {score} < {MIN_PHOTO_SCORE}")
                if meta.get("review_status") != "approved":
                    add("warning", "photo_review_status", slug, f"review_status={meta.get('review_status')}")
                if not (post.get("cover_credit") or {}).get("license"):
                    add("error", "photo_license_missing", slug, "Foto sem licença")
            elif strategy == "legacy":
                if meta.get("review_status") != "unreviewed":
                    add("warning", "legacy_review_status", slug, f"review_status={meta.get('review_status')}")
            elif strategy == "fallback":
                add("error", "ai_fallback_cover", slug,
                    "capa gerada por codigo (source=code, auto_fallback). "
                    "O dono pediu imagens reais, nao feitas por IA. Substituir "
                    "por fotografia com licenca e pôr review_status=approved")
            else:
                add("warning", "unknown_strategy", slug, f"strategy={strategy}")

    if Image is None and files:
        add(
            "warning",
            "visual_analysis_skipped",
            "",
            f"Análise visual de pixel indisponível (Pillow não instalado): "
            f"integridade e 1200x630 de {len(files)} capas foram verificadas "
            f"pelo cabeçalho JPEG, mas BRANCO/PRETO/SEM-TEXTURA não rodaram.",
        )

    for asset_name, slugs in by_cover.items():
        if len(slugs) > 1 and len(set(slugs)) > 1:
            add("warning", "duplicate_cover", ",".join(sorted(set(slugs))), f"Asset reutilizado: {asset_name}")

    # Capa solta em posts/covers/ que nenhum post referencia. A CI ja barra .md
    # orfao desde o caso do espelho bidirecional, mas capa nao tinha o mesmo
    # portao -- e o resultado foi um .svg de arte gerada commitado e servindo no
    # CDN sem ninguem notar, mais 7 versoes pre-revisao devolvidas pelo espelho.
    # `git add -A` publicaria arte velha de capa. Severidade warning, e nao
    # error: orfao nao quebra o site, ele so polui o repositorio e o CDN.
    referenced_assets = set(by_cover)
    for asset in sorted(covers_dir.iterdir()):
        if not asset.is_file() or asset.name in referenced_assets:
            continue
        if asset.name == "_meta.json":
            continue
        add(
            "warning",
            "orphan_cover",
            "",
            f"Asset sem post referenciando: {asset.name}",
        )

    return {
        "workspace": str(workspace),
        "ok": errors == 0,
        "summary": {
            "posts": len(posts),
            "files": len(files),
            "errors": errors,
            "warnings": warnings,
            "legacy": sum(1 for item in findings if item["code"] == "cover_meta_legacy"),
            "legacy_registered": sum(1 for post in posts if isinstance(post.get("cover_meta"), dict) and post["cover_meta"].get("strategy") == "legacy"),
        },
        "files": files,
        "findings": findings,
    }


def render_text(report: dict) -> str:
    summary = report["summary"]
    lines = [
        f"Workspace: {report['workspace']}",
        f"Posts: {summary['posts']} | assets: {summary.get('files', 0)} | findings: {summary['errors']} error, {summary['warnings']} warning",
    ]
    for item in report["findings"]:
        lines.append(f"[{item['severity'].upper()}] {item['slug'] or '-'}: {item['code']} — {item['message']}")
    if not report["findings"]:
        lines.append("OK: nenhum problema encontrado.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Verifica capas do blog sem escrever arquivos.")
    parser.add_argument("workspace", nargs="?", type=Path, default=default_root)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--fail-on", choices=("never", "warning", "error"), default="error")
    args = parser.parse_args(argv)
    report = verify_workspace(args.workspace)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.format == "json" else render_text(report))
    if args.fail_on == "never":
        return 0
    level = "warnings" if args.fail_on == "warning" else "errors"
    return int(report["summary"][level] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
