# SPDX-License-Identifier: GPL-3.0-only
"""A CHIM frame's standing hull traced as one scene (chim.collision.FrameScene). Synthetic data."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.collision import FrameScene, stand_height  # noqa: E402
from chim import format as F  # noqa: E402
from chim.validate import face_polygons, ground_max, validate  # noqa: E402
from player_hull import MINS  # noqa: E402
from test_chim_format import ROWS, fixture  # noqa: E402


class FrameSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.receipt, cls.source = fixture(Path(cls.tmp.name))
        fails, cls.world = validate(cls.tmp.name, cls.source)
        assert not fails, fails
        cls.scene = FrameScene(cls.world)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_box_stands_on_the_ground_everywhere_including_chunk_borders(self):
        # away from placements; across the chunk borders x = -256, 0, 256 and y = 0
        for x, y in ((-300.0, -400.0), (-256.2, -400.0), (-255.8, -400.0), (0.1, -350.0), (255.9, -330.0),
                     (-100.0, 0.2), (-100.0, -0.2)):
            with self.subTest(x=x, y=y):
                z = stand_height(self.scene, x, y)
                want = ground_max(self.source, x + MINS[0], y + MINS[1], x - MINS[0], y - MINS[1]) - MINS[2]
                self.assertIsNotNone(z)
                self.assertLess(abs(z - want), 0.3, (z, want))

    def test_placed_models_collide_where_placed(self):
        # the large box (ref 12) at (130, 70): a sideways trace at its centre height is stopped by it
        r = next(r for c in self.world['chunks'] for r in c['owned'] if r['ref'] == 12)
        x, y, z = r['origin']
        hit = self.scene.trace((x - 300, y, z + 40), (x, y, z + 40))
        self.assertIsNotNone(hit)
        self.assertEqual(hit['reference'], 12)
        self.assertLess(hit['fraction'], 0.9)

    def test_every_chunk_and_placement_is_a_brush(self):
        refs = [b[3] for b in self.scene.brushes if not isinstance(b[3], str)]
        self.assertEqual(sorted(refs), sorted(r['ref'] for r in ROWS))
        self.assertEqual(sum(1 for b in self.scene.brushes if isinstance(b[3], str)), len(self.world['chunks']))

    def test_the_spatial_index_gives_the_scan_s_results(self):
        # CHIM-STAIRGATE-SLOW-33: traces test only brushes near them; every result equals the full scan
        import random
        rnd = random.Random(7)
        scan = FrameScene(self.world)
        scan._trace_brushes = lambda a, b: (br for br, box in zip(scan.brushes, scan.boxes)
                                            if all(max(a[k], b[k]) >= box[k] and min(a[k], b[k]) <= box[k + 3]
                                                   for k in range(3)))
        for _ in range(300):
            a = (rnd.uniform(-520, 520), rnd.uniform(-520, 520), rnd.uniform(-40, 120))
            b = (a[0] + rnd.uniform(-60, 60), a[1] + rnd.uniform(-60, 60), a[2] + rnd.uniform(-80, 20))
            self.assertEqual(self.scene.trace(a, b), scan.trace(a, b))

    def test_frame_polys_are_placed_where_the_hull_is(self):
        from chim.collision import frame_polys
        polys = frame_polys(self.world)
        refs = {ref for _, ref in polys}
        self.assertEqual(refs - {'world'}, {r['ref'] for r in ROWS})
        terrain = [p for p, ref in polys if ref == 'world']
        self.assertEqual(len(terrain), sum(len(face_polygons(F.read_brush_image(c['image'])))
                                           for _, _, chunks in self.world['frames'] for c in chunks))
        # the large box's top face lies where a box dropped onto it comes to rest
        r = next(r for c in self.world['chunks'] for r in c['owned'] if r['ref'] == 12)
        top = max(max(p[2] for p in pts) for pts, ref in polys if ref == 12)
        z = stand_height(self.scene, r['origin'][0], r['origin'][1])
        self.assertLess(abs(z + MINS[2] - top), 0.5)


if __name__ == '__main__':
    unittest.main()
