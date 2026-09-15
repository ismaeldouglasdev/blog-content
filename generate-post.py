#!/usr/bin/env python3
"""
Blog Post Generator
Gera artigos via IA e cria PR para review.
"""

import json
import os
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

Retorne APENAS o conteúdo em Markdown, sem frontmatter."""
    
    try:
        content_pt = call_llm(prompt)
    except Exception as e:
        print(f"Erro ao gerar conteúdo: {e}")
        return None
    
    try:
        prompt_en = f"""Translate the article below to US English.

Rules:
- Natural translation, not machine-like
- Keep code blocks, variable names and URLs intact
- Translate user-visible strings inside code (e.g. console.log, error messages) when it makes sense
- Keep the Markdown format and heading structure
- Return ONLY the translated Markdown content, without frontmatter

ORIGINAL ARTICLE (PT-BR):
{content_pt}"""
        content_en = call_llm(prompt_en, max_tokens=2500)
    except Exception as e:
        print(f"Erro ao gerar tradução EN: {e}")
        content_en = None
    
    if not content_en:
        print("Aviso: tradução EN falhou, post ficará só em PT")
    
    # Gerar slug e metadata
    date = datetime.now().strftime("%Y-%m-%d")
    slug = topic.lower().replace(" ", "-").replace(":", "").replace("?", "")
    slug = slug[:50]  # Limitar tamanho
    
    title = topic
    
    # Gerar excerpt
    first_line = content_pt.split("\n")[0][:150]
    
    return {
        "title": title,
        "date": date,
        "category": category,
        "tags": topic_info["tags"],
        "excerpt": first_line,
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
    
    # Criar frontmatter
    frontmatter = f"""---
title: "{post_data['title']}"
date: "{post_data['date']}"
category: "{post_data['category']}"
tags: {json.dumps(post_data['tags'])}
excerpt: "{post_data['excerpt']}"
---

"""
    
    # Escrever post PT
    post_file = posts_dir / f"{post_data['slug']}.md"
    post_file.write_text(frontmatter + post_data["content"])
    
    # Escrever post EN (quando disponível)
    if post_data.get("content_en"):
        en_title = post_data["title"]
        en_excerpt = post_data["excerpt"]
        frontmatter_en = f"""---
title: "{en_title}"
date: "{post_data['date']}"
category: "{post_data['category']}"
tags: {json.dumps(post_data['tags'])}
excerpt: "{en_excerpt}"
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
            "excerpt": post_data["excerpt"],
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
        # Extrair URL do PR
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
