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
TOPICS = [
    # Tutoriais
    {"topic": "React Hooks avançados", "category": "tutorial", "tags": ["react", "hooks", "javascript"]},
    {"topic": "TypeScript para iniciantes", "category": "tutorial", "tags": ["typescript", "javascript"]},
    {"topic": "Como criar uma API REST com Node.js", "category": "tutorial", "tags": ["node", "api", "backend"]},
    {"topic": "CSS Grid na prática", "category": "tutorial", "tags": ["css", "frontend", "layout"]},
    {"topic": "Docker para desenvolvedores", "category": "tutorial", "tags": ["docker", "devops", "containers"]},
    # Case Studies
    {"topic": "Como construí meu portfólio minimalista", "category": "case-study", "tags": ["portfolio", "design", "react"]},
    {"topic": "Automatizando deploy com Vercel", "category": "case-study", "tags": ["vercel", "ci-cd", "deploy"]},
    # Artigos
    {"topic": "Tendências de desenvolvimento 2026", "category": "article", "tags": ["tendências", "mercado"]},
    {"topic": "Por que Rust está crescendo", "category": "article", "tags": ["rust", "linguagens"]},
    {"topic": "IA no desenvolvimento: onde estamos", "category": "article", "tags": ["ia", "ferramentas", "produtividade"]},
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

def main():
    # Clonar repo
    repo_dir = Path("/tmp/blog-content")
    if repo_dir.exists():
        subprocess.run(["rm", "-rf", repo_dir], check=True)
    
    subprocess.run(["git", "clone", f"https://github.com/{REPO}.git", repo_dir], check=True)
    
    # Escolher tópico aleatório
    import random
    topic = random.choice(TOPICS)
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
