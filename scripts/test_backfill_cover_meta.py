import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("backfill_cover_meta", Path(__file__).with_name("backfill-cover-meta.py"))
backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(backfill)


class BackfillCoverMetaTests(unittest.TestCase):
    def make_workspace(self, posts):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "posts").mkdir()
        (root / "posts" / "_meta.json").write_text(json.dumps({"posts": posts}), encoding="utf-8")
        return root

    def test_dry_run_does_not_write(self):
        root = self.make_workspace([{"slug": "legacy", "cover": "https://example.com/legacy.jpg"}])
        result = backfill.backfill_meta(root)
        self.assertEqual(result["updated"], ["legacy"])
        document = json.loads((root / "posts" / "_meta.json").read_text())
        self.assertNotIn("cover_meta", document["posts"][0])

    def test_apply_adds_explicit_legacy_state_and_backup(self):
        root = self.make_workspace([{"slug": "legacy", "cover": "https://example.com/legacy.jpg"}])
        result = backfill.backfill_meta(root, apply=True)
        self.assertTrue(result["applied"])
        self.assertTrue(Path(result["backup"]).exists())
        document = json.loads((root / "posts" / "_meta.json").read_text())
        meta = document["posts"][0]["cover_meta"]
        self.assertEqual(meta["strategy"], "legacy")
        self.assertEqual(meta["review_status"], "unreviewed")
        self.assertEqual(meta["source"], "historical")

    def test_second_apply_is_idempotent(self):
        root = self.make_workspace([{"slug": "legacy", "cover": "https://example.com/legacy.jpg"}])
        backfill.backfill_meta(root, apply=True)
        result = backfill.backfill_meta(root, apply=True)
        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"], ["legacy"])

    def test_existing_meta_is_preserved(self):
        existing = {"strategy": "fallback", "review_status": "auto_fallback"}
        root = self.make_workspace([{"slug": "current", "cover": "https://example.com/current.jpg", "cover_meta": existing}])
        result = backfill.backfill_meta(root, apply=True)
        self.assertEqual(result["skipped"], ["current"])
        document = json.loads((root / "posts" / "_meta.json").read_text())
        self.assertEqual(document["posts"][0]["cover_meta"], existing)


if __name__ == "__main__":
    unittest.main()
