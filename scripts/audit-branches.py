#!/usr/bin/env python3
"""
Auditoria das branches obsoletas do blog-content.

Veredito: o post que a branch nomeia ainda esta publicado no main? E o que
decide se ha trabalho perdido. Nao "o titulo bate" e nao "a branch esta
mergeada" -- as duas coisas mentem.

Tres armadilhas que esta auditoria atravessou, todas com consequencia real:

1. Testar a BRANCH inteira em vez do POST. Cada branch e um snapshot do
   diretorio posts/ inteiro, nao o post que a nomeia. O primeiro .md que
   falha pode ser um post de agosto numa branch de setembro. O
   prune-branches.sh (v1) reportava `post/2026-08-20-devtools...` como
   perdendo "CSS Grid vs Flexbox" -- que nao tem nada a ver com devtools --
   e por isso preservava 25 das 41 branches sem necessidade.

2. Assumir que existe posts/<slug>.md. O nome da branch e TRUNCADO:
     post/2026-08-18-react-hooks-avancados-useeffect,-useref-e-custom-hooks-que-v
   enquanto o arquivo real e bem mais longo. Entao o caminho testado nao
   existe, e "post nao encontrado na branch" e falha da verificacao, nao
   ausencia do post. O certo e casar por PREFIXO.

3. Comparar titulo cru. Duas branches "nao publicadas" estavam publicadas:
      branch "Autenticacao JWT completa: ..."  main "Autenticação JWT completa: ..."
      branch slug 2026-08-27-serverless-...   main slug 2026-08-24-serverless-...
   A branch guarda versao ANTIGA do post, sem acento e com outra data. Falso
   negativo aqui e o erro caro: manda preservar branch sem nada de unico.

Por isso a comparacao normaliza (minusculas, sem acento) e a data do slug
nao decides nada -- o titulo manda.

Este script nao apaga nada. Ele classifica, para a decisao ser informavel.
Com --emit-safe imprime so as branches seguras, uma por linha, que e o que
o prune-branches.sh consome -- a logica fica em UM lugar, porque duplicar
logica de verificacao foi exatamente o que gerou os tres bugs acima.
"""
import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

OWNER = "ismaeldouglasdev"
REPO = "blog-content"
REPO_DIR = Path.home() / "blog-content"


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(
        ["git", "-C", str(REPO_DIR), *args], capture_output=True, text=True,
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou: {r.stderr.strip()[:160]}")
    return r.stdout


def normalizar(t: str) -> str:
    """Minusculas e sem acento, para comparar titulo que foi reescrito."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def existe(ref: str) -> bool:
    return git("cat-file", "-e", ref, check=False).strip() != "" or (
        subprocess.run(["git", "-C", str(REPO_DIR), "cat-file", "-e", ref],
                       capture_output=True).returncode == 0
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-safe", action="store_true",
                    help="imprime so as branches seguras, uma por linha")
    args = ap.parse_args()

    git("fetch", "-q", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*")

    branches = []
    for cru in git("branch", "-r").splitlines():
        b = cru.strip()
        if not b:
            continue
        # symref: "origin/HEAD -> origin/main". endswith("/HEAD") NAO pega,
        # porque a linha termina em "origin/main". Sem este filtro, o
        # prune-branches.sh tentaria apagar origin/HEAD.
        if "->" in b:
            continue
        if b in ("origin/main", "main"):
            continue
        branches.append(b)

    # indice de titulos normalizados do main -> arquivo
    indice: dict[str, str] = {}
    main_md = [a for a in git("ls-tree", "-r", "--name-only", "origin/main").split()
               if a.endswith(".md") and a.startswith("posts/")]
    for arquivo in main_md:
        m = re.search(r'^title:\s*"(.*)"\s*$', git("show", f"origin/main:{arquivo}"), re.M)
        if m:
            indice.setdefault(normalizar(m.group(1)), arquivo)
    slugs_main = {Path(a).stem for a in main_md}

    seguros: list[str] = []
    renomeados: list[tuple[str, str]] = []
    preservados: list[tuple[str, str]] = []

    for b in branches:
        nome = b[len("origin/"):] if b.startswith("origin/") else b

        # --- branch que nao nomeia post: dist-publish, fix-cover-...
        if not nome.startswith("post/"):
            mergeado = subprocess.run(
                ["git", "-C", str(REPO_DIR), "merge-base", "--is-ancestor", b, "origin/main"],
                capture_output=True,
            ).returncode == 0
            if mergeado:
                seguros.append(nome)
                continue
            # nao mergeada: exige que TODO arquivo divergente ja exista no main
            # com conteudo identico. diff contra o ancestral, nao contra main,
            # porque main andou depois.
            base = subprocess.run(
                ["git", "-C", str(REPO_DIR), "merge-base", b, "origin/main"],
                capture_output=True, text=True).stdout.strip()
            if not base:
                preservados.append((nome, "sem ancestral comum com main"))
                continue
            divergentes = [f for f in git("diff", "--name-only", base, b).split() if f]
            perdeu = [f for f in divergentes
                      if not existe(f"origin/main:{f}")
                      or subprocess.run(["git", "-C", str(REPO_DIR), "diff", "--quiet",
                                        f"origin/main:{f}", f"{b}:{f}"],
                                       capture_output=True).returncode != 0]
            if perdeu:
                # IMPORTANTE: dizer a verdade aqui. Estes arquivos ESTAO no main
                # -- o que muda e o conteudo. A versao da branch e uma variante
                # mais antiga (main tem 401 linhas contra 309, e features que a
                # branch nao tem). Isso e forte indicio de que a branch e
                # obsoleta, mas "forte indicio" nao e prova, e apagar e sem
                # volta. Então preserva e deixa o humano olhar.
                preservados.append(
                    (nome, f"{len(perdeu)} arquivo(s) com conteudo divergente do main "
                           f"(existem no main, mas versao diferente): {', '.join(perdeu[:3])}")
                )
            else:
                seguros.append(nome)
            continue

        # --- branch post/<slug truncado>
        slug = nome[len("post/"):]
        base_slug = slug[:-3] if slug.endswith("-en") else slug
        if base_slug in slugs_main or slug in slugs_main:
            seguros.append(nome)
            continue

        # casa por PREFIXO, porque o nome da branch e truncado
        candidatos = [
            a for a in git("ls-tree", "-r", "--name-only", b, "--", "posts/").split()
            if a.endswith(".md")
            and (Path(a).stem.startswith(base_slug) or Path(a).stem.rstrip("-en") == base_slug)
        ]
        if not candidatos:
            preservados.append((nome, "nenhum .md casa com o nome da branch"))
            continue
        candidatos.sort(key=lambda p: (p.endswith("-en.md"), p))
        m = re.search(r'^title:\s*"(.*)"\s*$', git("show", f"{b}:{candidatos[0]}"), re.M)
        titulo = m.group(1) if m else ""
        destino = indice.get(normalizar(titulo))
        if destino:
            renomeados.append((nome, destino))
        else:
            preservados.append((nome, titulo or "(sem title legivel)"))

    if args.emit_safe:
        for nome in seguros + [n for n, _ in renomeados]:
            print(nome)
        return 0

    print("AUDITORIA DAS BRANCHES OBSOLETAS DO blog-content")
    print()
    print(f"  branches (sem main)          : {len(branches)}")
    print(f"  SEGURAS                     : {len(seguros) + len(renomeados)}")
    print(f"    mesmo slug, versao antiga : {len(seguros) - len([1 for n in seguros if not n.startswith('post/')])}")
    print(f"    nao mergeadas, sem perda  : {len([1 for n in seguros if not n.startswith('post/')])}")
    print(f"    publicadas sob outro slug : {len(renomeados)}")
    for nome, destino in renomeados:
        print(f"      {nome}")
        print(f"        -> {destino}")
    print(f"  PRESERVAR                   : {len(preservados)}")
    for nome, motivo in preservados:
        print(f"      {nome}")
        print(f"        {motivo[:100]}")
    print()
    if not preservados:
        print("  Nenhuma branch guarda trabalho unico: todas as 40 podem ir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
