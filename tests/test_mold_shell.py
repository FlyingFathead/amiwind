"""Distant outer-mold shells on synthetic meshes only (no game data)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

HAVE = all(importlib.util.find_spec(n) for n in ('numpy', 'scipy'))
if HAVE:
    import numpy as np
    import mold_shell as ms


def box(lo, hi):
    """12 outward triangles of an axis-aligned box."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris += [(p[a], p[b], p[c]), (p[a], p[c], p[d])]
    return np.array(tris)


def boxes(*specs):
    return np.concatenate([box(lo, hi) for lo, hi in specs])


def house(door_width, door_height=14, size=(60, 40, 30), wall=2):
    """Hollow house with walls, roof and floor; one door in the front (y=0) wall."""
    sx, sy, sz = size
    cx = sx / 2
    return boxes(((0, 0, 0), (sx, sy, wall)), ((0, 0, sz - wall), (sx, sy, sz)),
                 ((0, 0, 0), (wall, sy, sz)), ((sx - wall, 0, 0), (sx, sy, sz)),
                 ((0, sy - wall, 0), (sx, sy, sz)),
                 ((0, 0, 0), (cx - door_width / 2, wall, sz)), ((cx + door_width / 2, 0, 0), (sx, wall, sz)),
                 ((cx - door_width / 2, 0, door_height), (cx + door_width / 2, wall, sz)))


def covered(tris, direction, point, pixel=0.5):
    """Is the projection of point along direction inside the triangles' silhouette?"""
    u, v, _ = ms._basis(direction)
    lo = np.array([min((tris.reshape(-1, 3) @ u).min(), point @ u), min((tris.reshape(-1, 3) @ v).min(), point @ v)]) - 2
    hi = np.array([max((tris.reshape(-1, 3) @ u).max(), point @ u), max((tris.reshape(-1, 3) @ v).max(), point @ v)]) + 2
    shape = tuple(int(x) for x in np.ceil((hi - lo) / pixel) + 1)
    proj = np.stack([(tris @ u - lo[0]) / pixel, (tris @ v - lo[1]) / pixel], -1)
    mask, _ = ms.raster(proj, shape)
    i, j = int((point @ u - lo[0]) / pixel), int((point @ v - lo[1]) / pixel)
    return bool(mask[i, j])


@unittest.skipUnless(HAVE, 'numpy and scipy are build dependencies')
class MoldShellTests(unittest.TestCase):
    def test_closed_box_stays_a_box(self):
        tris = box((0, 0, 0), (40, 30, 20))
        s = ms.build_shell(tris, cell=2, faces=24, keep_opening=8)
        r = s['report']
        self.assertTrue(r['closed'])
        self.assertLessEqual(r['shell_triangles'], 24)
        self.assertLessEqual(r['deviation']['hausdorff'], 2.0)
        self.assertLess(r['silhouette']['worst_area_error'], 0.1)
        self.assertLessEqual(r['roofline']['max_dz'], 2.0)
        self.assertEqual(r['openings']['plugs'], [])

    def test_small_door_is_sealed_and_reported(self):
        tris = house(door_width=8)
        s = ms.build_shell(tris, cell=2, faces=48, keep_opening=16, report_width=6)
        r = s['report']
        self.assertTrue(r['closed'])
        self.assertLessEqual(r['shell_triangles'], 48)
        self.assertEqual(r['openings']['max_sealable_width'], 15)
        widths = [p['width'] for p in r['openings']['plugs']]
        self.assertTrue(any(6 <= w <= 12 for w in widths), widths)
        self.assertTrue(all(w <= 16 for w in widths), widths)
        doors = [o for o in r['openings']['openings'] if o['width'] >= 6]
        self.assertEqual(len(doors), 1, r['openings']['openings'])
        self.assertAlmostEqual(doors[0]['centre'][0], 30, delta=3)
        self.assertTrue(r['openings']['cavities'])
        self.assertGreater(r['openings']['cavities'][0]['volume'], 0.5 * 56 * 36 * 26)
        door = np.array([[30.0, 1.0, 8.0]])  # middle of the doorway
        self.assertGreater(ms.closest_points(door, tris)[0][0], 3.5)
        self.assertLessEqual(ms.closest_points(door, ms.mesh_triangles(s['vertices'], s['faces']))[0][0], 2.0)

    def test_wide_passage_is_kept(self):
        tris = boxes(((0, 0, 0), (10, 10, 40)), ((50, 0, 0), (60, 10, 40)), ((0, 0, 40), (60, 10, 50)))
        s = ms.build_shell(tris, cell=2, faces=96, keep_opening=16)
        r = s['report']
        self.assertTrue(r['closed'])
        self.assertTrue(all(p['width'] <= 16 for p in r['openings']['plugs']))
        shell = ms.mesh_triangles(s['vertices'], s['faces'])
        self.assertFalse(covered(shell, (0, 1, 0), np.array([30.0, 5.0, 20.0])))
        self.assertTrue(covered(shell, (0, 1, 0), np.array([5.0, 5.0, 20.0])))

    def test_courtyard_kept_above_threshold_and_sealed_below(self):
        ring = boxes(((0, 0, 0), (80, 20, 20)), ((0, 60, 0), (80, 80, 20)),
                     ((0, 0, 0), (20, 80, 20)), ((60, 0, 0), (80, 80, 20)))
        open_yard = ms.build_shell(ring, cell=2, faces=96, keep_opening=16)
        centre = np.array([40.0, 40.0, 10.0])
        shell = ms.mesh_triangles(open_yard['vertices'], open_yard['faces'])
        self.assertFalse(covered(shell, (0, 0, -1), centre))
        narrow = boxes(((0, 0, 0), (60, 20, 20)), ((0, 40, 0), (60, 60, 20)),
                       ((0, 0, 0), (20, 60, 20)), ((40, 0, 0), (60, 60, 20)))
        sealed = ms.build_shell(narrow, cell=2, faces=96, keep_opening=48)
        widths = [p['width'] for p in sealed['report']['openings']['plugs']]
        self.assertTrue(any(w >= 16 for w in widths), widths)
        shell = ms.mesh_triangles(sealed['vertices'], sealed['faces'])
        self.assertTrue(covered(shell, (0, 0, -1), np.array([30.0, 30.0, 10.0])))

    def test_materials_follow_the_facing_original_surface(self):
        tris = box((0, 0, 0), (40, 30, 20))
        n, _ = ms.triangle_normals(tris)
        mats = np.where(n[:, 2] > 0.5, 'roof', 'wall')
        s = ms.build_shell(tris, mats, cell=2, faces=24, keep_opening=8, measure=False)
        sn, _ = ms.triangle_normals(ms.mesh_triangles(s['vertices'], s['faces']))
        for normal, material, source in zip(sn, s['materials'], s['sources']):
            if normal[2] > 0.9:
                self.assertEqual(material, 'roof')
            elif abs(normal[2]) < 0.1:
                self.assertEqual(material, 'wall')
            self.assertEqual(mats[source], material)

    def test_diagonal_voxels_become_manifold(self):
        grid = np.zeros((6, 6, 6), bool)
        grid[2, 2, 2] = grid[3, 3, 2] = True
        grid[2, 2, 3] = grid[3, 3, 4] = True
        fixed, added = ms.make_manifold(grid)
        self.assertGreater(added, 0)
        v, f = ms.cuberille(fixed, np.zeros(3), 1.0)
        self.assertTrue(ms.edge_report(f)['closed'])
        v, f = ms.cuberille(grid, np.zeros(3), 1.0)
        self.assertFalse(ms.edge_report(f)['closed'])

    def test_cuberille_cube_merges_to_six_quads(self):
        grid = np.zeros((5, 5, 5), bool)
        grid[1:4, 1:4, 1:4] = True
        v, f = ms.cuberille(grid, np.zeros(3), 2.0)
        self.assertTrue(ms.edge_report(f)['closed'])
        self.assertEqual(ms.edge_report(f)['euler'], 2)
        v, f, method = ms.simplify(v, f, 12)
        self.assertLessEqual(len(f), 12)
        polys = ms.merge_coplanar(v, f, ['m'] * len(f))
        self.assertEqual(len(polys), 6)
        self.assertTrue(all(len(p[0]) == 4 for p in polys))

    def test_cluster_fallback_meets_budget(self):
        tris = house(door_width=8)
        s = ms.build_shell(tris, cell=2, faces=40, keep_opening=16, method='cluster', measure=False)
        self.assertEqual(s['report']['method'], 'cluster')
        self.assertLessEqual(s['report']['shell_triangles'], 40)
        self.assertGreater(s['report']['shell_triangles'], 0)

    def test_deterministic(self):
        tris = house(door_width=8)
        a = ms.build_shell(tris, cell=2, faces=48, keep_opening=16, measure=False)
        b = ms.build_shell(tris, cell=2, faces=48, keep_opening=16, measure=False)
        self.assertTrue(np.array_equal(a['vertices'], b['vertices']))
        self.assertTrue(np.array_equal(a['faces'], b['faces']))
        self.assertEqual(a['materials'], b['materials'])

    def test_closest_points_plane_and_edge(self):
        tri = np.array([[[0, 0, 0], [10, 0, 0], [0, 10, 0]]], float)
        d, i, p = ms.closest_points(np.array([[2, 2, 5], [-3, -4, 0]], float), tri)
        self.assertAlmostEqual(d[0], 5)
        self.assertAlmostEqual(d[1], 5)
        self.assertTrue(np.allclose(p[0], [2, 2, 0]))

    def test_quake_extent_split_count(self):
        quad = np.array([[0, 0, 0], [600, 0, 0], [600, 0, 10], [0, 0, 10]], float)
        axes = np.array([[1, 0, 0, 0], [0, 0, 1, 0]], float)
        self.assertEqual(ms.quake_face_count([quad], [axes]), 3)

    def test_budget_choice_and_screen_error(self):
        tris = boxes(((0, 0, 0), (60, 40, 20)), ((0, 0, 20), (30, 40, 40)), ((0, 0, 40), (15, 20, 60)))
        shells = ms.build_shells(tris, cell=2, budgets=(12, 24, 48, 96), keep_opening=16)
        reports = {b: s['report'] for b, s in shells.items()}
        budget, met = ms.pick_budget(reports, 4.0, 0.05)
        self.assertTrue(met)
        self.assertLessEqual(reports[budget]['silhouette']['worst_max_error'], 4.0)
        smaller = [b for b in reports if b < budget]
        for b in smaller:
            sil = reports[b]['silhouette']
            self.assertTrue(sil['worst_max_error'] > 4.0 or sil['mean_area_error'] > 0.05)
        self.assertEqual(ms.pick_budget(reports, 0.0, 0.0), (96, False))
        self.assertAlmostEqual(ms.screen_error(10, 160), 10.0)
        self.assertIn('p95_dz', reports[budget]['roofline'])

    def test_obj_round_trip_and_cli_report(self):
        tris = box((0, 0, 0), (20, 20, 20))
        with tempfile.TemporaryDirectory() as tmp:
            src, out, rep = Path(tmp, 'in.obj'), Path(tmp, 'out.obj'), Path(tmp, 'r.json')
            ms.write_obj(src, tris.reshape(-1, 3), np.arange(len(tris) * 3).reshape(-1, 3), ['stone'] * len(tris))
            self.assertEqual(ms.main([str(src), str(out), '--cell', '2', '--faces', '12',
                                      '--keep-opening', '8', '--report', str(rep)]), 0)
            v, f, mats = ms.read_obj(out)
            self.assertLessEqual(len(f), 12)
            self.assertEqual(set(mats), {'stone'})
            report = json.loads(rep.read_text(encoding='utf-8'))
            self.assertTrue(report['closed'])
            self.assertNotIn(b'\r', out.read_bytes())


if __name__ == '__main__':
    unittest.main()
