# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's CHIM frame (format 0.5, chim.seyda): the frame box, cell and origin agree with the
legacy scene stage, and the ground is the scene stage's own triangles plus the same sampler around
them, covering every tile of the frame once. Synthetic LAND, no game data."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import seyda  # noqa: E402


def grids():
    """Nine synthetic LAND cells around Seyda Neen's cell (-2, -9): 65 x 65 heights (world units), a
    coast where the ground dips below the water, 16 x 16 materials."""
    out = []
    for cy in range(-10, -7):
        for cx in range(-3, 0):
            heights = [[40.0 * math.sin((cx * 64 + i) / 23.0) + 30.0 * math.cos((cy * 64 + j) / 17.0) - 10.0
                        for i in range(65)] for j in range(65)]
            materials = [[(i + j + cx) % 3 + 1 for i in range(16)] for j in range(16)]
            out.append({'cell': [cx, cy], 'heights': heights, 'materials': materials})
    return out


class SeydaFrameTests(unittest.TestCase):
    def test_frame_agrees_with_the_scene_stage(self):
        from prepare_quake import CENTRE, GROUND_BOUNDS, TERRAIN_APRON
        self.assertEqual(seyda.TERRAIN_APRON, TERRAIN_APRON)
        self.assertEqual(seyda.ground_bounds(), GROUND_BOUNDS)
        self.assertEqual(seyda.centre(), tuple(float(v) for v in CENTRE))
        self.assertEqual(seyda.source_cell(), (-2, -9))
        (lx, ly), (hx, hy) = seyda.frame_box()
        (gx0, gy0), (gx1, gy1) = GROUND_BOUNDS
        self.assertTrue(lx <= gx0 and ly <= gy0 and hx >= gx1 and hy >= gy1)
        # whole sectors of 3 x 3 chunks of 256 units; at most 64 sector files + the frame file per folder
        self.assertEqual(((hx - lx) % 768, (hy - ly) % 768), (0, 0))
        self.assertLessEqual(((hx - lx) // 768) * ((hy - ly) // 768) + 1, 72)

    def test_seyda_and_balmora_frames_do_not_overlap(self):
        from chim.areas import area_problems
        self.assertEqual(area_problems(['seyda', 'balmora']), [])

    def test_ground_covers_every_tile_once_and_keeps_the_scene_triangles(self):
        from chim.ground import TriangleGround
        from prepare_quake import GROUND_BOUNDS, town_ground_triangles
        g = grids()
        low, high = seyda.frame_box()
        tris = seyda.ground_triangles(g, low, high)
        size = ((high[0] - low[0]) // 128, (high[1] - low[1]) // 128)
        ground = TriangleGround(tris, 128, low, size)       # raises on a tile without triangles
        inside = [(t, m) for t, m in town_ground_triangles(g)]
        self.assertEqual(tris[:len(inside)], [(t, int(m)) for t, m in inside])
        # every tile's triangles tile it exactly (area), none crosses a tile edge
        for (i, j), items in ground.tiles.items():
            x0, y0 = low[0] + i * 128, low[1] + j * 128
            area = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
                       for (a, b, c), _ in items)
            self.assertAlmostEqual(area, 128 * 128, places=3, msg=(i, j))
            for tri, _ in items:
                for p in tri:
                    self.assertTrue(x0 - 1e-6 <= p[0] <= x0 + 128 + 1e-6 and y0 - 1e-6 <= p[1] <= y0 + 128 + 1e-6)
        # the port's fine 32-unit patch is kept (prepare_quake.town_ground_triangles)
        port = ground.tile_list(*ground.clamp_tile(64, 320))
        self.assertEqual(len(port), 32)
        (gx0, gy0), _ = GROUND_BOUNDS
        self.assertLess(low[0], gx0 + 1)



class StoryHiddenTests(unittest.TestCase):
    """Format 0.5: a placement the opening story hides carries FLAG_STORY_HIDDEN (the legacy
    aw_story_hidden key), checked by the validator against the source manifest."""

    def test_flag_round_trips_and_the_validator_checks_it(self):
        import tempfile
        from chim import format as F
        from chim.validate import validate
        from test_chim_format import fixture
        with tempfile.TemporaryDirectory() as tmp:
            from unittest import mock
            from chim import build as CB
            original = CB.frame_input

            def hide_13(**kw):
                for ref in kw['references']:
                    if ref['number'] == 13:
                        ref['_story_hidden'] = True
                return original(**kw)
            with mock.patch.object(CB, 'frame_input', side_effect=hide_13):
                _, source = fixture(Path(tmp))
            fails, world = validate(tmp, dict(source, story_hidden=[13]))
            self.assertEqual(fails, [])
            flags = {r['ref']: r['flags'] for c in world['chunks'] for r in c['records']}
            self.assertTrue(flags[13] & F.FLAG_STORY_HIDDEN)
            self.assertFalse(any(v & F.FLAG_STORY_HIDDEN for k, v in flags.items() if k != 13))
            fails, _ = validate(tmp, dict(source, story_hidden=[]))
            self.assertTrue(any('story-hidden' in f for f in fails))

    def test_a_model_with_an_empty_own_profile_builds(self):
        # the tutorial barrel's profile is static_lod.rock_profile's {} (regression: KeyError)
        import tempfile
        from chim.validate import validate
        from test_chim_format import fixture
        with tempfile.TemporaryDirectory() as tmp:
            _, source = fixture(Path(tmp), own_profiles=True)
            self.assertEqual(validate(tmp, source)[0], [])

    def test_opening_references_are_one_reading_of_the_master(self):
        import inspect
        import prepare_opening_refs as O
        self.assertIn('opening_references(data_files)', inspect.getsource(O.prepare))
        self.assertIn('opening_references', inspect.getsource(seyda.prepare_area))


if __name__ == '__main__':
    unittest.main()
