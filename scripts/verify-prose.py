#!/usr/bin/env python3
"""Verificador de prosa 'sem AI slop' para os posts do blog.

Why: o CI so validava metadata, estrutura, encoding e diacriticos. Nada
impedia um post gerado por IA de ser mergeado com os tic's tipicos de LLM
("vale a pena notar", hedging empilhado, "vamos explorar", enumeracoes
forçadas). Este script fecha esse buraco.

Filosofia: nem todo registo formal e slop. "Nao e X, e Y" numa frase
factual e informacao; a mesma formula repetida como titulo de seccao e um
tique. Por isso severidade em dois niveis:

  ERROR  tic inequivoco, nunca passa. Faz o script sair != 0. Tambem entra a
         pontuacao reprovada (EM_DASH): nao e tic retorico, e illegalidade.
  WARN   registo que pode ser intencional. Conta, reporta, nao reprova.

Os ratios (TIC_FORMULA, TIC_TRIPLA) so disparam acima de N ocorrencias no
mesmo post: uma enumeracao de tres e normal em portugues, seis e estilo.

Ignora blocos de codigo e frontmatter: `Math.random()` nao e gerador
criptografico e um facto, nao umaformula retorica.

Read-only: nao escreve nada, nao precisa da rede, so stdlib.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
URL_IN_LINK = re.compile(r"\[([^\]]*)\]\((?:https?://[^)\s]*)\)")
BARE_URL = re.compile(r"https?://\S+")


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    severity: str  # "ERROR" | "WARN"
    why: str
    # limiar para regras de ratio; None = contar cada ocorrencia
    max_occurrences: int | None = None


# --------------------------------------------------------------------------
# ERROR: tics que nao tem razao de sobreviver num post tecnico
# --------------------------------------------------------------------------
ERROR_RULES: list[Rule] = [
    # Zero tolerancia por decisao do dono. O lookahead preserva o unico uso
    # legitimo de en dash no corpus, o intervalo "2020-2024".
    Rule(
        "EM_DASH",
        re.compile(r"—|–(?!\s*\d)"),
        "ERROR",
        "travessao: nao e pontuacao PT-BR e e marcador citado de prosa gerada",
    ),
    Rule(
        "CLICHE_NOTAR",
        re.compile(
            r"\b(?:vale a pena (?:notar|lembrar|destacar|mencionar)"
            r"|e importante (?:notar|lembrar|destacar|ressaltar)"
            r"|nao podemos deixar de"
            r"|nunca e demais (?:lembrar|reforcar)"
            r"|como ja dissemos"
            r"|frisando)\b",
            re.I,
        ),
        "ERROR",
        "transicao clichet que um LLM emite por defeito e que nao acrescenta nada",
    ),
    Rule(
        "META_SELF_REF",
        re.compile(
            r"\b(?:vamos (?:explorar|mergulhar|viajar|analisar|explorar)"
            r"|prepare-se para"
            r"|neste post (?:vamos|iremos|veremos)"
            r"|este artigo (?:vai|mostra) (?:mostrar|examinar|explorar)"
            r"|vamos dividir (?:isto|este)"
            r"|sem mais delongas)\b",
            re.I,
        ),
        "ERROR",
        "meta-comentario sobre o proprio texto em vez de sobre o assunto",
    ),
    Rule(
        "IMPERRATIVO_DICA",
        re.compile(
            r"(?m)^\s*[-*]\s*(?:Certifique-se|Lembre-se|Experimente|Veja|Tente|Nao esqueça)\b",
            re.I,
        ),
        "ERROR",
        "imperativo de dica: o post deixa de informar e passa a dar ordens",
    ),
    Rule(
        "FECHO_CONVERSACIONAL",
        re.compile(
            r"(?mi)^\s*(?:espero que (?:este|esse) (?:post|artigo|texto)"
            r"|ate (?:a proxima|o proximo|nos vermos)"
            r"|seja bem-vindo|comente abaixo"
            r"|se voce chegou ate aqui)\b",
        ),
        "ERROR",
        "fecho de conversa que nao pertence a um post, e sinal de geracao",
    ),
    Rule(
        "CLICHE_MUNDO",
        re.compile(
            r"\b(?:no mundo (?:atual|moderno|digital|de hoje)"
            r"|nos dias (?:atuais|modernos)"
            r"|em um mundo (?:onde|em que) (?:tudo|mudancas) )",
            re.I,
        ),
        "ERROR",
        "abertura de escenario generico: nao existe 'no mundo atual'",
    ),
    Rule(
        "TIC_INGLES_PT",
        re.compile(
            r"\b(?:vamos (?:dive|deep dive)|deep dive|brainstorm|consequential"
            r"|overview|in-depth|state-of-the-art)\b",
            re.I,
        ),
        "ERROR",
        "anglicismo de prosa que um escritor PT traduziria (commit, workflow e "
        "payload sao termos de dominio e ficam de fora de proposito)",
    ),
]

# --------------------------------------------------------------------------
# WARN: registo a vigiar, conta mas nao reprova sozinho
# --------------------------------------------------------------------------
WARN_RULES: list[Rule] = [
    Rule(
        "HEDGING",
        re.compile(r"\b(?:pode ser que|pode (?:ser|ajudar|valer|acontecer)"
                   r"|e poss[ií]vel que|talvez seja|em geral,? (?:costuma|é) )", re.I),
        "WARN",
        "hedging empilhado dilui afirmacoes; 3+ no mesmo post e estilo",
        max_occurrences=3,
    ),
    Rule(
        "SUPERLATIVO",
        re.compile(r"\b(?:incr[ií]vel|fant[aá]stico|revolucion[aá]rio|surpreendente"
                   r"|extremamente|altamente|incrivelmente"
                   r"|(?:e|é) (?:essencial|fundamental|crucial|indispensavel))\b", re.I),
        "WARN",
        "superlativo vazio; um ou dois sao opiniao, varios sao propaganda",
        max_occurrences=2,
    ),
    Rule(
        "FECHO_RESUMO",
        re.compile(r"(?m)^#{2,3}\s+(?:O\s+)?(?:Resumo|Conclus[õo]es?)\s*$", re.I),
        "WARN",
        "fecho previsivel; um resumo que repete o texto nao e resumo",
    ),
    # ratios: so conta acima do limiar
    Rule(
        "TIC_FORMULA",
        # O separador e `(?:,|—|–)`, nao so a virgula: com a virgula isolada a
        # regra escapava a mesmaformula escrita com travessao. Medido, nao suposto.
        re.compile(r"n[ãa]o (?:é|e) [^.\n]{1,40}(?:,|—|–)\s*(?:é|e)\s", re.I),
        "WARN",
        "formula 'nao e X, e Y': informativa uma vez, tique repetida",
        max_occurrences=2,
    ),
    Rule(
        "TIC_TRIPLA",
        re.compile(r"\b\w+,\s+\w+\s+e\s+\w+\b"),
        "WARN",
        "enumeracao de tres em serie: normal uma vez, estilo se repete",
        max_occurrences=5,
    ),
]

ALL_RULES = ERROR_RULES + WARN_RULES

# Nomes proprios de features que coincidem com anglicismos da lista. "CSS
# Overview" e o painel do Chrome DevTools; reprovar seria exigir que um post
# de devtools renomeasse uma feature existente.
ALLOW_PROPER_NOUNS = re.compile(
    r"\bCSS Overview\b", re.I
)


def strip_noise(raw: str) -> str:
    """Remove frontmatter, blocos e codigo inline e o titulo H1."""
    body = FRONTMATTER.sub("", raw)
    body = CODE_FENCE.sub("", body)
    body = INLINE_CODE.sub(" ", body)
    body = URL_IN_LINK.sub(r"[\1]", body)
    body = BARE_URL.sub(" ", body)
    return body


def audit(path: Path) -> tuple[list[str], list[str], int]:
    """Devolve (erros, avisos, n_linhas) para um post."""
    raw = path.read_text(encoding="utf-8")
    body = strip_noise(raw)
    # Allowlist de nomes proprios: "CSS Overview" e o painel do Chrome
    # DevTools. Reprovar exigiria que um post de devtools renomeasse uma
    # feature existente. Sem este comentario a lista parece arbitraria.
    body = ALLOW_PROPER_NOUNS.sub(" ", body)
    # `TIC_INGLES_PT` reprova anglicismos num post PT; num ficheiro -en seria
    # falso positivo por construcao. Sem este filtro, o `is_en` parece
    # defensivo redundante e uma "simplificacao" reintroduz o bug.
    is_en = path.stem.endswith("-en")
    rules = [r for r in ALL_RULES if not (is_en and r.name == "TIC_INGLES_PT")]
    # titulo de seccao conta como prosa: e onde o tique aparece
    errors: list[str] = []
    warns: list[str] = []
    for rule in rules:
        hits = list(rule.pattern.finditer(body))
        if not hits:
            continue
        line = raw[: hits[0].start()].count("\n") + 1
        excerpt = body[max(0, hits[0].start() - 40) : hits[0].end() + 40]
        excerpt = " ".join(excerpt.split())
        msg = (
            f"L{line}  {rule.name} (x{len(hits)})  {rule.why}\n"
            f"        … {excerpt[:150]} …"
        )
        if rule.max_occurrences is not None:
            if len(hits) > rule.max_occurrences:
                (warns if rule.severity == "WARN" else errors).append(
                    f"{msg}\n        (limiar {rule.max_occurrences}, "
                    f"total {len(hits)})"
                )
        else:
            (errors if rule.severity == "ERROR" else warns).append(msg)
    return errors, warns, len(body.splitlines())


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica prosa sem AI slop")
    ap.add_argument("posts_dir", nargs="?", default="posts")
    ap.add_argument("--files", nargs="*", help="ficheiros especificos")
    ap.add_argument("--strict", action="store_true", help="fails tambem em WARN")
    ap.add_argument("--fail-on", choices=["error", "warning", "never"], default="error")
    ap.add_argument("--quiet", action="store_true", help="so o resumo")
    args = ap.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        # `verify-prose.py posts/2026-10-03-uuid.md` caia em "nenhum post
        # encontrado" (o glob de um ficheiro devolve vazio) e o post passava.
        target = Path(args.posts_dir)
        if target.is_file():
            paths = [target]
        else:
            paths = sorted(
                p for p in target.glob("*.md") if p.name[0].isdigit()
            )
    if not paths:
        print("nenhum post encontrado", file=sys.stderr)
        return 2

    n_err = n_warn = 0
    failing: list[str] = []
    for p in paths:
        try:
            errs, warns, _ = audit(p)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"ERRO ao ler {p}: {exc}", file=sys.stderr)
            return 2
        if errs or warns:
            failing.append(p.name)
            n_err += len(errs)
            n_warn += len(warns)
            if args.quiet:
                continue
            print(f"\n=== {p.name} ===")
            for e in errs:
                print(f"  [ERROR] {e}")
            for w in warns:
                print(f"  [WARN ] {w}")

    total = len(paths)
    print(f"\n{'-' * 60}")
    print(f"prosa: {total} post(s) | ERROR {n_err} | WARN {n_warn} | {len(failing)} com ocorrencias")
    if args.strict:
        print("modo --strict: WARN tambem reprova")
        if n_err or n_warn:
            print(f"FALHA: {len(failing)} post(s) com slop")
            return 1
        print("OK: nenhum tic encontrado")
        return 0
    if args.fail_on == "error" and n_err:
        print(f"FALHA: {n_err} erro(s) de tic -- corrige ou escreve --fail-on never")
        return 1
    if args.fail_on == "warning" and (n_err or n_warn):
        print(f"FALHA: {n_err} erro(s) + {n_warn} aviso(s)")
        return 1
    if n_err or n_warn:
        print(f"tics encontrados, mas --fail-on {args.fail_on} nao reprova")
        return 0
    print("OK: nenhum tic encontrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())