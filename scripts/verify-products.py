#!/usr/bin/env python3
"""
verify-products.py — REGRA: preços, imagens e infos dos cards de produto
DEVEM SEMPRE ser verdadeiros e puxados direto da fonte.

Para cada produto com `url` no _meta.json:
  1. Resolve o link (meli.la de afiliado → página real do ML)
  2. Extrai da página real: og:title (produto), og:image (imagem), preço à vista do card
  3. Compara com `price` e `image` gravados no _meta.json
  4. Reporta divergência (exit 1 se --strict)

Uso:
  python3 scripts/verify-products.py            # lista divergências, exit 0
  python3 scripts/verify-products.py --strict   # exit 1 se alguma divergir
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
META = Path(__file__).resolve().parent.parent / "posts" / "_meta.json"

# Padrões numéricos crawleáveis (sem afetar exibição)
PRICE_RE = re.compile(r'aria-label="([0-9]+ reais(?: com [0-9]+ centavos)?)"')


def resolve(url: str) -> str:
    """Segue redirects do link (afiliado curto → página real)."""
    r = requests.get(url, headers=UA, allow_redirects=True, timeout=20)
    return r.url


def extract(page_html: str) -> dict:
    """Extrai produto/imagem/preço (à vista = primeiro card com price)."""
    og_title = re.search(r'<meta property="og:title" content="([^"]*)"', page_html)
    og_image = re.search(r'<meta property="og:image" content="([^"]*)"', page_html)
    price = None
    m = PRICE_RE.search(page_html)
    if m:
        label = m.group(1)
        parts = re.findall(r'\d+', label)
        if len(parts) == 2:
            price = f"R$ {int(parts[0]):,}".replace(",", ".") + f",{int(parts[1]):02d}"
        else:
            price = f"R$ {int(parts[0]):,}".replace(",", ".")
    return {
        "title": html.unescape(og_title.group(1)).strip() if og_title else None,
        "image": og_image.group(1) if og_image else None,
        "price": price,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 em qualquer divergência")
    args = ap.parse_args()

    meta = json.loads(META.read_text())
    divergencias = 0

    for post in meta["posts"]:
        for prod in post.get("products", []):
            name, url, meta_price, meta_image = prod["name"], prod["url"], prod["price"], prod["image"]
            real_url = None
            real = None
            try:
                real_url = resolve(url)
                page = requests.get(real_url, headers=UA, timeout=20).text
                # Página de verificação de conta? tenta de novo com o URL absoluto do produto
                real = extract(page)
            except Exception as e:
                print(f"⚠️  {name}: falha ao consultar fonte ({e})")
                divergencias += 1
                continue

            # Preço: normaliza para comparar
            def norm_price(p):
                if not p:
                    return None
                return p.replace("\u00a0", " ").strip()

            ok = True
            if real["image"] != meta_image:
                ok = False
                print(f"❌ {name}: IMAGEM diverge")
                print(f"   meta  : {meta_image}")
                print(f"   fonte : {real['image']}")
            if norm_price(real["price"]) != norm_price(meta_price):
                ok = False
                print(f"❌ {name}: PREÇO diverge")
                print(f"   meta  : {meta_price}")
                print(f"   fonte : {real['price']}")
            if not ok:
                divergencias += 1
            else:
                print(f"✅ {name}: {real['price']} | imagem e preço batem com a fonte ({real_url[:80]})")

    if divergencias:
        print(f"\n{divergencias} produto(s) com divergência. Atualize o _meta.json com os dados da fonte REAL.")
        if args.strict:
            sys.exit(1)
    else:
        print("\nTodos os produtos conferem com a fonte real.")


if __name__ == "__main__":
    main()