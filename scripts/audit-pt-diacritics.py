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

Antes de 2026-10-04 este script imprimia o relatorio e devolvia sempre 0, o que
o tornava decorativo: a CI mostrava 102 ocorrencias no post de nginx e passava.
`main()` agora devolve 1 quando ha violacoes, que e o que o torna gate.

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
    # Verbo x adjectivo com a mesma grafia: a forma acentuada existe no
    # portugues, mas como outra categoria. "valida"(verbo, "voce valida") x
    # "válida"(adjectivo, "sequência válida"). Sem estas, o corpus ensina o
    # mapeamento e o --fix escreve "voce válida a forma".
    "valida", "validam", "aplica", "aplicam", "torna", "tornam",
    "coloca", "colocam", "registra", "registram", "grava", "gravam",
}

# Siglas e marcas aparecem em CAIXA ALTA; ignoramos token todo maiusculo.
CODE_HINT = re.compile(r"^[A-Z]{2,}$")

# Verbo + pronome enclitico. O enclitico desloca a silaba tonica para a ultima
# silaba do verbo, e o acento passa a ser obrigatorio: "torna-se" escreve-se
# "torná-se". Estas construcoes nao entram no vocabulario (ver build_vocabulary).
ENCLITIC = re.compile(
    r"[A-Za-zÀ-ÿ]+-(?:se|lo|la|los|las|nos|na|me|te|lhe|lhes|vos|os|as|num|uma)\b"
)


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
    # O frontmatter vira uma linha em branco por linha: o numero de linha
    # reportado tem de bater com o arquivo, senao "conserta" a linha errada.
    raw = re.sub(r"^---\n.*?\n---\n",
                 lambda m: "\n" * m.group(0).count("\n"),
                 raw, count=1, flags=re.S)
    return strip_code(raw)


def build_vocabulary(paths: list) -> dict:
    """Mapeia forma acentuada -> forma sem acento, so do que o corpus usa."""
    vocab = defaultdict(set)
    for path in paths:
        # As construcoes com enclitico saem antes de tokenizar. La o acento do
        # verbo e gramatical e obrigatorio ("torna-se" mas "torná-se"), porque o
        # verbo deixa de ter a ultima silaba tonica. Sem esta remocao o corpus
        # ensina "torna -> torná", e o --fix passa a escrever `torná` tambem
        # onde o verbo esta solto -- que e como 12 verbs foram partidos num post.
        # `re.sub` com " " mantem a contagem de linhas, como read_body.
        text = ENCLITIC.sub(" ", read_body(path))
        for word in re.findall(r"[A-Za-zÀ-ÿ]+", text):
            if CODE_HINT.match(word):
                continue
            low = word.lower()
            # NEVER_FLAG e consultado nas duas formas. As entradas da lista sao
            # as nao acentuadas ("verifica", "torna") mas o token do corpus e o
            # acentuado ("verificá", "torná"), e comparar so `low` deixava o
            # mapeamento ser aprendido na mesma -- o filtro so funcionava na
            # deteccao, nao no `--fix`. Sem isto o auditor escrevia "você válida".
            if low in NEVER_FLAG or strip_accents(low) in NEVER_FLAG:
                continue
            if strip_accents(low) != low:
                vocab[strip_accents(low)].add(low)
    return vocab


def apply_fix(path: str, hits: list) -> tuple:
    """Reescreve so as linhas onde `read_body` encontrou a palavra.

    `read_body` substitui codigo e frontmatter por linhas em branco, com a mesma
    contagem. Por isso os numeros que ela devolve batem com o ficheiro original e
    da para corrigir apenas essas linhas. Escrever o `read_body` de volta
    apagaria o codigo e o frontmatter, por isso nunca se faz.

    Inline code e' preservado: `--cluster-replicas 0` e um comando, e acento
    nuns quebra. `read_body` mascara inline code com espacos, o que nao chega
    porque o correcto e nao tocar na linha.

    Base com mais de uma forma acentuada no corpus fica por corrigir: `replica`
    tanto pode dar `réplica` como `réplicas`, e escolher a primeira
    alfabeticamente transformou `os replicas` em `os replica`. Adivinhar flexao e
    pior que nao corrigir.
    """
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    before = len(lines)

    by_line = defaultdict(dict)
    ambiguous = set()
    for lineno, word, correct in hits:
        if len(correct) > 1:
            ambiguous.add((lineno, word, tuple(correct)))
            continue
        by_line[lineno][word.lower()] = correct[0]

    changed = 0
    for lineno, forms in by_line.items():
        if not 1 <= lineno <= len(lines):
            continue
        original = lines[lineno - 1]
        # Mascara o inline code para o swap nao lhe tocar, e restaura depois.
        spans = []

        def hide(m):
            spans.append(m.group(0))
            return "\x00" * len(m.group(0))

        masked = re.sub(r"`[^`]*`", hide, original)

        def swap(m, forms=forms):
            low = m.group(0).lower()
            if low not in forms:
                return m.group(0)
            rep = forms[low]
            return rep.capitalize() if m.group(0)[:1].isupper() else rep

        fixed = re.sub(r"[A-Za-zÀ-ÿ]+", swap, masked)
        if fixed != original:
            for original_span in spans:
                fixed = fixed.replace("\x00" * len(original_span), original_span, 1)
            assert "\x00" not in fixed, f"{path}: inline code nao restaurado"
            lines[lineno - 1] = fixed
            changed += 1

    assert len(lines) == before, f"{path}: contagem de linhas mudou"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return changed, sorted(ambiguous)


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
                # `low == base` = a palavra foi escrita SEM acento. A comparacao
                # e com `low` e nao com `word`: `word` guarda a maiuscula, e
                # `Configuracao != configuracao` fazia com que palavra no inicio
                # de frase nunca fosse detectada.
                # `base in vocab` = o corpus usa a variante acentuada em outro
                # post. As duas juntas = diacritico perdido.
                if low == base and base in vocab:
                    hits.append((lineno, word, sorted(vocab[base])))
        if hits:
            per_file[path] = hits

    if fix and per_file:
        total_lines = 0
        skipped = []
        for path, hits in sorted(per_file.items()):
            changed, ambiguous = apply_fix(path, hits)
            total_lines += changed
            skipped.extend((os.path.basename(path), *a) for a in ambiguous)
        print(f"--fix: {total_lines} linha(s) reescrita(s) em {len(per_file)} post(s)")
        if skipped:
            print(f"\n{len(skipped)} caso(s) ambiguo(s) NAO corrigidos:")
            for name, lineno, word, correct in skipped:
                print(f"  {name} L{lineno}: {word} -> {' ou '.join(correct)}")
        return 0

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
    if affected:
        print(f"FALHA: {total} palavra(s) sem acento em {affected} post(s).")
        return 1
    print("OK: nenhum diacritico perdido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
