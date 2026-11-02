# SPDX-License-Identifier: GPL-3.0-only
"""CURSOR-MW-58: the original's mouse pointer as the default cursor.

The builder (tools/prepare_ui.py) converts textures/tx_cursor.dds from the player's own game data into
gfx/cursor.awc; when the data has no pointer, no file is written and nothing fails, and the engine
(engine/aga/src/aw_ui.c AW_UICursor) keeps AmiWind's own cursor. The engine side is exercised natively by
tests/aga_ui_test.c (pointer, none, corrupt), aga_worldui_test.c and aga_menu_test.c; this file checks the
converter on synthetic art (no game data in the repository) and the contract both sides share."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image  # noqa: E402
import prepare_ui  # noqa: E402

GOLD = (210, 184, 121)


def palette():
    """A test palette: a grey ramp with the UI gold at index 40 and black at 0."""
    out = bytearray()
    for i in range(256):
        out += bytes((i, i, i))
    out[40 * 3:40 * 3 + 3] = bytes(GOLD)
    return bytes(out)


def pointer_png(tip_x=6):
    """A 32x32 arrow like the original's: solid from (TIP_X, 0), two pixels wide, widening downwards, clear elsewhere."""
    art = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    for y in range(24):
        for x in range(tip_x, min(32, tip_x + 2 + y * 3 // 4)):
            art.putpixel((x, y), GOLD + (255,))
    stream = io.BytesIO()
    art.save(stream, format='PNG')
    return stream.getvalue()


class Assets:
    """Stands in for npc_geometry.Assets: read() by name, KeyError when the data has no such asset."""
    def __init__(self, files):
        self.files, self.reads = files, []

    def read(self, name):
        self.reads.append(name)
        return self.files[name]


class CursorConversion(unittest.TestCase):
    def test_pointer_found_is_written_with_its_tip_and_clear_pixels(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            assets = Assets({'textures/tx_cursor.dds': pointer_png()})
            record, colours = prepare_ui.write_cursor(assets, palette(), out)
            self.assertEqual(assets.reads, ['textures/tx_cursor.dds'])
            raw = (out / 'cursor.awc').read_bytes()
            self.assertEqual(raw[:4], b'AWC1')
            self.assertEqual((raw[4], raw[5]), (16, 16))
            self.assertEqual(len(raw), 8 + 16 * 16)
            self.assertEqual((raw[6], raw[7]), (3, 0))       # the tip: 6,0 in the 32x32 art, halved
            pixels = raw[8:]
            self.assertEqual(pixels[raw[7] * 16 + raw[6]], 40)  # the tip is drawn, in the gold entry
            self.assertEqual(pixels[0], 255)                    # clear corner
            self.assertEqual(pixels[15 * 16 + 15], 255)
            self.assertEqual(colours, {40})
            self.assertEqual(record['output'], 'cursor.awc')
            self.assertEqual(record['tip'], [3, 0])
            self.assertEqual(len(record['source_sha256']), 64)

    def test_pointer_missing_writes_nothing_and_does_not_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            (out / 'cursor.awc').write_bytes(b'stale')        # from an earlier conversion into the same folder
            record, colours = prepare_ui.write_cursor(Assets({}), palette(), out)
            self.assertFalse((out / 'cursor.awc').exists())
            self.assertEqual((record['output'], colours), (None, set()))

    def test_unreadable_or_empty_pointer_writes_nothing(self):
        empty = io.BytesIO()
        Image.new('RGBA', (32, 32), (0, 0, 0, 0)).save(empty, format='PNG')
        for raw in (b'not an image', empty.getvalue()):
            with tempfile.TemporaryDirectory() as temp:
                record, _ = prepare_ui.write_cursor(Assets({'textures/tx_cursor.dds': raw}), palette(), Path(temp))
                self.assertFalse((Path(temp) / 'cursor.awc').exists())
                self.assertIsNone(record['output'])

    def test_the_tip_follows_the_art(self):
        packet = prepare_ui.cursor_packet(pointer_png(tip_x=12), palette())
        self.assertEqual((packet[6], packet[7]), (6, 0))


class CursorContract(unittest.TestCase):
    def test_engine_reads_the_file_the_builder_writes(self):
        ui = (ROOT / 'engine/aga/src/aw_ui.c').read_text(encoding='utf-8')
        self.assertIn('"gfx/cursor.awc"', ui)
        self.assertIn('memcmp(p,"AWC1",4)', ui)
        self.assertIn('#define CURSOR_MAX 32', ui)
        self.assertLessEqual(prepare_ui.CURSOR, 32)
        self.assertEqual(prepare_ui.CURSOR_FILE, 'cursor.awc')
        # the saved setting, Morrowind's (2) by default, and the Options entry and console row that set it
        self.assertIn('static cvar_t cursor_type={"aw_cursor_type","2",true};', ui)
        menu = (ROOT / 'engine/aga/src/aw_menu.c').read_text(encoding='utf-8')
        self.assertIn('"Mouse cursor: Morrowind":"Mouse cursor: AmiWind"', menu)
        rows = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('VIDEO|cursortype|aw_cursor_type|', rows)

    def test_every_window_asks_for_the_original_pointer_first(self):
        src = ROOT / 'engine/aga/src'
        for name in ('aw_worldui.c', 'aw_menu.c', 'aw_reader.c', 'aw_character.c', 'aw_gallery.c'):
            self.assertIn('AW_UICursor(', (src / name).read_text(encoding='utf-8'), name)

    def test_the_file_is_part_of_the_ui_feature(self):
        features = json.loads((ROOT / 'config/release-features.json').read_text(encoding='utf-8'))
        ui = next(f for f in features['features'] if f['id'] == 'ui')
        self.assertIn('id1/gfx/cursor.awc', ui['patterns'])


if __name__ == '__main__':
    unittest.main()
