# SPDX-License-Identifier: GPL-3.0-only
"""Harvest pick audit (HARVEST-BITTERCOAST-29): the offline replay of the engine's pick rule."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import harvest_pick_audit as H  # noqa: E402

CATALOGUE = """AWH4 4 1 2 2083 0000 1
progs/harvest/a.mdl 00 -2 -3 -4 2 3 4
aw:h:aaaa 11 7 @0 11 3 1 10 20 30 0 90 0 1 Luminous Russula
aw:h:bbbb 12 8 @0 11 4 1 -5 0 0 10 0 0 2 Violet Coprinus
"""


class HarvestPickAuditTests(unittest.TestCase):
    def test_catalogue_rows(self):
        boxes, plants = H.read_catalogue(CATALOGUE)
        self.assertEqual(boxes, [((-2.0, -3.0, -4.0), (2.0, 3.0, 4.0))])
        self.assertEqual([p['ref'] for p in plants], [7, 8])
        self.assertEqual(plants[0]['origin'], (10.0, 20.0, 30.0))
        self.assertEqual(plants[1]['scale'], 2.0)
        self.assertEqual(plants[0]['label'], 'Luminous Russula')
        with self.assertRaises(ValueError):
            H.read_catalogue('AWH2 1 1 1\n')

    def test_slab_test_matches_the_engine(self):
        plant = {'origin': (0.0, 0.0, 0.0), 'angles': (0.0, 0.0, 0.0), 'scale': 1.0}
        box = H.Box(plant, ((-2, -2, -2), (2, 2, 2)))
        self.assertAlmostEqual(box.entry((-20, 0, 0), (1, 0, 0), 72), 18)
        self.assertIsNone(box.entry((-20, 0, 0), (1, 0, 0), 10))      # a wall at 10 hides it
        self.assertIsNone(box.entry((-20, 5, 0), (1, 0, 0), 72))       # beside the ray
        scaled = H.Box(dict(plant, scale=2.0), ((-2, -2, -2), (2, 2, 2)))
        self.assertAlmostEqual(scaled.entry((-20, 0, 0), (1, 0, 0), 72), 16)

    def test_box_centre_follows_the_proxy_angles(self):
        # yaw 90 turns the model's +x offset to world +y; the pitch is negated as target() does
        box = H.Box({'origin': (0, 0, 0), 'angles': (0, 90, 0), 'scale': 1.0}, ((2, -1, -1), (4, 1, 1)))
        self.assertAlmostEqual(box.centre[0], 0, places=5)
        self.assertAlmostEqual(box.centre[1], 3, places=5)
        tilted = H.Box({'origin': (0, 0, 0), 'angles': (30, 0, 0), 'scale': 1.0}, ((2, -1, -1), (4, 1, 1)))
        self.assertGreater(tilted.centre[2], 0)   # proxy pitch 30 is drawn nose-up (pitch negated)

    def test_summary_and_check(self):
        rows = [
            {'map': 'vf0001', 'ref': 1, 'label': 'a', 'origin': [0, 0, 0], 'centre_in_solid': True,
             'positions': 3, 'pick_before': 0, 'pick_fixed': 3},
            {'map': 'vf0002', 'ref': 1, 'label': 'a', 'origin': [0, 0, 0], 'centre_in_solid': False,
             'positions': 2, 'pick_before': 0, 'pick_fixed': 0},
            {'map': 'vf0001', 'ref': 2, 'label': 'b', 'origin': [0, 0, 0], 'centre_in_solid': False,
             'positions': 4, 'pick_before': 0, 'pick_fixed': 0},
            {'map': 'vf0001', 'ref': 3, 'label': 'c', 'origin': [0, 0, 0], 'centre_in_solid': False,
             'positions': 0, 'pick_before': 0, 'pick_fixed': 0},
        ]
        report = H.summarise(rows)
        self.assertEqual(report['plants'], 3)
        self.assertEqual(report['unpickable_before'], [1, 2])
        self.assertEqual(report['unpickable_fixed'], [2])
        self.assertEqual(report['unreachable'], [3])
        self.assertEqual(H.check(report, known={}), [2])
        self.assertEqual(H.check(report, known={2: {'ref': 2, 'bug': 'X'}}), [])

    def test_known_list_is_empty(self):
        self.assertEqual(H.load_known(), {})

    def test_replay_matches_the_engine_source(self):
        runtime = (ROOT / 'engine/aga/src/aw_harvest_runtime.c').read_text(encoding='utf-8')
        self.assertIn('reach=72', runtime)
        self.assertRegex(runtime, r'inside=SV_Move\(world,vec3_origin,vec3_origin,world,MOVE_NORMAL')
        self.assertIn('if(!inside.startsolid && !inside.allsolid)continue;', runtime)
        self.assertEqual(H.REACH, float(re.search(r'reach=(\d+)', runtime).group(1)))
        world = (ROOT / 'engine/aga/qc/world.qc').read_text(encoding='utf-8')
        self.assertIn("self.view_ofs = '0 0 %s';" % H.VIEW_HEIGHT, world)

    def test_image_step_runs_the_audit_before_the_disk(self):
        source = (ROOT / 'tools/harvest_build.py').read_text(encoding='utf-8')
        step = source[source.index('def image_step'):source.index('def main')]
        self.assertIn('pick_audit(id1', step)
        self.assertIn('raise ValueError', step)


if __name__ == '__main__':
    unittest.main()
