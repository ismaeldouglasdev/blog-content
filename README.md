# Blog Content

Repositório privado com artigos do blog ismaeltech.com.

## Estrutura

```
posts/
├── 2026-08-17-como-criar-api-rest.md
├── 2026-08-16-react-hooks-guia.md
└── _meta.json
```

## Formato dos Posts

Cada post é um Markdown com frontmatter:

```markdown
---
title: "Como Criar uma API REST"
date: "2026-08-17"
category: "tutorial"
tags: ["node", "express", "api"]
excerpt: "Guia completo para criar APIs REST modernas"
cover: "https://..."
---

Conteúdo do artigo aqui...
```

## Automação

Script `generate-post.py` roda via cron diariamente:
1. Gera conteúdo via IA
2. Cria branch `post/YYYY-MM-DD`
3. Abre PR para review
4. Após merge, portfolio faz deploy automático

## REGRA: cards de produto (afiliado Mercado Livre)

Preços, imagens e infos dos `products` no `_meta.json` **devem SEMPRE ser
verdadeiros e puxados direto da fonte real**. NUNCA inventar, estimar ou copiar
preço/imagem de anúncio antigo/de outro vendedor.

- O campo `url` é o link de afiliado (ex.: `meli.la/...`) — **não alterar**.
- Para obter os dados corretos de um produto: resolva o `url` (segue o redirect)
  e extraia do HTML real: `og:title` (nome do produto), `og:image` (imagem) e o
  preço à vista do card em destaque.
- Após qualquer mudança em `products`, rode a verificação:

```bash
python3 scripts/verify-products.py          # mostra divergências
python3 scripts/verify-products.py --strict # exit 1 se alguma divergir
```

O script resolve cada link de afiliado e compara `price`/`image` do meta com a
fonte real, reportando o que estiver desatualizado.
