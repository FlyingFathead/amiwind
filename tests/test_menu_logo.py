# SPDX-License-Identifier: GPL-3.0-only
"""The menu logo is the gold name without a rule above it (UI-MENU-LOGO-32)."""
import colorsys
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from prepare_logo import MENU_LOGO_SIZE, gold_ramp, menu_logo_excluded, prepare_menu_logo  # noqa: E402
from sky_palette_overlay import BANK  # noqa: E402
from ui_palette import RESERVED  # noqa: E402

NAME = ROOT / 'resources/media/AmiWind_logo_name_only.png'
WORDMARK = ROOT / 'resources/media/AmiWind_wordmark.png'


def game_like_palette():
    """A 256-colour palette shaped like the converted game palette: pale golds
    and browns, the salmon and red status-bar colours in the reserved UI slots,
    and a bright saturated gold in a sky bank entry (repainted later)."""
    pal = [(i, i, i) for i in range(256)]
    for i in range(1, 120):  # greys, blues and greens of the world textures
        pal[i] = ((i * 37) % 120, 60 + (i * 53) % 140, 80 + (i * 29) % 170)
    golds = [(238, 221, 170), (191, 167, 136), (165, 130, 90), (148, 112, 73), (133, 106, 71),
             (119, 88, 55), (106, 81, 45), (96, 66, 34), (84, 62, 32), (66, 52, 31), (56, 45, 25),
             (42, 35, 18), (164, 149, 120), (122, 95, 68), (77, 70, 48)]
    for k, rgb in enumerate(golds):
        pal[2 + 7 * k] = rgb
    pal[0] = (0, 0, 0)
    reds = [(203, 129, 101), (214, 154, 123), (215, 168, 136), (187, 93, 68), (179, 76, 56),
            (148, 52, 41), (23, 7, 3), (5, 1, 1)]
    for k, i in enumerate(sorted(RESERVED)):
        pal[i] = reds[k % len(reds)]
    pal[140] = (255, 174, 66)  # sky bank: a tempting saturated gold
    pal[83] = (255, 232, 160)
    pal[255] = (0, 0, 0)
    assert 140 in BANK and 83 in BANK
    return bytes(c for rgb in pal for c in rgb)


def build(palette, source=NAME, **options):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / 'palette.lmp').write_bytes(palette)
        prepare_menu_logo(source, tmp / 'palette.lmp', tmp / 'amiwind.awi', **options)
        raw = (tmp / 'amiwind.awi').read_bytes()
    width, height = struct.unpack_from('<HH', raw, 4)
    return raw[:4], width, height, raw[8:]


def opaque_rows(pixels, background, width=200):
    rows = [pixels[y * width:(y + 1) * width] for y in range(len(pixels) // width)]
    return [y for y, row in enumerate(rows) if any(p != background for p in row)], rows


def longest_run(row, background):
    best = run = 0
    for p in row:
        run = run + 1 if p != background else 0
        best = max(best, run)
    return best


def rule_rows(pixels, background, width=200):
    """Rows where one unbroken run covers most of the width: a rule, never a letter row."""
    _, rows = opaque_rows(pixels, background, width)
    return [y for y, row in enumerate(rows) if longest_run(row, background) > width * 0.6]


class MenuLogoTests(unittest.TestCase):
    def setUp(self):
        self.palette = game_like_palette()
        self.ramp, self.black = gold_ramp(self.palette)

    def test_format_and_size_fit_the_menu_title_box(self):
        magic, width, height, pixels = build(self.palette)
        self.assertEqual((magic, width, height, len(pixels)), (b'AWI1', 200, 40, 8000))
        self.assertEqual(MENU_LOGO_SIZE, (200, 40))
        rows, _ = opaque_rows(pixels, self.black)
        self.assertTrue(rows)
        self.assertGreaterEqual(rows[0], 0)
        self.assertLess(rows[-1], 40)

    def test_no_rule_above_the_letters(self):
        _, _, _, pixels = build(self.palette)
        self.assertEqual(rule_rows(pixels, self.black), [])
        rows, all_rows = opaque_rows(pixels, self.black)
        # The top rows of the opaque area are letter tops (A, i dots, W, d), not a line.
        for y in rows[:3]:
            self.assertLess(longest_run(all_rows[y], self.black), 200 // 4, y)

    def test_detector_sees_the_old_rule_above(self):
        _, _, _, pixels = build(self.palette, source=WORDMARK, style='legacy')
        black = 0
        rules = rule_rows(pixels, black)
        rows, _ = opaque_rows(pixels, black)
        self.assertTrue(rules, 'legacy wordmark should show its rule')
        letters = [y for y in rows if y not in rules]
        self.assertLess(max(rules), min(letters))

    def test_optional_rule_is_below_the_letters(self):
        _, _, _, pixels = build(self.palette, rule='below')
        rules = rule_rows(pixels, self.black)
        self.assertEqual(len(rules), 1)
        rows, _ = opaque_rows(pixels, self.black)
        self.assertEqual(max(rows), rules[0])
        self.assertLess(rules[0], 40)
        with self.assertRaises(ValueError):
            build(self.palette, rule='above')

    def test_mean_hue_is_gold_not_red(self):
        _, _, _, pixels = build(self.palette)
        hues = [colorsys.rgb_to_hsv(*(c / 255 for c in self.palette[p * 3:p * 3 + 3]))[0] * 360
                for p in pixels if p != self.black]
        self.assertGreater(len(hues), 1000)
        mean = sum(hues) / len(hues)
        self.assertGreaterEqual(mean, 35, mean)
        self.assertLessEqual(mean, 55, mean)
        # The legacy method on the same palette picks the salmon and red UI slots.
        _, _, _, old = build(self.palette, source=WORDMARK, style='legacy')
        self.assertTrue(set(old) & set(RESERVED))

    def test_no_reserved_or_banked_palette_entries(self):
        _, _, _, pixels = build(self.palette)
        used = set(pixels)
        self.assertFalse(used & set(RESERVED), sorted(used & set(RESERVED)))
        self.assertFalse(used & set(BANK), sorted(used & set(BANK)))
        self.assertNotIn(255, used)
        self.assertLessEqual(used, set(self.ramp) | {self.black})
        self.assertEqual(menu_logo_excluded(), set(RESERVED) | set(BANK) | {255})

    def test_letters_stay_crisp_and_use_a_ramp(self):
        _, _, _, pixels = build(self.palette)
        self.assertGreaterEqual(len(set(pixels) - {self.black}), 6)
        self.assertEqual(build(self.palette)[3], pixels)  # deterministic

    def test_palette_without_gold_is_refused(self):
        grey = bytes(c for i in range(256) for c in (i, i, i))
        with self.assertRaises(ValueError):
            build(grey)

    def test_builder_uses_the_name_only_logo_and_keeps_legacy(self):
        build_aga = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("prepare_menu_logo(ROOT/'resources/media/AmiWind_logo_name_only.png'", build_aga)
        self.assertIn("style='legacy'", build_aga)
        self.assertIn("'--menu-logo',choices=['gold','legacy'],default='gold'", build_aga)
        # The startup stream keeps the wordmark and its own palette.
        self.assertIn("prepare_logo(logo,logo_stream,", build_aga)


if __name__ == '__main__':
    unittest.main()
