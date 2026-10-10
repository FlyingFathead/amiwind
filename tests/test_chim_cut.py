# SPDX-License-Identifier: GPL-3.0-only
"""chim.cut, the large-model cut (CHIM-ARENA-MEMORY-33): a placement wider than the cut threshold becomes
one model per chunk. Faces keep their area and texture coordinates, collision keeps its solid, and a world
built with the cut validates and owns every piece in its own chunk."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import cut as C  # noqa: E402


def box_faces(lo, hi):
    """The six faces of a box, counter-clockwise from outside, with a planar texture mapping."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    quads = [((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (0, 0, -1)),
             ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
             ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)),
             ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (0, 1, 0)),
             ((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (-1, 0, 0)),
             ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0))]
    ax = np.array([[0.5, 0.0], [0.0, 0.5], [0.25, 0.25]])
    return [(np.array(q[:4], float), np.array(q[4], float), ax, np.array([3.0, 7.0]), 0) for q in quads]


def inside(parts, p):
    from scipy.spatial import ConvexHull
    for points, *_ in parts:
        eq = ConvexHull(points).equations
        if np.all(eq[:, :3] @ p + eq[:, 3] < -1e-6):
            return True
    return False


class CutGeometryTests(unittest.TestCase):
    LOW, GRAIN, NX, NY = (-512.0, -512.0), 256.0, 4, 4

    def model(self):
        surfaces = box_faces((-300, -40, 0), (300, 40, 50))          # 600 x 80 x 50: crosses three lines
        parts = [(np.array([[x, y, z] for x in (-300, 0) for y in (-40, 40) for z in (0, 50)], float), None, [], 0.),
                 (np.array([[x, y, z] for x in (0, 300) for y in (-40, 40) for z in (0, 50)], float), None, [], 0.)]
        return surfaces, parts

    MODE = 'clip'

    def cut(self, origin=(10.0, -20.0, 5.0), yaw=30.0):
        s, p = self.model()
        return C.cut_pieces(s, p, origin, yaw, self.LOW, self.GRAIN, self.NX, self.NY, self.MODE), s, p

    def test_faces_keep_their_area(self):
        pieces, surfaces, _ = self.cut()
        before = sum(C.area(list(q)) for q, *_ in surfaces)
        after = sum(C.area(list(q)) for surfs, _, _ in pieces.values() for q, *_ in surfs)
        self.assertAlmostEqual(before, after, places=3)
        self.assertGreater(len(pieces), 1)

    def test_every_piece_lies_in_its_chunk(self):
        pieces, _, _ = self.cut()
        for (cx, cy), (surfs, parts, po) in pieces.items():
            x0, y0 = self.LOW[0] + cx * self.GRAIN, self.LOW[1] + cy * self.GRAIN
            self.assertEqual((po[0], po[1]), (x0 + self.GRAIN / 2, y0 + self.GRAIN / 2))
            for q, *_ in surfs:
                f = np.asarray(q) + po
                self.assertTrue(np.all(f[:, 0] >= x0 - 1e-6) and np.all(f[:, 0] <= x0 + self.GRAIN + 1e-6))
                self.assertTrue(np.all(f[:, 1] >= y0 - 1e-6) and np.all(f[:, 1] <= y0 + self.GRAIN + 1e-6))

    def test_texture_coordinates_are_unchanged(self):
        origin, yaw = np.array((10.0, -20.0, 5.0)), 30.0
        pieces, surfaces, _ = self.cut(tuple(origin), yaw)
        R = C.rotation(yaw)
        ax, off = surfaces[0][2], surfaces[0][3]
        for surfs, _, po in pieces.values():
            for q, n, axn, offn, *_ in surfs:
                for v in q:
                    model_point = R.T @ (np.asarray(v) + po - origin)
                    np.testing.assert_allclose(np.asarray(v) @ axn + offn, model_point @ ax + off, atol=1e-6)

    def test_collision_solid_is_unchanged(self):
        origin, yaw = np.array((10.0, -20.0, 5.0)), 30.0
        pieces, _, parts = self.cut(tuple(origin), yaw)
        R = C.rotation(yaw)
        moved = [(np.asarray(pts) @ R.T + origin,) for pts, *_ in parts]
        cut = [(np.asarray(pts) + po,) for _, prts, po in pieces.values() for pts, *_ in prts]
        rng = np.random.default_rng(3)
        for p in rng.uniform((-400, -400, -20), (400, 400, 80), (3000, 3)):
            self.assertEqual(inside(moved, p), inside(cut, p), p)

    def test_yaw_matches_the_engine(self):
        # a point on the model's x axis lands at angle yaw in the frame (Quake AngleVectors)
        R = C.rotation(90.0)
        np.testing.assert_allclose(R @ np.array([1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1e-9)

    def test_clip_piece_inside_outside_and_split(self):
        cube = np.array([[x, y, z] for x in (0, 10) for y in (0, 10) for z in (0, 10)], float)
        self.assertIs(C.clip_piece(cube, -5, -5, 20, 20), cube)
        self.assertIsNone(C.clip_piece(cube, 20, 20, 30, 30))
        half = C.clip_piece(cube, 0, 0, 5, 10)
        np.testing.assert_allclose(half.max(axis=0), [5, 10, 10])


class PartitionGeometryTests(CutGeometryTests):
    """The default mode: whole faces and whole convex pieces, each in the chunk holding its centre."""
    MODE = 'partition'

    def test_every_piece_lies_in_its_chunk(self):
        pieces, _, _ = self.cut()
        for (cx, cy), (surfs, parts, po) in pieces.items():
            x0, y0 = self.LOW[0] + cx * self.GRAIN, self.LOW[1] + cy * self.GRAIN
            for q, *_ in surfs:
                c = (np.asarray(q).min(axis=0) + np.asarray(q).max(axis=0)) / 2 + po
                self.assertTrue(x0 - 1e-6 <= c[0] <= x0 + self.GRAIN + 1e-6 and y0 - 1e-6 <= c[1] <= y0 + self.GRAIN + 1e-6)

    def test_the_polygons_are_the_models_own(self):
        origin, yaw = np.array((10.0, -20.0, 5.0)), 30.0
        pieces, surfaces, _ = self.cut(tuple(origin), yaw)
        R = C.rotation(yaw)
        want = sorted(tuple(np.round((np.asarray(q) @ R.T + origin).ravel(), 4)) for q, *_ in surfaces)
        got = sorted(tuple(np.round((np.asarray(q) + po).ravel(), 4)) for surfs, _, po in pieces.values()
                     for q, *_ in surfs)
        self.assertEqual(want, got)

    def test_clip_piece_inside_outside_and_split(self):
        pass


class TileTests(unittest.TestCase):
    """Mode 'tiles' (default): the model is cut once in its own frame; tiles are shared by its placements."""

    def test_tiles_keep_the_models_polygons_and_texture_coordinates(self):
        surfaces = box_faces((-300, -40, 0), (300, 40, 50))
        parts = [(np.array([[x, y, z] for x in (-300, 0) for y in (-40, 40) for z in (0, 50)], float), None, [], 0.)]
        tiles = C.model_tiles(surfaces, parts, 256.0)
        self.assertGreater(len(tiles), 1)
        want = sorted(tuple(np.round(np.asarray(q).ravel(), 4)) for q, *_ in surfaces)
        got = sorted(tuple(np.round((np.asarray(q) + c).ravel(), 4)) for surfs, _, c in tiles.values() for q, *_ in surfs)
        self.assertEqual(want, got)
        ax, off = surfaces[0][2], surfaces[0][3]
        for surfs, _, c in tiles.values():
            for q, n, axn, offn, *_ in surfs:
                for v in q:
                    np.testing.assert_allclose(np.asarray(v) @ axn + offn, (np.asarray(v) + c) @ ax + off, atol=1e-6)
        self.assertEqual(sum(len(p) for _, p, _ in tiles.values()), 1)


class CutWorldTests(unittest.TestCase):
    """A fixture world built with a low cut threshold: the large box (ref 12) is cut and the world
    validates; with cut_models_over 0 nothing is cut (the earlier form)."""

    def build(self, cut_over):
        from test_chim_format import fixture
        from chim.validate import validate
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / 'w'
        fixture(out, settings={'grain': 256, 'sector_chunks': 2, 'cut_models_over': cut_over}, large_size=(300, 64))
        fails, world = validate(out)
        self.assertFalse(fails, fails[:3])
        return world

    def test_cut_world_validates_and_owns_pieces_in_their_chunks(self):
        whole = self.build(0)
        cut = self.build(64)
        names = lambda w: [m['name'] for m in w['models']]  # noqa: E731
        self.assertFalse([n for n in names(whole) if '@tile' in n])
        pieces = [n for n in names(cut) if '@tile' in n]
        self.assertTrue(pieces)
        refs = [r['ref'] for _, _, chunks in cut['frames'] for c in chunks for r in c['owned']]
        self.assertEqual(len(refs), len(set(refs)))         # placement numbers stay unique
        sources = [C.source_ref(r) for r in refs]
        self.assertGreater(len(sources), len(set(sources)))  # one placement became several owned pieces
        whole_refs = {r['ref'] for _, _, chunks in whole['frames'] for c in chunks for r in c['owned']}
        self.assertEqual(set(sources), whole_refs)          # the same placements, mapped back
        for _, frame, chunks in cut['frames']:
            for c in chunks:
                for r in c['owned']:
                    if r['ref'] != C.source_ref(r['ref']):
                        self.assertEqual(r['owner'], c['index'])

    def test_a_cut_hollow_house_still_hides_what_is_behind_it(self):
        # the first piece carries the whole shell's solid columns (CHIM-PVS-HOLLOW-33)
        from test_chim_format import fixture
        rows = [{'ref': 1, 'cell': (0, 0), 'origin': (0.0, 0.0, 0.0), 'yaw': 0.0, 'variant': 'large'},
                {'ref': 2, 'cell': (0, 0), 'origin': (-460.0, 40.0, 0.0), 'yaw': 0.0, 'variant': 'small'},
                {'ref': 3, 'cell': (0, 0), 'origin': (460.0, 40.0, 0.0), 'yaw': 0.0, 'variant': 'small'}]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        receipt, _ = fixture(Path(tmp.name), rows, hollow_large=True, heights_of=lambda x, y: 4.0 + 0 * x,
                             large_size=(60, 300, 500), settings={'grain': 256, 'sector_chunks': 2, 'cut_models_over': 512})
        self.assertGreater(len(receipt['placements'] if isinstance(receipt['placements'], list) else range(receipt['placements'])), 3)
        self.assertGreater(receipt['visibility']['placements_blocked'], 0)

    def test_piece_numbers(self):
        self.assertEqual(C.source_ref(C.piece_ref(41499, 3)), 41499)
        self.assertEqual(C.source_ref(41499), 41499)
        with self.assertRaises(ValueError):
            C.piece_ref(41499, 128)


class DetailBudgetTests(unittest.TestCase):
    def test_named_budget_and_default_none(self):
        from chim.build import detail_budget
        self.assertEqual(detail_budget(None), {})
        vivec = detail_budget('vivec')
        self.assertEqual(vivec['meshes/x/ex_v_vivecstatue_02.nif'], 1200)
        # the owner-approved deep budget: every 'vivec-wide' mesh, at or below its 'vivec-wide' target
        wide, deep = detail_budget('vivec-wide'), detail_budget('vivec-deep')
        self.assertTrue(set(wide) <= set(deep))
        self.assertTrue(all(deep[k] <= wide[k] for k in wide))
        self.assertEqual((deep['meshes/x/ex_v_vivecstatue_02.nif'], deep['meshes/n/ingred_bc_coda_flower.nif']),
                         (900, 150))
        with self.assertRaises(ValueError):
            detail_budget('nowhere')


class ReducerOptionTests(unittest.TestCase):
    def test_border_lock_keeps_the_open_rim_and_defaults_are_unchanged(self):
        from static_lod import reduce_mesh
        # an open, curved sheet: 16 x 16 quads, one material, uv in columns 3-4
        n = 16
        verts, faces = [], []
        for j in range(n + 1):
            for i in range(n + 1):
                verts.append([i, j, 0.05 * ((i - n / 2) ** 2 + (j - n / 2) ** 2), i / n, j / n])
        for j in range(n):
            for i in range(n):
                a, b, c, d = j * (n + 1) + i, j * (n + 1) + i + 1, (j + 1) * (n + 1) + i + 1, (j + 1) * (n + 1) + i
                faces += [[a, b, c, 0], [a, c, d, 0]]
        v = np.array([[*p[:3], *p[3:5], 1.0, 1.0, 1.0] for p in verts], float)
        f = np.array(faces)
        plain_v, plain_f, _ = reduce_mesh(v, f, 0.25)
        again_v, again_f, _ = reduce_mesh(v, f, 0.25, (), False, agg=7.0, preserve_border=False)
        np.testing.assert_array_equal(plain_v, again_v)                    # defaults: the original call
        locked_v, locked_f, _ = reduce_mesh(v, f, 0.25, preserve_border=True)
        rim = {(x, y) for x in range(n + 1) for y in range(n + 1) if x in (0, n) or y in (0, n)}
        corners = {(0, 0), (0, n), (n, 0), (n, n)}
        kept = {(round(p[0]), round(p[1])) for p in locked_v[:, :3] if abs(p[0] - round(p[0])) < 1e-6 and abs(p[1] - round(p[1])) < 1e-6}
        self.assertTrue(corners <= kept)
        self.assertGreaterEqual(len(rim & kept), len(rim) // 2)


if __name__ == '__main__':
    unittest.main()
