# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM/legacy border fixes (docs/chim/STITCH_AUDIT.md).

CHIM-STITCH-SHORELINE-36: a town frame's ground goes through the legacy region maps' own
triangulation (prepare_world_regions.terrain_triangles: 32-unit samples where land and water flip),
so both sides of a handover meet without a step; only the chunks holding a refined tile change.
CHIM-FAR-BAND-GAP-36: a handoff row whose core lies closer than draw distance + 32 to the frame's
ground edge is refused unless it selects the inset method by name (the Arena); a CHIMport block owns
its cell box and carries a terrain-only margin.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_chim_format import LOW, SPAN, STEP, ROWS, fixture, height, material  # noqa: E402


def sampler(x, y):
    return float(height(x, y)), 0


def grid_materials():
    xs = range(int(LOW[0]), int(LOW[0]) + SPAN[0], STEP)
    ys = range(int(LOW[1]), int(LOW[1]) + SPAN[1], STEP)
    return [[material(x + STEP / 2, y + STEP / 2) for x in xs] for y in ys]


def shore_ground():
    from chim.build import shoreline_ground
    high = (LOW[0] + SPAN[0], LOW[1] + SPAN[1])
    return shoreline_ground(sampler, grid_materials(), LOW, high, STEP)


class ShorelineGroundTests(unittest.TestCase):
    def test_the_legacy_triangulation_tile_by_tile(self):
        from prepare_world_regions import Terrain, terrain_triangles
        g = shore_ground()
        self.assertTrue(g.refined, 'the fixture ground crosses the water level')
        self.assertLess(len(g.refined), g.size[0] * g.size[1])

        class Legacy(Terrain):          # the legacy maps' sampler over the same heights
            def __init__(self):
                pass

            def sample(self, x, y):
                return sampler(x, y)
        legacy = Legacy()
        mats = grid_materials()
        for j in range(g.size[1]):
            for i in range(g.size[0]):
                x, y = int(LOW[0]) + i * STEP, int(LOW[1]) + j * STEP
                want = [[[float(v) for v in p] for p in t] for t in terrain_triangles(legacy, x, y)]
                got = g.tile_list(i, j)
                self.assertEqual([[list(p) for p in t] for t, _ in got], want, (i, j))
                self.assertEqual({m for _, m in got}, {mats[j][i]})
                self.assertEqual((i, j) in g.refined, len(got) != 2, (i, j))
                if (i, j) not in g.refined:
                    c = [[x, y, height(x, y)], [x + STEP, y, height(x + STEP, y)],
                         [x + STEP, y + STEP, height(x + STEP, y + STEP)], [x, y + STEP, height(x, y + STEP)]]
                    c = [[float(v) for v in p] for p in c]
                    self.assertEqual([[list(p) for p in t] for t, _ in got], [[c[0], c[1], c[2]], [c[0], c[2], c[3]]])


class HybridFrameTests(unittest.TestCase):
    """A frame with the corner grid and shoreline tiles: chunks whose collision box holds a refined
    tile take the triangles, every other chunk is byte-identical to the plain grid's (unit reused)."""

    @classmethod
    def setUpClass(cls):
        from chim.validate import validate
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ground = shore_ground()
        out = {}
        for name, ground in (('grid', None), ('shore', cls.ground)):
            path = Path(cls.tmp.name) / name
            receipt, source = fixture(path, placements=ROWS, ground=ground)
            fails, world = validate(str(path), source)
            out[name] = (fails, world)
        cls.out = out

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_both_frames_validate(self):
        for name, (fails, _) in self.out.items():
            self.assertEqual(fails, [], name)

    def test_only_chunks_near_a_refined_tile_change(self):
        g, per = self.ground, 256 // STEP
        n = SPAN[0] // 256
        grid = {(c['cx'], c['cy']): c['image'] for _, _, chunks in self.out['grid'][1]['frames'] for c in chunks}
        shore = {(c['cx'], c['cy']): c['image'] for _, _, chunks in self.out['shore'][1]['frames'] for c in chunks}
        self.assertEqual(set(grid), set(shore))
        changed = same = 0
        for (cx, cy) in sorted(grid):
            a, b = grid[cx, cy], shore[cx, cy]
            box = [(i, j) for j in range(max(0, cy * per - 1), min(n * per, (cy + 1) * per + 1))
                   for i in range(max(0, cx * per - 1), min(n * per, (cx + 1) * per + 1))]
            if any(t in g.refined for t in box):
                changed += 1
            else:
                self.assertEqual(a, b, (cx, cy))
                same += 1
        self.assertGreater(changed, 0)
        self.assertGreater(same, 0)


class SectorLayoutTests(unittest.TestCase):
    def test_large_frames_group_their_sectors_small_frames_keep_their_paths(self):
        from chim import format as F
        from chim.world import SECTOR_GROUP, sector_path
        self.assertEqual(sector_path(5, 64), 's05.ccs')           # every frame up to 8 x 8 sectors: unchanged
        self.assertEqual(sector_path(70, 71), 's70.ccs')
        paths = [sector_path(i, 100) for i in range(100)]        # 30 x 30 chunks of 3 x 3: 10 x 10 sectors
        self.assertEqual(paths[0], 'g0/s00.ccs')
        self.assertEqual(paths[99], 'g1/s99.ccs')
        groups = {}
        for p in paths:
            groups.setdefault(p.split('/')[0], []).append(p)
        self.assertTrue(all(len(v) <= min(SECTOR_GROUP, F.FFS_MAX_DIRECTORY_ENTRIES) for v in groups.values()))
        self.assertLessEqual(len(groups) + 1, F.FFS_MAX_DIRECTORY_ENTRIES)
        self.assertLessEqual(len('frames/x-07/y+02/' + paths[-1]), 31)    # index path limit


class ShorelineSwitchTests(unittest.TestCase):
    def test_default_on_and_off_selectable(self):
        import argparse
        from build import chim_stage_options
        from chim.build import SHORELINE_MODES
        self.assertEqual(SHORELINE_MODES, ('on', 'off'))
        self.assertEqual(chim_stage_options(argparse.Namespace(chim_terrain_shoreline='on')), [])
        self.assertEqual(chim_stage_options(argparse.Namespace(chim_terrain_shoreline='off')),
                         ['--terrain-shoreline', 'off'])
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        self.assertIn("'--terrain-shoreline', choices=('on', 'off'), default='on'", text)


class FarBandGateTests(unittest.TestCase):
    def settings(self, **kw):
        s = {'bounds': [[-3072, -3072], [3072, 3072]], 'draw_distance': 540, 'terrain_step': 128}
        s.update(kw)
        return s

    def test_inset_core_is_refused_unless_selected_by_name(self):
        from town_config import handoff_core, handoff_gap_problem
        self.assertIn('CHIM-FAR-BAND-GAP-36', handoff_gap_problem(self.settings(), 540))
        s = self.settings(handoff_core='inset')
        self.assertIsNone(handoff_gap_problem(s, 540))
        self.assertEqual(handoff_core(s), [[-2976, -2976], [2976, 2976]])

    def test_cell_box_core_with_a_terrain_margin(self):
        from town_config import frame_ground_bounds, handoff_core, handoff_gap_problem
        core = [[-3072, -3072], [3072, 3072]]
        s = self.settings(terrain_margin=768, handoff_core=core)
        self.assertEqual(frame_ground_bounds(s), [[-3840, -3840], [3840, 3840]])
        self.assertEqual(handoff_core(s), core)
        self.assertIsNone(handoff_gap_problem(s, 540))
        with self.assertRaisesRegex(ValueError, 'draw distance'):
            handoff_core(self.settings(terrain_margin=512, handoff_core=core))      # 512 < 540 + 32
        self.assertIsNotNone(handoff_gap_problem(self.settings(terrain_margin=256), 540))   # inset: 352 < 572
        with self.assertRaisesRegex(ValueError, 'terrain_margin'):
            frame_ground_bounds(self.settings(terrain_margin=100))

    def test_every_handoff_row_of_the_table_passes(self):
        from town_config import runtime_towns
        rows = {r['id']: r for r in runtime_towns() if r['handoff']}
        self.assertEqual(rows['bcoast_x7y2']['core'], [[-3072, -3072], [3072, 3072]])
        self.assertEqual(rows['vivec_arena']['core'], [[-1440, -1440], [1440, 1440]])   # inset kept (Arena)
        arena = json.loads((ROOT / 'config/vivec_arena.json').read_text(encoding='utf-8'))
        self.assertEqual(arena['handoff_core'], 'inset')

    def test_bcoast_frame_has_ground_up_to_the_fog_plane(self):
        from town_config import frame_ground_bounds, handoff_core, load_settings
        s = load_settings('bcoast_x7y2')
        core, (low, high) = handoff_core(s), frame_ground_bounds(s)
        for k in range(2):
            self.assertGreaterEqual(core[0][k] - low[k], s['draw_distance'] + 32)
            self.assertGreaterEqual(high[k] - core[1][k], s['draw_distance'] + 32)
            self.assertEqual((high[k] - low[k]) % 256, 0)     # whole chunks (grain 256)


if __name__ == '__main__':
    unittest.main()


class LavaTerrainDetailTests(unittest.TestCase):
    def test_elevated_pool_preserves_depression_and_coarse_boundary(self):
        from chim.build import shoreline_ground
        def sample(x, y):
            return (20.0 if 32 <= x <= 128 and 32 <= y <= 96 else 100.0), 0
        pool = {'hull': [[16,16],[112,16],[112,112],[16,112]], 'top':80}
        plain = shoreline_ground(sample, [[0,0]], (0,0), (256,128), 128)
        fixed = shoreline_ground(sample, [[0,0]], (0,0), (256,128), 128, [pool])
        self.assertEqual(plain.height(64,64), 100)
        self.assertEqual(fixed.height(64,64), 20)
        self.assertEqual(fixed.height(256,64), plain.height(256,64))
        self.assertEqual(fixed.refined, {(0,0),(1,0)})
        edges = []
        for tile in [(0,0),(1,0)]:
            edges.append({tuple(p) for tri, _ in fixed.tile_list(*tile)
                          for p in tri if p[0] == 128})
        self.assertEqual(edges[0], edges[1])
        self.assertIn((128.0,64.0,20.0), edges[0])
        no_shore = shoreline_ground(sample, [[0,0]], (0,0), (256,128), 128,
                                   [pool], shoreline=False)
        self.assertEqual(no_shore.rows(), fixed.rows())

    def test_no_pool_preserves_existing_triangle_bytes(self):
        from chim.build import shoreline_ground
        sample = lambda x,y: (100+x/16+y/32,0)
        old = shoreline_ground(sample, [[0]], (0,0), (128,128),128)
        explicit = shoreline_ground(sample, [[0]], (0,0), (128,128),128, [])
        self.assertEqual(old.rows(), explicit.rows())
        self.assertFalse(explicit.refined)
