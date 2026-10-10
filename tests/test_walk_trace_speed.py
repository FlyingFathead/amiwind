# SPDX-License-Identifier: GPL-3.0-only
"""The stair walk's faster trace, collision box grid and headroom grid give bit-identical answers to the
original code they replace (BUILD-STAIR-WALK-SLOW-33): random segments and points over synthetic flights,
compared with the kept reference implementations, value for value (repr, so -0.0 and 0.0 differ)."""
import importlib.util
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
READY = importlib.util.find_spec('numpy') is not None


@unittest.skipUnless(READY, 'numpy required')
class WalkTraceIdentity(unittest.TestCase):
    def scenes(self):
        import stair_walk
        from test_stair_walk import build
        for raw in (build(), build(fill=True), build(rise=7.)):
            yield stair_walk, raw

    def test_trace_and_box_filter_match_the_reference(self):
        rng = random.Random(34)
        for stair_walk, raw in self.scenes():
            for hull in (0, 1):
                scene = stair_walk.Collision(raw, hull=hull)
                for _ in range(3000):
                    a = (rng.uniform(-120, 140), rng.uniform(-60, 100), rng.uniform(-40, 80))
                    if rng.random() < .3:
                        b = (a[0], a[1], a[2] - rng.uniform(0, 300))      # a settle
                    elif rng.random() < .2:
                        b = a                                           # a point test
                    else:
                        b = tuple(v + rng.uniform(-40, 40) for v in a)
                    self.assertEqual(list(scene._trace_brushes(a, b)), list(scene.reference_trace_brushes(a, b)))
                    self.assertEqual(repr(scene.trace(a, b)), repr(scene.reference_trace(a, b)))

    def test_headroom_matches_every_triangle(self):
        import numpy as np
        rng = random.Random(35)
        for stair_walk, raw in self.scenes():
            room = stair_walk.Headroom(stair_walk._faces(raw))
            full = stair_walk.Headroom(stair_walk._faces(raw))
            full._near = lambda *args: None                         # every triangle, as before
            for _ in range(3000):
                x, y, z = rng.uniform(-200, 200), rng.uniform(-200, 200), rng.uniform(-30, 60)
                got, ref = room._heights(x, y, True), room.reference_heights(x, y, True)
                self.assertTrue(np.array_equal(got[0], ref[0]) and np.array_equal(got[1], ref[1]))
                self.assertEqual(repr(room.ground(x, y, z)), repr(full.ground(x, y, z)))
                self.assertEqual(repr(room.ground(x, y, z, True)), repr(full.ground(x, y, z, True)))
                self.assertEqual(room.free(x, y, z, 56.), full.free(x, y, z, 56.))
                side = rng.choice((None, -stair_walk.SHELL_MARGIN))
                self.assertEqual(room.box_free((x, y, z), side=side), full.box_free((x, y, z), side=side))

    def test_gate_rows_unchanged(self):
        """Whole-map rows from the gate equal those of the reference implementations."""
        import json
        from unittest.mock import patch
        import audit_walkability
        for stair_walk, raw in self.scenes():
            tmp = Path(__import__('tempfile').mkdtemp()); self.addCleanup(__import__('shutil').rmtree, tmp)
            (tmp / 'room.bsp').write_bytes(raw)
            fast = stair_walk.check_map((str(tmp / 'room.bsp'), None, {}))
            with patch.object(audit_walkability.Scene, 'trace', audit_walkability.Scene.reference_trace), \
                    patch.object(stair_walk.Collision, '_trace_brushes', stair_walk.Collision.reference_trace_brushes), \
                    patch.object(stair_walk.Headroom, '_near', lambda self, *args: None):
                slow = stair_walk.check_map((str(tmp / 'room.bsp'), None, {}))
            self.assertEqual(json.dumps(fast), json.dumps(slow))


if __name__ == '__main__':
    unittest.main()
