#!/usr/bin/env python3
"""
Blog Post Generator
Gera artigos via IA e cria PR para review.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# Config
REPO = "ismaeldouglasdev/blog-content"
BRANCH_PREFIX = "post"

# Lista de temas candidatos. pick_unused_topic() descarta os que ja foram
# publicados, mas a lista precisa acompanhar o ritmo do blog: com 10 itens e 33
# posts publicados, o sorteio_secado sobrava quase nada -- e o gerador travava
# com SystemExit assim que os 10 acabavam.
#
# Regra ao adicionar: nao repetir angulo ja coberto. "Gerenciamento de memoria
# em Go" nao pode virar "Go do zero"; o topic novo tem que ser outro assunto.
TOPICS = [
    # --- React / Frontend ---
    {"topic": "React 19 e Server Actions na prática", "category": "tutorial", "tags": ["react", "server-actions", "frontend"]},
    {"topic": "Performance em React: memo, useMemo e re-renderização", "category": "tutorial", "tags": ["react", "performance", "frontend"]},
    {"topic": "Error Boundary e Suspense: tratando falhas na UI", "category": "tutorial", "tags": ["react", "erros", "frontend"]},
    {"topic": "TanStack Query: cache, revalidação e estados de servidor", "category": "tutorial", "tags": ["react", "cache", "dados"]},
    {"topic": "CSS moderno: container queries e cascade layers", "category": "tutorial", "tags": ["css", "frontend", "layout"]},
    {"topic": "Animações em CSS sem biblioteca", "category": "tutorial", "tags": ["css", "animacao", "frontend"]},
    {"topic": "Acessibilidade web na prática: WCAG sem complicação", "category": "tutorial", "tags": ["acessibilidade", "wcag", "frontend"]},
    {"topic": "Web performance: otimizando Core Web Vitals", "category": "tutorial", "tags": ["performance", "web-vitals", "frontend"]},
    {"topic": "Service Workers e PWA do zero", "category": "tutorial", "tags": ["pwa", "service-worker", "frontend"]},
    {"topic": "IndexedDB: armazenamento local no navegador", "category": "tutorial", "tags": ["storage", "navegador", "frontend"]},

    # --- TypeScript ---
    {"topic": "Decorators e metaprogramação em TypeScript", "category": "tutorial", "tags": ["typescript", "metaprogramacao"]},
    {"topic": "TypeScript do compilador ao runtime", "category": "article", "tags": ["typescript", "compilador"]},
    {"topic": "Validação de tipos em runtime com Zod", "category": "tutorial", "tags": ["typescript", "zod", "validacao"]},

    # --- Node.js / Backend ---
    {"topic": "Node.js: streams e buffers na prática", "category": "tutorial", "tags": ["node", "streams", "backend"]},
    {"topic": "Node.js: worker threads e paralelismo real", "category": "tutorial", "tags": ["node", "performance", "backend"]},
    {"topic": "API REST do zero com FastAPI", "category": "tutorial", "tags": ["python", "fastapi", "api"]},
    {"topic": "Python assíncrono: asyncio do zero", "category": "tutorial", "tags": ["python", "assincrono"]},
    {"topic": "gRPC e Protocol Buffers entre serviços", "category": "tutorial", "tags": ["grpc", "protobuf", "backend"]},
    {"topic": "Event streaming com Kafka do zero", "category": "tutorial", "tags": ["kafka", "streaming", "backend"]},
    {"topic": "WebAssembly: rodando Rust e Go no navegador", "category": "article", "tags": ["wasm", "rust", "go"]},
    {"topic": "SQLite: quando um banco em arquivo basta", "category": "article", "tags": ["sqlite", "banco-de-dados"]},

    # --- Go / Rust ---
    {"topic": "Go: goroutines, channels e concorrência", "category": "tutorial", "tags": ["go", "concorrencia"]},
    {"topic": "Go: net/http e APIs do zero", "category": "tutorial", "tags": ["go", "api", "backend"]},
    {"topic": "Rust: ownership e borrow checker sem medo", "category": "tutorial", "tags": ["rust", "ownership", "linguagens"]},
    {"topic": "Rust async com Tokio", "category": "tutorial", "tags": ["rust", "async", "tokio"]},

    # --- Banco de dados ---
    {"topic": "PostgreSQL: índices, EXPLAIN e performance", "category": "tutorial", "tags": ["postgresql", "performance", "banco-de-dados"]},
    {"topic": "PostgreSQL: JSONB e consultas semi-estruturadas", "category": "tutorial", "tags": ["postgresql", "jsonb", "banco-de-dados"]},
    {"topic": "Modelagem de dados: quando normalizar", "category": "article", "tags": ["banco-de-dados", "modelagem"]},

    # --- DevOps / Infra ---
    {"topic": "Docker do zero: imagem, container e volume", "category": "tutorial", "tags": ["docker", "containers", "devops"]},
    {"topic": "GitHub Actions: CI que roda de verdade", "category": "tutorial", "tags": ["ci-cd", "github-actions", "devops"]},
    {"topic": "Kubernetes: conceitos que você precisa antes do deploy", "category": "tutorial", "tags": ["kubernetes", "devops", "containers"]},
    {"topic": "Terraform: infraestrutura como código", "category": "tutorial", "tags": ["terraform", "iac", "devops"]},
    {"topic": "Nginx: proxy reverso e balanceamento de carga", "category": "tutorial", "tags": ["nginx", "infra", "devops"]},
    {"topic": "Observabilidade: OpenTelemetry, logs, métricas e traces", "category": "tutorial", "tags": ["observabilidade", "opentelemetry", "monitoring"]},
    {"topic": "Linux: tuning de performance e gargalo", "category": "tutorial", "tags": ["linux", "performance", "sistema"]},
    {"topic": "Bash: scripting robusto com set -euo pipefail", "category": "tutorial", "tags": ["bash", "scripting", "automacao"]},
    {"topic": "Monorepo: pnpm workspaces e Turbo", "category": "tutorial", "tags": ["monorepo", "pnpm", "turbo"]},
    {"topic": "Comparativo de bundlers: Vite, Turbopack e Webpack", "category": "article", "tags": ["build", "vite", "frontend"]},

    # --- Segurança ---
    {"topic": "OWASP Top 10: os erros que mais aparecem em produção", "category": "article", "tags": ["seguranca", "owasp"]},
    {"topic": "Autenticação vs autorização: a linha que quase todo mundo atravessa", "category": "article", "tags": ["seguranca", "auth"]},
    {"topic": "Criptografia aplicada: hashes, salts e rotação de chaves", "category": "tutorial", "tags": ["seguranca", "criptografia"]},

    # --- IA ---
    {"topic": "LLMs em produção: chamadas, custo e limites de taxa", "category": "tutorial", "tags": ["ia", "llm", "backend"]},
    {"topic": "RAG e embeddings: quando a busca semântica compensa", "category": "article", "tags": ["ia", "rag", "embeddings"]},
    {"topic": "MCP: o padrão que conecta IA a ferramentas", "category": "article", "tags": ["ia", "mcp", "ferramentas"]},
    {"topic": "Como a IA está mudando o trabalho de quem programa", "category": "article", "tags": ["ia", "carreira"]},

    # --- Curiosidade / News / Gadget ---
    {"topic": "Como o GitHub Copilot mudou meu fluxo de trabalho", "category": "article", "tags": ["ia", "github", "produtividade"]},
    {"topic": "Neovim: produtividade com configuração mínima", "category": "tutorial", "tags": ["neovim", "editor", "produtividade"]},
    {"topic": "Terminais e TUIs: interfaces de texto que ainda vencem", "category": "curiosity", "tags": ["tui", "terminal"]},
    {"topic": "Regex na prática: do básico ao que ninguém te ensinou", "category": "tutorial", "tags": ["regex", "programacao"]},
    {"topic": "Eletrônica: teclado mecânico montado do zero", "category": "gadget", "tags": ["teclado", "eletronica"]},
    {"topic": "Guia de compra: monitor para programmer em 2026", "category": "gadget", "tags": ["monitor", "hardware"]},
    {"topic": "Notebook para programar: o que importa de verdade", "category": "gadget", "tags": ["notebook", "hardware"]},

    # --- Carreira / Case studies ---
    {"topic": "Contrato de freelance: cláusulas que evitam prejuízo", "category": "case-study", "tags": ["freelance", "carreira", "contrato"]},
    {"topic": "Como precifico meu trabalho como desenvolvedor", "category": "case-study", "tags": ["freelance", "carreira", "precificacao"]},
    {"topic": "PDV e e-commerce: integrando estoque entre sistemas", "category": "case-study", "tags": ["pdv", "ecommerce", "arquitetura"]},
    {"topic": "Migrar um sistema legado sem parar de vender", "category": "case-study", "tags": ["legado", "migracao", "arquitetura"]},
]

EM_DASH_PATTERN = re.compile(r'[—–]')
AI_SLOP_PATTERNS = [
    re.compile(r'(?i)the text you provided is already in english'),
    re.compile(r'(?i)doesn\'t need translation'),
    re.compile(r'(?i)if you have.*english'),
    re.compile(r'(?i)here is the (translation|english version)'),
    re.compile(r'(?i)translated article:'),
    re.compile(r'(?i)here\'s the (translation|english)'),
]

def contains_em_dash(text: str) -> bool:
    """Check if text contains em dash or en dash."""
    return bool(EM_DASH_PATTERN.search(text))

def contains_ai_slop(text: str) -> bool:
    """Check if text contains AI meta-responses instead of actual content."""
    for pattern in AI_SLOP_PATTERNS:
        if pattern.search(text):
            return True
    return False

def sanitize_em_dashes(text: str) -> str:
    """Replace em dashes and en dashes with regular dashes or commas."""
    # Replace em dash with " - " or ", "
    text = text.replace('—', ' - ').replace('–', '-')
    # Fix double spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def call_llm(prompt: str, max_tokens: int = 2000) -> str:
    """Chama o 9Router e retorna o texto gerado."""
    response = requests.post(
        "http://localhost:20131/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": "groq/llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_excerpt(content: str, max_len: int = 160) -> str:
    """Generate a proper excerpt from article content."""
    # Remove frontmatter if present
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            content = parts[2]
    
    # Find first meaningful paragraph (skip headings, code blocks)
    lines = content.strip().split('\n')
    paragraphs = []
    current_para = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
            continue
        # Skip headings
        if line.startswith('#'):
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
            continue
        # Skip code fences
        if line.startswith('```'):
            if current_para:
                paragraphs.append(' '.join(current_para))
                current_para = []
            continue
        current_para.append(line)
    
    if current_para:
        paragraphs.append(' '.join(current_para))
    
    # Get first substantial paragraph
    for para in paragraphs:
        if len(para) > 50:
            if len(para) <= max_len:
                return sanitize_em_dashes(para)
            # Try to cut at the last sentence ending before max_len
            cut = para[:max_len]
            for sep in ('. ', '! ', '? '):
                idx = cut.rfind(sep)
                if idx > max_len // 2:
                    return sanitize_em_dashes(cut[:idx + 1])
            # Fallback: last space (no sentence boundary found)
            return sanitize_em_dashes(cut.rsplit(' ', 1)[0] + '...')
    
    # Fallback: first 160 chars of content
    return sanitize_em_dashes(content[:max_len].rsplit(' ', 1)[0] + '...')


def generate_content(topic_info: dict) -> dict:
    """Gera conteúdo do post (PT) e sua tradução (EN) via IA."""
    topic = topic_info["topic"]
    category = topic_info["category"]
    
    # Prompt para gerar artigo
    prompt = f"""Escreva um artigo técnico para blog sobre: {topic}

Requisitos:
- Tom profissional mas acessível
- 800-1200 palavras
- Use exemplos de código quando aplicável
- Inclua introdução, desenvolvimento e conclusão
- Formato Markdown
- Linguagem: Português do Brasil
- NÃO use travessões (— ou –), use vírgulas ou " - " entre espaços
- NÃO use aspas curvas (“”), use aspas retas ("")

Retorne APENAS o conteúdo em Markdown, sem frontmatter."""
    
    try:
        content_pt = call_llm(prompt)
    except Exception as e:
        print(f"Erro ao gerar conteúdo: {e}")
        return None
    
    # Sanitize Portuguese content
    if contains_em_dash(content_pt):
        print("Aviso: conteúdo PT contém travessões, sanitizando...")
        content_pt = sanitize_em_dashes(content_pt)
    
    # Generate PT excerpt
    excerpt_pt = generate_excerpt(content_pt)
    
    # Generate English translation
    try:
        prompt_en = f"""Translate the article below to natural US English.

Rules:
- Natural, fluent translation - not machine-like
- Keep code blocks, variable names, and URLs intact
- Translate user-visible strings inside code (e.g., console.log, error messages) when it makes sense
- Keep the Markdown format and heading structure
- DO NOT use em dashes (—) or en dashes (–), use commas or " - " with spaces
- DO NOT use curly quotes (“”), use straight quotes (")
- Return ONLY the translated Markdown content, without frontmatter
- DO NOT include any meta-commentary like "Here is the translation" or "The text is already in English"

ORIGINAL ARTICLE (PT-BR):
{content_pt}"""
        content_en = call_llm(prompt_en, max_tokens=2500)
    except Exception as e:
        print(f"Erro ao gerar tradução EN: {e}")
        content_en = None
    
    # Validate English translation
    if content_en:
        if contains_ai_slop(content_en):
            print("Erro: tradução EN contém resposta de IA em vez de tradução. Tentando novamente...")
            # Retry with stricter prompt
            retry_prompt = prompt_en + "\n\nIMPORTANTE: Retorne APENAS o artigo traduzido. Sem comentários, sem meta-texto."
            content_en = call_llm(retry_prompt, max_tokens=2500)
        
        if contains_ai_slop(content_en):
            print("Erro: tradução EN ainda contém resposta de IA. Abortando.")
            content_en = None
        
        # Sanitize em dashes in EN content
        if contains_em_dash(content_en):
            print("Aviso: tradução EN contém travessões, sanitizando...")
            content_en = sanitize_em_dashes(content_en)
    
    if not content_en:
        print("Aviso: tradução EN falhou ou foi rejeitada, post ficará só em PT")
    
    # Generate English excerpt
    excerpt_en = generate_excerpt(content_en) if content_en else None
    
    # Gerar slug e metadata
    date = datetime.now().strftime("%Y-%m-%d")
    slug = topic.lower().replace(" ", "-").replace(":", "").replace("?", "")
    slug = slug[:50]
    
    title = topic
    
    return {
        "title": title,
        "date": date,
        "category": category,
        "tags": topic_info["tags"],
        "excerpt": excerpt_pt,
        "excerpt_en": excerpt_en,
        "slug": f"{date}-{slug}",
        "content": content_pt,
        "content_en": content_en,
    }

def create_post(post_data: dict) -> bool:
    """Cria o post PT + versão EN no repo."""
    repo_dir = Path("/tmp/blog-content")
    
    # Criar branch
    branch = f"{BRANCH_PREFIX}/{post_data['slug']}"
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo_dir, check=True)
    
    # Criar diretório de posts se não existir
    posts_dir = repo_dir / "posts"
    posts_dir.mkdir(exist_ok=True)
    
    # Criar frontmatter PT
    frontmatter = f"""---
title: "{post_data['title']}"
date: "{post_data['date']}"
category: "{post_data['category']}"
tags: {json.dumps(post_data['tags'])}
excerpt: "{post_data['excerpt'].replace('"', '\\"')}"
---

"""
    
    # Escrever post PT
    post_file = posts_dir / f"{post_data['slug']}.md"
    post_file.write_text(frontmatter + post_data["content"])
    
    # Escrever post EN (quando disponível)
    if post_data.get("content_en"):
        en_title = post_data["title"]
        en_excerpt = post_data["excerpt_en"] or post_data["excerpt"]
        frontmatter_en = f"""---
title: "{en_title}"
date: "{post_data['date']}"
category: "{post_data['category']}"
tags: {json.dumps(post_data['tags'])}
excerpt: "{en_excerpt.replace('"', '\\"')}"
lang: "en"
translation_of: "{post_data['slug']}"
---

"""
        en_file = posts_dir / f"{post_data['slug']}-en.md"
        en_file.write_text(frontmatter_en + post_data["content_en"])
    
    # Atualizar _meta.json
    meta_file = posts_dir / "_meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
    else:
        meta = {"posts": []}
    
    pt_entry = {
        "slug": post_data["slug"],
        "title": post_data["title"],
        "date": post_data["date"],
        "category": post_data["category"],
        "excerpt": post_data["excerpt"],
    }
    en_entry = None
    if post_data.get("content_en"):
        pt_entry["lang"] = "pt"
        pt_entry["translation_slug"] = f"{post_data['slug']}-en"
        en_entry = {
            "slug": f"{post_data['slug']}-en",
            "title": post_data["title"],
            "date": post_data["date"],
            "category": post_data["category"],
            "excerpt": post_data["excerpt_en"] or post_data["excerpt"],
            "lang": "en",
            "translation_slug": post_data["slug"],
            "translation_of": post_data["slug"],
        }
    
    meta["posts"].append(pt_entry)
    if en_entry:
        meta["posts"].append(en_entry)
    
    # Ordenar por data (mais recente primeiro)
    meta["posts"].sort(key=lambda x: x["date"], reverse=True)
    meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    
    # Commit
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", f"post: {post_data['title']}"], cwd=repo_dir, check=True)
    
    return True

def create_pr(branch: str, title: str) -> str:
    """Cria PR no GitHub."""
    result = subprocess.run(
        ["gh", "pr", "create", "--repo", REPO, "--title", f"Blog: {title}", "--body", "Artigo gerado automaticamente. Revise antes de merge."],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if "https://github.com" in line:
                return line.strip()
    return None

def published_topics(repo_dir: Path) -> set:
    """Topicos ja publicados, lidos do _meta.json do repo clonado.

    Sem essa checagem o `random.choice(TOPICS)` sortava o mesmo tema varias
    vezes: a lista tem 11 itens e nao muda, entao com 1 post/dia a repeticao
    era garantida -- foi assim que 'Testing Library' saiu em 01/09, 17/09, 25/09
    e 26/09, quatro datas para o mesmo artigo.
    """
    meta_path = repo_dir / "posts" / "_meta.json"
    used = set()
    if not meta_path.exists():
        return used
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Aviso: nao foi possivel ler {meta_path} ({exc}); "
              "assumindo nenhum topico usado.")
        return used

    for post in data.get("posts", []):
        slug = post.get("slug", "")
        # Remove a data e o sufixo -en: o que identifica o tema e o miolo do slug.
        topic_slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
        topic_slug = re.sub(r"-en$", "", topic_slug)
        if topic_slug:
            used.add(topic_slug)
    return used


def slugify_topic(topic: str) -> str:
    """Deriva o slug de um topico da lista TOPICS no mesmo formato dos publicados."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", topic.lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")


def pick_unused_topic(repo_dir: Path) -> dict:
    """Escolhe um topico que ainda nao foi publicado.

    A lista TOPICS e' estatica e nao acompanha o que o blog ja cobriu, entao
    casar por slug exato falha. Por isso a selecao e' por palavra-chave: um topico
    e' considerado usado quando pelo menos dois termos seus (sem stopwords)
    aparecem no slug de algum post ja publicado. Exigir dois termos evita falso
    positivo por palavras genericas como 'para', 'com' ou 'como'.
    """
    import random

    stopwords = {
        "para", "com", "que", "por", "uma", "como", "na", "no", "de", "da",
        "do", "das", "dos", "em", "a", "o", "e", "nao", "mais", "seu",
        "sua", "pratica", "pratico",
    }

    used = published_topics(repo_dir)
    used_words = set()
    for slug in used:
        used_words.update(
            w for w in slug.split("-") if len(w) >= 3 and w not in stopwords
        )

    def is_used(candidate: dict) -> bool:
        if slugify_topic(candidate["topic"]) in used:
            return True
        significant = [
            w for w in slugify_topic(candidate["topic"]).split("-")
            if len(w) >= 3 and w not in stopwords
        ]
        if not significant:
            return False
        hits = sum(1 for w in significant if w in used_words)
        # >= 2 termos E >= metade dos termos significativos: preciso o bastante
        # para nao bloquear topico novo so por sharespalavras genericas.
        return hits >= 2 and hits >= len(significant) / 2

    available = [t for t in TOPICS if not is_used(t)]
    if not available:
        raise SystemExit(
            "Todos os topicos da lista TOPICS ja foram publicados. "
            "Atualize TOPICS em generate-post.py antes de rodar de novo."
        )

    print(f"Topicos disponiveis: {len(available)}/{len(TOPICS)} "
          f"(ja publicados: {len(TOPICS) - len(available)})")
    return random.choice(available)


def main():
    # Clonar repo
    repo_dir = Path("/tmp/blog-content")
    if repo_dir.exists():
        subprocess.run(["rm", "-rf", repo_dir], check=True)
    
    subprocess.run(["git", "clone", f"https://github.com/{REPO}.git", repo_dir], check=True)
    
    # Escolher topico aleatorio entre os que ainda nao foram publicados
    topic = pick_unused_topic(repo_dir)
    print(f"Gerando artigo sobre: {topic['topic']}")
    
    # Gerar conteúdo
    post_data = generate_content(topic)
    if not post_data:
        print("Falha ao gerar conteúdo")
        sys.exit(1)
    
    # Criar post
    if create_post(post_data):
        # Push
        branch = f"{BRANCH_PREFIX}/{post_data['slug']}"
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=repo_dir, check=True)
        
        # Criar PR
        pr_url = create_pr(branch, post_data["title"])
        if pr_url:
            print(f"PR criado: {pr_url}")
        else:
            print("Falha ao criar PR")
    
    print("Concluído!")

if __name__ == "__main__":
    main()
