"""Font-source preference and Steam-style fallback regression tests."""
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "tools"))

from mwad import font_sources
import prepare_ui


class FontSourceTests(unittest.TestCase):
    def fixture(self, root, *, ttf=False):
        data = root / "Data Files"
        data.mkdir()
        (data / "Morrowind.esm").write_bytes(b"fixture")
        (data / "Morrowind.bsa").write_bytes(b"fixture")
        fonts = data / "Fonts"
        fonts.mkdir()
        for spec in font_sources.FAMILIES.values():
            (fonts / spec["bitmap"]).write_bytes(b"fnt")
            (fonts / spec["atlas"]).write_bytes(b"tex")
        if ttf:
            book = data / "BookArt"
            book.mkdir()
            for name in font_sources.PREFERRED_TTFS:
                (book / name).write_bytes(b"ttf")
        return data

    def test_steam_style_tree_uses_bitmap_fallback_and_warns(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.fixture(Path(temp), ttf=False)
            fonts = font_sources.discover(data)
            self.assertEqual(font_sources.source_mode(fonts["magic"]), "bitmap")
            self.assertTrue(all(item["bitmap_ready"] for item in fonts.values()))
            warnings = "\n".join(font_sources.fallback_warnings(fonts))
            self.assertIn("Steam GOTY", warnings)
            self.assertIn("GOG GOTY", warnings)
            self.assertIn(font_sources.GOG_GOTY_URL, warnings)
            self.assertIn("may be inferior", warnings)

    def test_gog_style_tree_prefers_all_loose_ttfs(self):
        with tempfile.TemporaryDirectory() as temp:
            data = self.fixture(Path(temp), ttf=True)
            fonts = font_sources.discover(data)
            inventory = font_sources.preferred_ttf_inventory(fonts)
            self.assertEqual(set(inventory), set(font_sources.PREFERRED_TTFS))
            self.assertTrue(all(inventory.values()))
            self.assertEqual(font_sources.fallback_warnings(fonts), [])
            self.assertTrue(all(font_sources.source_mode(item) == "ttf" for item in fonts.values()))

    def test_unrepresentable_ttf_falls_back_to_complete_bitmap_family(self):
        item = {
            "label": "Daedric", "ttf_path": Path("daedric_runes.ttf"),
            "bitmap_path": Path("daedric_font.fnt"), "bitmap_ready": True,
        }
        with patch.object(prepare_ui, "pack_truetype", side_effect=ValueError("Glyph exceeds native limits")), \
             patch.object(prepare_ui, "pack_font", return_value=b"bitmap") as bitmap:
            payloads, mode, reason = prepare_ui.bake_family(item)
        self.assertEqual(mode, "bitmap-fallback")
        self.assertIn("Glyph exceeds native limits", reason)
        self.assertEqual(set(payloads), {12, 14, 16})
        self.assertEqual(bitmap.call_count, 3)


if __name__ == "__main__":
    unittest.main()
