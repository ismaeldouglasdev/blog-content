import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "audit_pt_diacritics", Path(__file__).with_name("audit-pt-diacritics.py")
)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

FM = "---\ntitle: t\ndate: 2026-01-01\nlang: pt\n---\n\n"


class Corpus:
    """Corpus temporario. O vocabulario do audit deriva dos posts, por isso um
    fixture so com a forma sem acento nao produz deteccao nenhuma: e preciso
    a variante acentuada em algum post para o mapeamento existir."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "posts").mkdir()
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def add(self, day, body):
        name = f"2026-01-{day:02d}-p.md"
        (self.root / "posts" / name).write_text(FM + body + "\n", encoding="utf-8")
        return self.root / "posts" / name

    def run(self):
        cwd = Path.cwd()
        os.chdir(self.root)
        try:
            return audit.main()
        finally:
            os.chdir(cwd)


class ExitCodeTests(unittest.TestCase):
    def test_clean_corpus_passes(self):
        with Corpus() as c:
            c.add(1, "Configuração e boas.")
            self.assertEqual(c.run(), 0)

    def test_missing_diacritic_fails(self):
        with Corpus() as c:
            c.add(1, "A configuração inicial.")
            c.add(2, "A configuracao inicial.")
            self.assertEqual(c.run(), 1)

    def test_capitalised_word_is_detected(self):
        """Regressao: o check comparava `word` (com maiuscula) com `base`, e
        `Configuracao != configuracao`, entao inicio de frase escapava."""
        with Corpus() as c:
            c.add(1, "configuração inicial")
            c.add(2, "Configuracao inicial")
            self.assertEqual(c.run(), 1)

    def test_word_never_accented_is_not_judged(self):
        with Corpus() as c:
            c.add(1, "Processo e acesso são duas palavras.")
            self.assertEqual(c.run(), 0)

    def test_enclitic_accent_is_not_a_missing_diacritic(self):
        """Regressao: com pronome enclitico o acento do verbo passa a ser
        gramatical ("torná-se"), nao um diacritico perdido. Sem esta regra o
        corpus ensinava "torna -> torná" e o `torna` solto passava a ser
        julgado -- o --fix escrevia `torná` onde o verbo nao leva acento."""
        with Corpus() as c:
            c.add(1, "No desktop, torná-se horizontal.")
            c.add(2, "Isso torna mais fácil a migração.")
            self.assertEqual(c.run(), 0)

    def test_verb_homograph_of_adjective_is_not_judged(self):
        """Regressao: `válida` (adjectivo) e `valida` (verbo) so diferem no
        acento. O corpus ensinava o mapeamento e o --fix escrevia
        "voce válida a forma", que nao e portugues."""
        with Corpus() as c:
            c.add(1, "A sequência válida tem 121 combinações.")
            c.add(2, "Você valida a forma sempre.")
            self.assertEqual(c.run(), 0)

    def test_non_breaking_hyphen_enclitic_is_also_excluded(self):
        """Regressao: `aciona-la` do corpus esta escrito com U+2011, nao com
        `-`. O ENCLITIC so casava `-` ASCII, e o verbo nao esta em NEVER_FLAG,
        por isso a construcao poluia o vocabulario e o `aciona` solto passava a
        ser julgado -- o --fix escrevia `acioná` onde o verbo nao leva acento."""
        with Corpus() as c:
            c.add(1, "A fun\u00e7\u00e3o acion\u00e1\u2011la no final do pedido.")
            c.add(2, "Isso aciona um evento antes de responder.")
            self.assertEqual(c.run(), 0)


class ApplyFixTests(unittest.TestCase):
    def build(self, *bodies):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        (root / "posts").mkdir()
        paths = []
        for i, body in enumerate(bodies, 1):
            p = root / "posts" / f"2026-01-{i:02d}-p.md"
            p.write_text(FM + body + "\n", encoding="utf-8")
            paths.append(p)
        return paths

    def fix(self, paths, target):
        vocab = audit.build_vocabulary([str(p) for p in paths])
        vocab = {b: a for b, a in vocab.items() if b not in a}
        hits = []
        for lineno, line in enumerate(audit.read_body(str(target)).splitlines(), 1):
            for word in audit.re.findall(r"[A-Za-zÀ-ÿ]+", line):
                low = word.lower()
                base = audit.strip_accents(low)
                if audit.CODE_HINT.match(word) or low in audit.NEVER_FLAG:
                    continue
                if low == base and base in vocab:
                    hits.append((lineno, word, sorted(vocab[base])))
        return audit.apply_fix(str(target), hits)

    def test_inline_code_is_not_touched(self):
        paths = self.build(
            "A configuração do servidor.",
            "Use `--cluster-replicas 0` na configuracao.",
        )
        self.fix(paths, paths[1])
        out = paths[1].read_text(encoding="utf-8")
        self.assertIn("`--cluster-replicas 0`", out)
        self.assertIn("configuração", out)

    def test_unambiguous_words_are_fixed(self):
        paths = self.build(
            "A equação e as equações do modelo.",
            "Outra equacao com equacoes no texto.",
        )
        self.fix(paths, paths[1])
        out = paths[1].read_text(encoding="utf-8")
        self.assertIn("equação", out)
        self.assertIn("equações", out)
        self.assertNotIn("equacao", out)

    def test_ambiguous_base_is_left_alone(self):
        """`mantem` mapeia para `mantem` E `mantem` no corpus real, e o sujeito
        decide qual. Adivinhar transformou `os replicas` em `os replica`, no
        singular. Ambiguo fica por corrigir e e reportado."""
        paths = self.build(
            "Ele mantém a conexão e elas mantêm as conexões.",
            "A aplicacao mantem conexoes persistentes.",
        )
        _, ambiguous = self.fix(paths, paths[1])
        body = paths[1].read_text(encoding="utf-8").split("---\n\n", 1)[1]
        self.assertIn("mantem", body)
        self.assertNotIn("mantém", body)
        self.assertNotIn("mantêm", body)
        self.assertTrue(any(w == "mantem" for _, w, _ in ambiguous), ambiguous)

    def test_unambiguous_plural_is_fixed(self):
        """`replicas` tem base propria, logo nao e ambiguo com `replica`."""
        paths = self.build(
            "Uma réplica e duas réplicas no texto.",
            "Uma replica e os replicas do cluster.",
        )
        self.fix(paths, paths[1])
        body = paths[1].read_text(encoding="utf-8").split("---\n\n", 1)[1]
        self.assertIn("réplica", body)
        self.assertIn("réplicas", body)

    def test_line_count_preserved(self):
        paths = self.build(
            "A configuração do servidor.\n\nMais configuracao aqui.\n",
        )
        before = paths[0].read_text(encoding="utf-8").count("\n")
        self.fix(paths, paths[0])
        self.assertEqual(paths[0].read_text(encoding="utf-8").count("\n"), before)


if __name__ == "__main__":
    unittest.main()
