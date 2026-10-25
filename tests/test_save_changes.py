# SPDX-License-Identifier: GPL-3.0-only
"""The world-state change list in saves (AWS4 feature bit 8; engine aw_save.h, aw_save_codec.c, aw_save.c and
aw_actors.c): native round trips of the codec (tests/aga_save_changes_test.c), the bytes of a save without a change
list pinned to the codec before the change list existed (the dev line 723d6bb9: same input, same SHA-256), and the
engine wiring (aw_actors.c exports and imports the list; island positions; the intro roles under bit 31).
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'

# aga_save_changes_test.c's "base" and "rows" saves made with the dev line's codec (723d6bb9, -DPIN_ONLY): a save
# without a change list must stay these bytes
BASE = '4d0b3e9fd087e710fc69fc3a72173ee5f0ba25f40b8338da9eb9d79149ae7c8b'
ROWS = 'd6e53fe2078b453d8a85cbdc154d0da37414be2b47bb9dfb9fd5d0dc397fde53'


class ChangeListCodecTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_codec(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-save-changes-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_save_changes_test.c',
                                          [SRC / n for n in ('aw_save_codec.c', 'aw_story.c', 'aw_state.c',
                                                             'aw_inventory.c')],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter', '-fsanitize=undefined',
                                                  '-fno-sanitize-recover=all'],
                                          arguments=[str(out)])
            lines = dict(line.split(' ', 1) for line in out.read_text(encoding='ascii').splitlines())
        self.assertEqual(lines['base'].split()[0], BASE)
        self.assertEqual(lines['rows'].split()[0], ROWS)
        self.assertIn('refusals', lines)


class WiringTests(unittest.TestCase):
    def test_engine_wiring(self):
        actors = (SRC / 'aw_actors.c').read_text(encoding='utf-8')
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('aw_save_changes_export = SaveExport;', actors)
        self.assertIn('aw_save_changes_import = SaveImport;', actors)
        # positions in the change list are island positions (a recentre does not move them)
        self.assertIn('VectorAdd (e->v.origin, d, c->origin);', actors)
        self.assertIn('VectorSubtract (c->origin, d, ent->v.origin);', actors)
        # a load hands the list over before the window spawns, folding an old save's actor rows
        self.assertLess(save.index('AW_SaveFoldActors(&world,&pending_changes)'),
                        save.index('AW_BarrierLoad();AW_OpeningSpawn();'))
        self.assertIn('AW_SaveEncodeChanges(raw,AW_SAVE_BYTES,&world,&save_changes)', save)
        # object state (v0.0.51, the scripts' Disable and Lock): merged after the actors' export, read after their
        # import, set by the script host
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertLess(save.index('aw_save_changes_export(&save_changes)'), save.index('aw_save_objects_export(&save_changes)'))
        self.assertLess(save.index('aw_save_changes_import(&pending_changes)'),
                        save.index('aw_save_objects_import(&pending_changes)'))
        self.assertIn('aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;', host)
        # death stays (no respawn yet), also for an actor a level change spawned again from its map; a load's (or a
        # new map's) changes reach the scene's own actors at the next window tick, after the combat set-up
        self.assertIn('c->dead = c->dead || state == 2;', actors)
        self.assertLess(actors.index('if (apply_pending)\n\t\tApplyLoaded ();'), actors.index('SpawnQueued ();\n\tif (++n % 10)'))

    def test_load_menu_says_why_a_slot_cannot_load(self):
        # AW25-06: absent, unreadable and other-data saves were all "(empty)"; the slot state is read once at the
        # menu's refresh (not every frame) and only for a slot without a loadable save
        menu = (SRC / 'aw_savemenu.c').read_text(encoding='utf-8')
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('int AW_SaveSlotState(uint32_t profile,int slot)', save)
        for reason in ('" (unreadable)"', '" (other game data or build)"', '" (empty)"'):
            self.assertIn(reason, menu)
        refresh = menu[menu.index('static void refresh(void)'):menu.index('static const char *slot_reason')]
        self.assertIn('AW_SaveSlotState(', refresh)
        draw = menu[menu.index('void AW_SaveMenuDraw(void)'):]
        self.assertNotIn('AW_SaveSlotState(', draw)


if __name__ == '__main__':
    unittest.main()
