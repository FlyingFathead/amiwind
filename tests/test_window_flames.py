# SPDX-License-Identifier: GPL-3.0-only
"""FIREPIT-FLAMES-62: the world-wide check of the flames of every CHIM window frame (tools/window_flames_check.py)
against the engine's bounds (aw_guard_torch.c STATIC_FLAME_MAX, SLOT_FLAMES). Synthetic measures only."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import window_flames_check as W  # noqa: E402


class WindowFlamesCheck(unittest.TestCase):
    def test_bounds_are_the_engines(self):
        map_max, slot_max = W.engine_bounds()
        self.assertEqual(map_max, 128)
        # the v0.0.62 release world's busiest frame carries 49 rows (tools/chim/flames.py measure): room above it
        self.assertGreaterEqual(slot_max, 49)

    def test_a_frame_over_the_slot_bound_fails(self):
        _, slot_max = W.engine_bounds()
        measured = {'per_frame': [{'cell': [2, 4], 'frame': 'rcp2_p4', 'emitters': 1},
                                  {'cell': [4, -12], 'frame': 'town', 'emitters': slot_max},
                                  {'cell': [0, 0], 'frame': 'rcp0_p0', 'emitters': slot_max + 1}]}
        result = W.check(measured)
        self.assertEqual(result['busiest'], slot_max + 1)
        self.assertEqual(result['over'], [{'cell': [0, 0], 'frame': 'rcp0_p0', 'emitters': slot_max + 1}])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'm.json'
            path.write_text(json.dumps(measured), encoding='utf-8')
            self.assertEqual(W.main(['--measured', str(path)]), 1)
            measured['per_frame'].pop()
            path.write_text(json.dumps(measured), encoding='utf-8')
            self.assertEqual(W.main(['--measured', str(path)]), 0)


if __name__ == '__main__':
    unittest.main()
