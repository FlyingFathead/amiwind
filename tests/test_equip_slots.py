# SPDX-License-Identifier: GPL-3.0-only
"""The original's equipment slot rules in a sequence and the drawn parts of the outfit (tests/aga_equip_slots_test.c;
ROBE-PART-NOT-BAKED-62, EQUIP-ACTION-REGRESSION-62)."""
import os
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


class EquipSlotSequenceTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_slot_sequence_and_drawn_parts(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_aga_native_source import NativeSourceTests
        NativeSourceTests.compile_run(self, 'aga_equip_slots_test.c',
                                      [SRC / 'aw_inventory.c', SRC / 'aw_state.c', SRC / 'aw_player_parts.c'],
                                      defines=['AW_INVENTORY_RULES_ONLY'],
                                      cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                              '-Wno-unused-parameter', '-fsanitize=address,undefined',
                                              '-fno-sanitize-recover=all'])


if __name__ == '__main__':
    unittest.main()
