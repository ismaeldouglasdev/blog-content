#!/usr/bin/env python3
"""Deteca palavras portuguesas escritas sem diacriticos nos posts pt-BR.

O pipeline ja vazou encoding quebrado para posts publicados (travessao virando
"a\\x80\\x94", acentos virando "A\\xc2\\xa9").Este script pega o outro lado do
mesmo problema: texto escrito sem o acento.

A ideia NAO e um dicionario curado à mao -- listas desse tipo carregam falso
positivo ("suporte", "acesso", "processo" nao levam acento). Em vez disso o
proprio corpus define o vocabulario: se o blog escreve "interacao" acentuada em
um post, entao "interacao" sem acento em outro e bug. Palavras que o blog
nunca acentua nao sao julgadas.

Uso:  python3 scripts/audit-pt-diacritics.py [--fix]
"""
import glob
import os
import re
import sys
import unicodedata
from collections import defaultdict

# Palavras que nao seguem a regra acima: Tokens de codigo, siglas, marcas e
# nomes proprios que aparecem acentuados por acaso.
NEVER_FLAG = {
    "e", "a", "o", "as", "os", "um", "uma", "uns", "umas", "no", "na", "nos",
    "nas", "por", "para", "com", "sem", "de", "da", "do", "das", "dos",
    "que", "se", "nao", "sim", "mais", "menos", "muito", "pouco", "quando",
    "onde", "porque", "porem", "entao", "ja", "ate", "apos", "sobre",
    "entre", "desde", "ate", "cada", "todo", "toda", "todos", "todas",
    "este", "esta", "estes", "estas", "esse", "essa", "aquele", "aquela",
    "isso", "isto", "aquilo", "meu", "minha", "seu", "sua", "meus", "minhas",
    "seus", "suas", "nos", "voce", "voces", "ele", "ela", "eles", "elas",
    "eu", "tu", "nos", "vos", "lhe", "lhes", "la", "lo", "ai", "aqui",
    "la", "ali", "entao", "logo", "entao", "bem", "mal", "quase", "sempre",
    "nunca", "jamais", "agora", "hoje", "ontem", "amanha", "vez", "vezes",
    "ano", "anos", "dia", "dias", "hora", "horas", "vez", "tempo", "parte",
    "partes", "resto", "meio", "terco", "lugar", "coisa", "caso", "casos",
    "modo", "forma", "formas", "maneira", "jeito", "fato", "fatos",
    "lei", "leis", "nome", "nomes", "vez", "passo", "passos", "erro", "erros",
    "problema", "problemas", "ideia", "ideias", "ponto", "pontos", "linha",
    "linhas", "palavra", "palavras", "letra", "letras", "numero", "numeros",
    "vez", "ordem", "tipo", "tipos", "forma", "grupo", "grupos", "sistema",
    "sistemas", "projeto", "projetos", "versao", "versoes",
    # Palavras que NAO levam acento em pt-BR (falso positivo se entrarem aqui
    # por engano, o corpus acusaria a si mesmo).
    "prazo", "escopo", "suporte", "acesso", "processo", "conceito", "categoria",
    "desempenho", "automaticamente", "necessariamente", "posicionamento",
    "navegacao",  # so aparece em codigo; aqui para nao poluir o self-test
    # Formas verbais ambiguas: a variante acentuada existe no portugues para
    # outra funcao gramatical (plural, substantivo, gerundio), nao como erro.
    # "tem"(verbo) x "têm"(plural) | "usa" x "usá" | "continua" x "contínua" |
    # "evita" x "evitá" | "compara" x "compará" | "verifica" x "verificá".
    "tem", "usam", "evita", "evitam", "vem", "verifica", "verificam",
    "salva", "salvam", "compara", "comparam", "continua", "continuam",
    "escreve", "escrevem", "estabiliza", "estabilizam", "precisa",
    "precisam", "muda", "mudam", "falta", "faltam", "existe", "existem",
    "funciona", "funcionam", "depende", "dependem", "acontece", "acontecem",
    "significa", "significam", "representa", "representam", "permite",
    "permitem", "oferece", "oferecem", "gera", "geram", "usa", "usa",
}

# Siglas e marcas常 aparecem em CAIXA ALTA; ignoramos token todo maiusculo.
CODE_HINT = re.compile(r"^[A-Z]{2,}$")


def strip_accents(word: str) -> str:
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _blank(match: "re.Match") -> str:
    """Substitui o trecho por um '\n' por linha, para o numero da linha
    continuar batendo com o arquivo original depois do strip."""
    return "\n" * match.group(0).count("\n")


def strip_code(text: str) -> str:
    """Remove codigo preservando a contagem de linhas.

    Cercas, bloco indentado, codigo inline, HTML e URLs sao apagados, mas cada
    linha consumida vira uma linha vazia -- senao o numero de linha reportado
    nao corresponde ao arquivo e da para "consertar" a linha errada.
    """
    text = re.sub(r"```.*?```", _blank, text, flags=re.S)          # cercas
    text = re.sub(r"~~~.*?~~~", _blank, text, flags=re.S)
    text = re.sub(r"^(?:[ ]{4}|\t).*$", "", text, flags=re.M)        # indentado
    text = re.sub(r"`[^`]*`", _blank, text)                          # inline
    text = re.sub(r"https?://\S+", _blank, text)                     # URLs
    text = re.sub(r"<[^>]+>", _blank, text)                          # HTML
    return text


def read_body(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    raw = re.sub(r"^---\n.*?\n---\n", "\n", raw, count=1, flags=re.S)
    return strip_code(raw)


def build_vocabulary(paths: list) -> dict:
    """Mapeia forma acentuada -> forma sem acento, so do que o corpus usa."""
    vocab = defaultdict(set)
    for path in paths:
        for word in re.findall(r"[A-Za-zÀ-ÿ]+", read_body(path)):
            if CODE_HINT.match(word):
                continue
            low = word.lower()
            if low in NEVER_FLAG:
                continue
            if strip_accents(low) != low:
                vocab[strip_accents(low)].add(low)
    return vocab


def main() -> int:
    fix = "--fix" in sys.argv
    posts = sorted(
        p for p in glob.glob("posts/2026-*.md") if not p.endswith("-en.md")
    )
    vocab = build_vocabulary(posts)
    # so interessa se a forma acentuada for de fato diferente da base
    vocab = {b: a for b, a in vocab.items() if b not in a}

    total = 0
    affected = 0
    per_file = {}
    for path in posts:
        hits = []
        for lineno, line in enumerate(read_body(path).splitlines(), 1):
            for word in re.findall(r"[A-Za-zÀ-ÿ]+", line):
                low = word.lower()
                if CODE_HINT.match(word) or low in NEVER_FLAG:
                    continue
                base = strip_accents(low)
                # `word == base` = a palavra foi escrita SEM acento.
                # `base in vocab` = o corpus usa a variante acentuada em outro
                # post. As duas juntas = diacritico perdido.
                if word == base and base in vocab:
                    hits.append((lineno, word, sorted(vocab[base])))
        if hits:
            per_file[path] = hits

    for path, hits in sorted(per_file.items()):
        affected += 1
        print(f"\n### {os.path.basename(path)}")
        seen = set()
        for lineno, word, correct in hits:
            key = (word, tuple(correct))
            if key in seen:
                continue
            seen.add(key)
            print(f"  L{lineno:<5} {word:<20} -> {', '.join(correct)}")
        total += len(seen)

    print(f"\n{'=' * 62}")
    print(f"ARQUIVOS COM PALAVRA SEM ACENTO: {affected}/{len(posts)}")
    print(f"OCORRENCIAS DISTINTAS: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
