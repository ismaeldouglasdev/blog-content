import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

_spec = importlib.util.spec_from_file_location("verify_covers", Path(__file__).with_name("verify-covers.py"))
verify_covers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_covers)


def make_cover(path: Path, color=(20, 70, 110)):
    image = Image.new("RGB", (1200, 630), color)
    draw = ImageDraw.Draw(image)
    for x in range(0, 1200, 40):
        draw.line((x, 0, x, 630), fill=(x % 255, 90, 150), width=2)
    for y in range(0, 630, 40):
        draw.line((0, y, 1200, y), fill=(30, y % 255, 160), width=2)
    image.save(path, "JPEG", quality=90)


class VerifyCoversTests(unittest.TestCase):
    def workspace(self, posts, assets=("post.jpg",)):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        covers = root / "posts" / "covers"
        covers.mkdir(parents=True)
        for name in assets:
            make_cover(covers / name)
        (root / "posts" / "_meta.json").write_text(json.dumps({"posts": posts}), encoding="utf-8")
        return root

    def test_valid_legacy_cover_warns_only(self):
        root = self.workspace([{
            "slug": "post",
            "cover": "https://example.com/post.jpg",
        }])
        report = verify_covers.verify_workspace(root)
        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["legacy"], 1)

    def test_low_photo_score_blocks(self):
        root = self.workspace([{
            "slug": "post",
            "cover": "https://example.com/post.jpg",
            "cover_meta": {"strategy": "photo", "relevance_score": 0.2, "review_status": "approved"},
            "cover_credit": {"license": "CC BY 4.0"},
        }])
        report = verify_covers.verify_workspace(root)
        self.assertFalse(report["ok"])
        self.assertIn("photo_score_low", {item["code"] for item in report["findings"]})

    def test_missing_asset_blocks(self):
        root = self.workspace([{
            "slug": "post",
            "cover": "https://example.com/missing.jpg",
        }], assets=())
        report = verify_covers.verify_workspace(root)
        self.assertIn("asset_missing", {item["code"] for item in report["findings"]})

    def test_translation_pair_is_not_duplicate(self):
        root = self.workspace([
            {"slug": "post", "cover": "https://example.com/post.jpg"},
            {"slug": "post-en", "cover": "https://example.com/post.jpg"},
        ])
        report = verify_covers.verify_workspace(root)
        self.assertNotIn("duplicate_cover", {item["code"] for item in report["findings"]})

    def test_real_duplicate_cover_warns(self):
        root = self.workspace([
            {"slug": "post-a", "cover": "https://example.com/post.jpg"},
            {"slug": "post-b", "cover": "https://example.com/post.jpg"},
        ])
        report = verify_covers.verify_workspace(root)
        self.assertIn("duplicate_cover", {item["code"] for item in report["findings"]})

    def test_cli_json_output(self):
        root = self.workspace([{"slug": "post", "cover": "https://example.com/post.jpg"}])
        self.assertEqual(verify_covers.main([str(root), "--format", "json", "--fail-on", "never"]), 0)

    def test_cli_error_exit_code(self):
        root = self.workspace([{"slug": "post", "cover": "https://example.com/missing.jpg"}], assets=())
        self.assertEqual(verify_covers.main([str(root), "--format", "json", "--fail-on", "error"]), 1)


if __name__ == "__main__":
    unittest.main()
