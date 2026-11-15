# SPDX-License-Identifier: GPL-3.0-only
"""The active-effect icons (HUD-ACTIVE-EFFECTS-ROW-64, docs/HUD_ACTIVE_EFFECTS.md): the rules natively, the builder's
effect file from synthetic pictures only (no game icon is used or stored here), the palette overlay's reading of it, and
the engine's wiring (the HUD, the Stats window and V, the setting, the console rows)."""
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class EffectRowRuleTests(unittest.TestCase):
    def test_groups_grid_more_texts_and_directory(self):
        native.NativeSourceTests().compile_run('aga_fxrow_test.c', [SRC / 'aw_fxrow_rules.c'], cflags=UBSAN)


class EffectFileTests(unittest.TestCase):
    def test_rows_by_effect_number_pictures_and_descriptions(self):
        import prepare_icons as icons
        from test_hud_icons import Assets, PALETTE, png
        assets = Assets()
        assets.files['icons/s/tx_s_test_light.dds'] = png((16, 16), (250, 250, 120, 255))
        assets.files['icons/s/tx_s_test_shield.dds'] = png((16, 16), (60, 60, 250, 255))
        effects = {41: {'icon': 's\\tx_s_test_light.tga', 'description': 'Lights  the\r\nway.'},
                   3: {'icon': 's\\tx_s_test_shield.tga', 'description': ''},
                   7: {'icon': 's\\tx_s_missing.tga', 'description': 'Heavier.'}}
        with tempfile.TemporaryDirectory() as tmp:
            report = icons.write_effects(assets, tmp, effects, PALETTE)
            raw = (Path(tmp) / icons.EFFECTS_FILE).read_bytes()
        self.assertEqual(raw[:4], b'AWE1')
        count, small, large = struct.unpack_from('<HBB', raw, 4)
        self.assertEqual((count, small, large), (143, 12, 16))
        header = (SRC / 'aw_fxrow.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_FX_HUD_ICON %d' % icons.EFFECT_SMALL, header)
        self.assertIn('#define AW_FX_LIST_ICON %d' % icons.EFFECT_LARGE, header)
        self.assertIn('#define AW_FX_EFFECTS %d' % icons.EFFECT_COUNT, header)
        self.assertIn('#define AW_FX_FILE "%s"' % icons.EFFECTS_FILE, header)
        row = lambda i: struct.unpack_from('<IIIHH', raw, 8 + 16 * i)
        s, l, d, n, pad = row(41)
        self.assertTrue(s and l and d and pad == 0)
        self.assertEqual(raw[d:d + n], b'Lights the way.')                  # one line, spaces folded
        self.assertEqual(len(set(raw[s:s + 144])), 1); self.assertEqual(len(set(raw[l:l + 256])), 1)
        self.assertNotIn(255, raw[s:s + 144])                                # never the transparent index
        s, l, d, n, _ = row(3)
        self.assertTrue(s and l); self.assertEqual((d, n), (0, 0))           # no description
        s, l, d, n, _ = row(7)
        self.assertEqual((s, l), (0, 0)); self.assertEqual(raw[d:d + n], b'Heavier.')   # held, never replaced
        self.assertIn('mgef:7', report['held'])
        self.assertEqual(row(0), (0, 0, 0, 0, 0))                           # no record: an empty row
        self.assertEqual((report['icons'], report['descriptions'], report['bytes']), (2, 2, len(raw)))
        # the palette overlay knows the file: both pictures of each effect, never its texts
        import sky_palette_overlay as overlay
        spans, why = overlay.spans(raw, 'gfx/effects.awe')
        self.assertEqual(why, 'indexed pixels')
        self.assertEqual(sorted(size for _, size in spans), [144, 144, 256, 256])

    def test_the_inventory_stage_reads_every_master(self):
        text = (ROOT / 'tools' / 'prepare_inventory.py').read_text(encoding='utf-8')
        self.assertIn("EFFECT_MASTERS=('Morrowind.esm','Tribunal.esm','Bloodmoon.esm')", text)
        self.assertIn('effects=effect_records(data))', text)


class EffectRowWiringTests(unittest.TestCase):
    def test_the_hud_the_stats_window_and_the_setting(self):
        fx = code('aw_fxrow.c')
        self.assertIn('static cvar_t hud_effects={"aw_hud_effects","1",true};', fx)
        self.assertIn('n=AW_EffectsList(AW_ACTOR_PLAYER_REF,fx,AW_EFFECTS_PLAYER);', fx)   # one pass a frame
        self.assertIn('if(sig==passive_sig)return;', fx)                  # the spell list read again only on a change
        self.assertIn('AW_ResetRegister("active-effect icons",reset_fx,NULL);', fx)
        self.assertIsNone(re.search(r'\b(Hunk_\w+|Z_Malloc|Cache_Alloc)\s*\(', fx))
        self.assertIn('if(aw_hud_effects_draw && (boxes&AW_HUD_STATS))aw_hud_effects_draw();', code('aw_ui.c'))
        self.assertIn('sb_lines += aw_fx_strip_lines ();', code('screen.c'))
        stats = code('aw_statswin.c')
        self.assertIn("if((key=='v' || key=='V') && aw_stats_effects_open){", stats)
        self.assertIn('if(aw_stats_effects_row)aw_stats_effects_row(8,EFFECTS_Y,122);', stats)
        # the stats window opens as a menu panel since v0.0.65 (the opening's menus, enabled by the original's scripts),
        # with the close callback that frees the effects list
        self.assertIn('AW_WorldUIOpenMenuPanel(stats_draw,stats_key,stats_closed,AW_MENU_STATS);', stats)
        self.assertIn('AW_FxRowInit();', code('aw_debug.c'))
        self.assertIn('aw_fxrow_rules.c aw_fxrow.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        self.assertIn('"aw_hud_effects"', (SRC / 'aw_boolean.h').read_text(encoding='utf-8'))
        self.assertRegex((ROOT / 'config' / 'game.cfg').read_text(encoding='utf-8'), r'\naw_hud_effects 1\n')

    def test_the_console_rows_are_listed(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('\nUI / CONSOLE|hudeffects|aw_hud_effects|', catalogue)
        self.assertIn('\nUI / CONSOLE|effects|aw_effects_status|', catalogue)
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg hudeffects`', page)
        self.assertIn('`dbg effects`', page)


if __name__ == '__main__':
    unittest.main()
