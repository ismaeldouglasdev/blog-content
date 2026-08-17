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
