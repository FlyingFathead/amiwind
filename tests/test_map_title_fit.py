# SPDX-License-Identifier: GPL-3.0-only
"""MAP-VERSION-2-DEFAULT-68: the measure of which place names fit map version 2's title in the game's font
(tools/map_title_fit.py), on synthetic tables, fonts and masters: the widths, the fallback rule (the same numbers as
the engine's layout helper, aw_layout.c AW_LayoutTitle), the names held to the engine's 63 characters, the names read
from an image's tables or straight from the masters. Seconds."""
import io
import json
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import map_title_fit as fit  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def font(advance=6, wide=None):
    """An AWF1 font of no pixels, every character ADVANCE wide (WIDE: {char: advance} besides)."""
    metrics = b''
    for c in range(256):
        metrics += struct.pack('<HBBbbBB', 0, 0, 0, 0, 0, (wide or {}).get(c, advance), 0)
    return b'AWF1' + bytes([12, 14]) + struct.pack('<H', 0) + metrics


def arn2(regions, places):
    rows = [struct.pack('<iiII', i, 0, 0, i) for i in range(len(places))]
    return (b'ARN2' + struct.pack('<III', len(regions), len(places), len(rows))
            + b''.join(r.ljust(64, b'\0') for r in regions) + b''.join(p.ljust(64, b'\0') for p in places) + b''.join(rows))


def record(tag, subs, flags=0):
    payload = b''.join(k + struct.pack('<I', len(v)) + v for k, v in subs)
    return tag + struct.pack('<III', len(payload), 0, flags) + payload


class TheRule(unittest.TestCase):
    def test_the_numbers_are_the_engines(self):
        numbers = fit.layout_numbers()
        self.assertEqual((numbers['plaque_margin'], numbers['plaque_end'], numbers['console_char']),
                         (fit.PLAQUE_MARGIN, fit.PLAQUE_END, fit.CONSOLE_CHAR))
        ui = (SRC / 'aw_worldui.c').read_text(encoding='utf-8')
        self.assertIn('AW_LayoutTitle(&map_name_fit,%d,' % fit.BAR_W, ui)
        self.assertIn('window_title(6,6,%d,map_name,gold)' % fit.BAR_W, ui)
        self.assertIn('static char map_name[%d]' % (fit.NAME_MAX + 1), ui)
        self.assertIn('static int title_plaque(int x,int y,int w,int *plaque_x,int *plaque_w)',
                      (SRC / 'aw_icons.c').read_text(encoding='utf-8'))

    def test_the_game_font_then_the_console_glyphs_then_cut(self):
        self.assertEqual(fit.fit(120, 20), ('game', 134, 20))
        self.assertEqual(fit.fit(288, 48), ('game', 302, 48))        # exactly the 288 pixels of room
        self.assertEqual(fit.fit(289, 48), ('console', 48 * 4 + 14, 48))
        self.assertEqual(fit.fit(400, 72), ('console', 302, 72))
        self.assertEqual(fit.fit(500, 73), ('cut', 302, 72))

    def test_widths_are_the_fonts_advances_and_link_marks_have_none(self):
        advances = fit.font_advances(font(6, {ord('W'): 11}))
        self.assertEqual(fit.text_width(b'Wa', advances), 17)
        self.assertEqual(advances[2], 0)
        self.assertEqual(advances[3], 0)
        self.assertIsNone(fit.font_advances(b'AWF1' + bytes(10)))
        self.assertIsNone(fit.font_advances(font()[:-1]))


class TheMeasure(unittest.TestCase):
    def tree(self, temp, advance):
        id1 = Path(temp) / 'id1'
        (id1 / 'gfx').mkdir(parents=True)
        (id1 / 'world').mkdir()
        (id1 / 'gfx' / 'book12.awf').write_bytes(font(advance))
        (id1 / 'world' / 'region-names.awn').write_bytes(arn2([b'Bitter Coast Region'], [b'Seyda Neen', b'P' * 60]))
        cells = Path(temp) / 'cell-numbers.json'
        cells.write_text(json.dumps({'maps': [{'map': 'a', 'number': 1, 'cell': 'Seyda Neen, Census and Excise Office'},
                                              {'map': 'b', 'number': 2, 'cell': 'R' * 50},
                                              {'map': 'c', 'number': 3, 'cell': 'Q' * 70}]}), encoding='utf-8')
        return id1, cells

    def test_image_tables_counted_and_the_fallbacks_named(self):
        with tempfile.TemporaryDirectory() as temp:
            id1, cells = self.tree(temp, 6)        # 6 pixels a character: 48 fit the game font
            report = fit.measure(id1, cells)
        self.assertEqual(report['font'], 'gfx/book12.awf')
        self.assertEqual(report['room_px'], 288)
        self.assertEqual(report['counts']['region'], {'names': 1, 'game': 1, 'console': 0, 'cut': 0})
        self.assertEqual(report['counts']['place'], {'names': 2, 'game': 1, 'console': 1, 'cut': 0})
        self.assertEqual(report['counts']['room'], {'names': 3, 'game': 1, 'console': 2, 'cut': 0})
        long_room = [r for r in report['names'] if r['name'].startswith('QQQ')][0]   # held to the engine's 63
        self.assertEqual((long_room['chars'], long_room['held_to'], long_room['game_px']), (63, 63, 378))
        self.assertEqual(sorted(r['name'][:1] for r in report['fallbacks']), ['P', 'Q', 'R'])
        self.assertEqual(report['widest']['room'][0]['name'], 'Q' * 70)

    def test_the_magic_font_when_the_book_font_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            id1, cells = self.tree(temp, 4)
            (id1 / 'gfx' / 'book12.awf').rename(id1 / 'gfx' / 'magic12.awf')
            report = fit.measure(id1, cells)
            self.assertEqual(report['font'], 'gfx/magic12.awf')
            self.assertEqual(report['fallbacks'], [])      # 4 pixels a character: everything fits
            (id1 / 'gfx' / 'magic12.awf').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                fit.measure(id1, cells)

    def test_names_straight_from_the_masters(self):
        with tempfile.TemporaryDirectory() as temp:
            id1, _ = self.tree(temp, 6)
            masters = Path(temp) / 'data'
            masters.mkdir()
            (masters / 'Morrowind.esm').write_bytes(
                record(b'TES3', [(b'HEDR', bytes(300))])
                + record(b'REGN', [(b'NAME', b'Sheogorad\0'), (b'FNAM', b'Sheogorad Region\0')])
                + record(b'CELL', [(b'NAME', b'Seyda Neen\0'), (b'DATA', struct.pack('<Iii', 0, -2, -9))])
                + record(b'CELL', [(b'NAME', b'\0'), (b'DATA', struct.pack('<Iii', 0, 5, 5))])
                + record(b'CELL', [(b'NAME', b'Arrille\'s Tradehouse\0'), (b'DATA', struct.pack('<Iii', 1, 0, 0)),
                                   (b'FRMR', struct.pack('<I', 1)), (b'NAME', b'ignored\0')])
                + record(b'CELL', [(b'NAME', b'Gone Room\0'), (b'DELE', bytes(4)), (b'DATA', struct.pack('<Iii', 1, 0, 0))]))
            (masters / 'Bloodmoon.esm').write_bytes(
                record(b'REGN', [(b'NAME', b'Brodir Grove Region\0'), (b'FNAM', b'Solstheim, Brodir Grove Region\0')]))
            self.assertEqual(fit.master_names(masters),
                             ([b'Sheogorad Region', b'Solstheim, Brodir Grove Region'], [b'Seyda Neen'],
                              [b"Arrille's Tradehouse"]))
            out = Path(temp) / 'report.json'
            text = io.StringIO()
            with redirect_stdout(text):
                self.assertEqual(fit.main(['--id1', str(id1), '--masters', str(masters), '--out', str(out)]), 0)
            self.assertIn('names from the masters', text.getvalue())
            self.assertIn('=== PHASE 2/2', text.getvalue())
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['counts']['region']['names'], 2)


if __name__ == '__main__':
    unittest.main()
