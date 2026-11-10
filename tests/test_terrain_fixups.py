"""Hand-listed ground fix-up vertices of a CHIM town frame (chim.build terrain_fixups, insert_ground_vertex,
ground_check_failures, apply_terrain_fixups; BALMORA-GROUND-DENTS-51): synthetic grounds, no game data; and
Balmora's own list in config/balmora.json."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    sys.path.insert(0, str(p))
from chim.build import (FIXUP_CHECK_GRID, FIXUP_CHECK_TOLERANCE, apply_terrain_fixups, ground_check_failures,
                        insert_ground_vertex, original_surface, terrain_fixups)
from chim.ground import TriangleGround


def plain(corners, step=128, low=(0, 0), size=(2, 1), material=7):
    """A 2x1-tile ground of plain triangles 0-1-2, 0-2-3 from corner heights {(x, y): z}."""
    tris = []
    for j in range(size[1]):
        for i in range(size[0]):
            x, y = low[0] + i * step, low[1] + j * step
            c = [(x, y, corners[(x, y)]), (x + step, y, corners[(x + step, y)]),
                 (x + step, y + step, corners[(x + step, y + step)]), (x, y + step, corners[(x, y + step)])]
            tris.append(([c[0], c[1], c[2]], material))
            tris.append(([c[0], c[2], c[3]], material))
    return TriangleGround(tris, step, low, size)


def count(ground):
    return sum(len(rows) for rows in ground.tiles.values())


def edge_points(ground, x):
    return {p for rows in ground.tiles.values() for tri, _ in rows for p in tri if p[0] == x}


class InsertVertexTests(unittest.TestCase):
    def setUp(self):
        self.corners = {(0, 0): 0., (128, 0): 0., (256, 0): 100., (0, 128): 0., (128, 128): 0., (256, 128): 100.}

    def test_a_vertex_on_an_edge_splits_both_triangles_and_keeps_the_rest(self):
        ground = plain(self.corners)
        after, split = insert_ground_vertex(ground, (64, 64, 30.))      # on tile 0's diagonal
        self.assertEqual(split, 2)
        self.assertEqual(count(after), count(ground) + 2)
        self.assertEqual(after.tiles[(1, 0)], ground.tiles[(1, 0)])      # the other tile is untouched
        self.assertEqual(after.height(64, 64), 30.)
        for (x, y), z in self.corners.items():                          # the corners keep their heights
            self.assertEqual(after.height(x, y, near=(min(x, 255), min(y, 127))), z)
        self.assertEqual(after.step, ground.step)
        self.assertEqual((after.low, after.size), (ground.low, ground.size))

    def test_a_vertex_inside_a_triangle_splits_it_in_three(self):
        ground = plain(self.corners)
        after, split = insert_ground_vertex(ground, (96, 32, 12.))      # inside tile 0's lower triangle
        self.assertEqual(split, 1)
        self.assertEqual(count(after), count(ground) + 2)
        self.assertEqual(after.height(96, 32), 12.)
        self.assertEqual(after.height(32, 96), 0.)                      # the upper triangle stays

    def test_a_vertex_on_a_tile_edge_keeps_the_ground_closed(self):
        ground = plain(self.corners)
        after, split = insert_ground_vertex(ground, (128, 64, 0.))      # the edge both tiles share
        self.assertEqual(split, 2)
        self.assertEqual(count(after), count(ground) + 2)
        self.assertEqual(edge_points(after, 128), {(128., 0., 0.), (128., 64., 0.), (128., 128., 0.)})
        self.assertEqual(len(after.tiles[(0, 0)]), 3)
        self.assertEqual(len(after.tiles[(1, 0)]), 3)

    def test_the_vertex_lifts_a_sagging_edge_to_its_height(self):
        ground = plain(self.corners)
        self.assertEqual(ground.height(192, 64), 50.)                    # the coarse diagonal of tile 1
        after, _ = insert_ground_vertex(ground, (192, 64, 77.))
        self.assertEqual(after.height(192, 64), 77.)
        self.assertEqual(after.height(256, 64, near=(255, 64)), 100.)   # the edge to the corner is unchanged
        self.assertEqual(set(after.refined), set())


class CheckTests(unittest.TestCase):
    def test_the_original_surface_follows_the_parity_diagonals(self):
        h = lambda x, y: 10. if (x, y) == (32, 0) else 0.              # one raised sample
        self.assertEqual(original_surface(h, 32, 0), 10.)
        self.assertEqual(original_surface(h, 24, 8), 5.)                # even quad (0, 0), face 0-1-2 holds it
        self.assertEqual(original_surface(h, 8, 24), 0.)                # its face 0-2-3 does not
        self.assertEqual(original_surface(h, 40, 8), 5.)                # odd quad (1, 0), face 0-1-3 holds it
        self.assertEqual(original_surface(h, 56, 24), 0.)               # its face 1-2-3 does not
        self.assertEqual(original_surface(h, 8, 24, grid_origin=(32, 0)), 2.5)   # the same point, odd parity now

    def test_failures_name_every_point_outside_the_tolerance(self):
        ground = plain({(0, 0): 42., (128, 0): 42., (256, 0): 42., (0, 128): 0., (128, 128): 42., (256, 128): 42.})
        check = {'box': ((48., 80.), (64., 96.)), 'grid': 8., 'tolerance': 4.}
        failures = ground_check_failures(ground, lambda x, y: 42., check)
        self.assertEqual(len(failures), 9)
        self.assertIn('(48, 80): ground 31.50, original 42.00', failures)
        self.assertEqual(ground_check_failures(ground, lambda x, y: 42., {'box': ((128., 0.), (256., 128.)),
                                                                           'grid': 32., 'tolerance': 0.}), [])

    def test_apply_inserts_the_vertices_and_passes_the_check(self):
        ground = plain({(0, 0): 42., (128, 0): 42., (256, 0): 42., (0, 128): 0., (128, 128): 42., (256, 128): 42.})
        fixups = {'bug': 'TEST-1', 'vertices': [(32., 96., 42.)],
                  'check': {'box': ((48., 80.), (64., 96.)), 'grid': 8., 'tolerance': 4.}}
        after, record = apply_terrain_fixups(ground, fixups, lambda x, y: 42.)
        self.assertEqual(record['vertices'], 1)
        self.assertEqual(record['triangles_added'], 2)
        self.assertTrue(record['check'].startswith('box check passed'))
        self.assertEqual(count(after), count(ground) + 2)
        self.assertEqual(after.height(48, 80), 42.)

    def test_apply_refuses_a_drifted_height_and_a_failing_box(self):
        ground = plain({(0, 0): 42., (128, 0): 42., (256, 0): 42., (0, 128): 0., (128, 128): 42., (256, 128): 42.})
        with self.assertRaises(ValueError) as caught:
            apply_terrain_fixups(ground, {'bug': 'TEST-1', 'vertices': [(32., 96., 40.)], 'check': None},
                                 lambda x, y: 42.)
        self.assertIn('lists height 40 but the original LAND there is 42.00', str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            apply_terrain_fixups(ground, {'bug': 'TEST-1', 'vertices': [(200., 64., 42.)],
                                          'check': {'box': ((48., 80.), (64., 96.)), 'grid': 8., 'tolerance': 4.}},
                                 lambda x, y: 42.)
        self.assertIn('TEST-1: the frame ground misses the original surface by more than 4 at 9 points', str(caught.exception))


class ConfigTests(unittest.TestCase):
    LOW, HIGH = (-3840, -3840), (3840, 3840)

    def test_the_list_is_checked(self):
        self.assertIsNone(terrain_fixups({}, self.LOW, self.HIGH))
        good = {'terrain_fixups': {'bug': 'TEST-1', 'vertices': [[480, -256, 42.0]],
                                   'check': {'box': [[480, -400], [512, -160]]}}}
        parsed = terrain_fixups(good, self.LOW, self.HIGH)
        self.assertEqual(parsed['vertices'], [(480., -256., 42.)])
        self.assertEqual(parsed['check'], {'box': ((480., -400.), (512., -160.)), 'grid': FIXUP_CHECK_GRID,
                                           'tolerance': FIXUP_CHECK_TOLERANCE})
        self.assertIsNone(terrain_fixups({'terrain_fixups': {'bug': 'TEST-1', 'vertices': [[1, 2, 3]]}},
                                         self.LOW, self.HIGH)['check'])
        for bad in [[], {'vertices': [[1, 2, 3]]}, {'bug': '', 'vertices': [[1, 2, 3]]},
                    {'bug': 'T', 'vertices': []}, {'bug': 'T', 'vertices': [[1, 2]]},
                    {'bug': 'T', 'vertices': [[1, 2, 'x']]}, {'bug': 'T', 'vertices': [[1, 2, True]]},
                    {'bug': 'T', 'vertices': [[3840, 0, 1]]}, {'bug': 'T', 'vertices': [[1, 2, 3], [1, 2, 4]]},
                    {'bug': 'T', 'vertices': [[1, 2, 3]], 'check': {'box': [[0, 0], [0, 1]]}},
                    {'bug': 'T', 'vertices': [[1, 2, 3]], 'check': {'box': [[0, 0], [4000, 1]]}},
                    {'bug': 'T', 'vertices': [[1, 2, 3]], 'check': {'box': [[0, 0], [1, 1]], 'grid': 0}},
                    {'bug': 'T', 'vertices': [[1, 2, 3]], 'check': {'box': [[0, 0], [1, 1]], 'tolerance': -1}}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                terrain_fixups({'terrain_fixups': bad}, self.LOW, self.HIGH)

    def test_balmora_lists_the_canal_wall_vertices(self):
        from town_config import frame_ground_bounds
        settings = json.loads((ROOT / 'config/balmora.json').read_text(encoding='utf-8'))
        low, high = frame_ground_bounds(settings)
        parsed = terrain_fixups(settings, low, high)
        self.assertEqual(parsed['bug'], 'BALMORA-GROUND-DENTS-51')
        self.assertEqual(parsed['vertices'], [(480., -256., 42.), (480., -320., 42.), (488., -288., 42.),
                                              (480., -160., 38.), (488., -416., 42.)])
        self.assertEqual(parsed['check'], {'box': ((480., -480.), (512., -160.)), 'grid': 8., 'tolerance': 4.})
        # the whole register, archives included: a fixed bug rotates out of bugs.json (BALMORA-GROUND-DENTS-51 was seen
        # fixed in the v0.0.63 release check), and the fixup must still name a real entry
        import bug_register
        ids = {b['id'] for b in bug_register.load()}
        self.assertIn(parsed['bug'], ids)


if __name__ == '__main__':
    unittest.main()
