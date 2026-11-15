# SPDX-License-Identifier: GPL-3.0-only
"""The save contract (SAVE-STATE-FIXED-CAPS-66): what a saved game must hold and what must be true after a load.

The budget: a synthetic 100-hour game's change list (sized from a late original save: about 7,700 changed references,
242 containers, 3,000 changed actors with their records, 2,800 script locals, every global, quest and topic, 1,400
refilled places, a 2,489-entry journal) is encoded as one saved game (tests/aga_save_budget_test.c): every part is
back after a load, a second save of the unchanged game gives the same bytes, and the file stays under 1 MiB. The
measured numbers are printed, so a run records the budget of the day.
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

SOURCES = ('aw_ledger.c', 'aw_ledger_drops.c', 'aw_save_codec.c', 'aw_story.c', 'aw_state.c', 'aw_inventory.c',
           'aw_jhist.c')
CFLAGS = ['-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-parameter',
          '-fsanitize=undefined,address', '-fno-sanitize-recover=all']


class SaveBudgetTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_two_swords_keep_their_own_condition_charge_and_slot_through_a_save(self):
        # SAVE-ITEM-INSTANCES-ONE-PER-KIND-66 (the contract's row A5): the item instances (tests/aga_item_instances_test.c)
        from test_aga_native_source import NativeSourceTests
        NativeSourceTests.compile_run(self, 'aga_item_instances_test.c',
                                      [SRC / n for n in ('aw_ledger.c', 'aw_ledger_drops.c', 'aw_save_codec.c', 'aw_story.c',
                                                         'aw_state.c', 'aw_inventory.c')],
                                      defines=['AW_INVENTORY_RULES_ONLY'], cflags=CFLAGS)

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_hundred_hour_game_fits_loads_whole_and_saves_again_the_same(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-save-budget-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_save_budget_test.c', [SRC / n for n in SOURCES],
                                          defines=['AW_INVENTORY_RULES_ONLY'], cflags=CFLAGS, arguments=[str(out)])
            lines = dict(line.split(' ', 1) for line in out.read_text(encoding='ascii').splitlines())
        numbers = {k: int(v) for k, v in lines.items()}
        # the contract's limit: well under 1 MiB in a 100-hour game (the records are the biggest part)
        self.assertLess(numbers['file_bytes'], 1048576, numbers)
        self.assertEqual(numbers['made_refused'], 0, 'a bound refused a change of the synthetic game')
        self.assertEqual(numbers['second_encode_same'], 1)
        for part in ('rows', 'actors', 'locals', 'scripts', 'contents', 'stolen', 'values', 'stamps', 'idents', 'records'):
            self.assertEqual(numbers['loaded_' + part], numbers['made_' + part], part)
        print('save budget:', ', '.join('%s=%d' % (k, numbers[k]) for k in
                                        ('plain_bytes', 'ledger_bytes', 'ledger_without_records_bytes', 'journal_bytes',
                                         'file_bytes', 'resident_bytes', 'encode_ms', 'decode_ms')))


if __name__ == '__main__':
    unittest.main()
