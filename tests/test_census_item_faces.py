# SPDX-License-Identifier: GPL-3.0-only
"""The census office's item models that keep every drawn triangle (ITEM-AIM-UNDER-OTHERS-69, config/room-item-faces.json,
tools/prepare_census.py).

The converter's surface pass (mesh_geometry.surface_polygons) leaves out a triangle whose doubled area at the quarter
scale is under its floor. On the office's Iron Dagger that took the guard's ends: drawn at 0.67 of its width. A model
with an entry keeps those triangles, and the census stage refuses a kept model drawn smaller than its source. Synthetic
meshes only: the game data is not in the repository (the stage checks the real dagger at every build)."""
from pathlib import Path
import json
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import mesh_geometry  # noqa: E402
import prepare_census as pc  # noqa: E402
import prepare_mesh_bsp  # noqa: E402


def dagger():
    """A dagger-like mesh in original units (x y z u v; faces a b c material): a blade of two large triangles along y,
    and a guard across x made of small triangles, each under the surface floor at the quarter scale, out to x = +-5.1
    (the original's w_iron_dagger.nif guard)."""
    v = [(-1.3, 0, 0, 0, 0), (1.3, 0, 0, 1, 0), (1.3, 20, 0, 1, 1), (-1.3, 20, 0, 0, 1)]
    f = [(0, 1, 2, 0), (0, 2, 3, 0)]
    for side in (-1, 1):
        for k in range(4):        # the guard: 4 small triangles a side, each 0.95 x 0.8 original units
            x0 = side * (1.3 + .95 * k)
            x1 = side * (1.3 + .95 * (k + 1))
            base = len(v)
            v += [(x0, -.4, 0, 0, 0), (x1, -.4, 0, 1, 0), (x0, .4, 0, 0, 1)]
            f.append((base, base + 1, base + 2, 0) if side > 0 else (base, base + 2, base + 1, 0))
    return np.array(v, float), np.array(f, int)


def extent_x(polys):
    pts = np.concatenate([np.asarray(p, float) for p, *_ in polys])
    return float(pts[:, 0].min()), float(pts[:, 0].max())


class SurfaceFloor(unittest.TestCase):
    def test_the_floor_is_the_surface_pass_own(self):
        """SURFACE_FLOOR is mesh_geometry.surface_polygons' floor: a triangle just under it is left out there, one just
        over it is kept (doubled area at the quarter scale)."""
        def tri(doubled):      # a right triangle of legs a, a at the quarter scale: doubled area a * a
            a = (doubled ** .5) * 4
            return np.array([(0, 0, 0, 0, 0), (a, 0, 0, 1, 0), (0, a, 0, 0, 1)], float), np.array([(0, 1, 2, 0)])
        v, f = tri(pc.SURFACE_FLOOR * .98)
        self.assertEqual(mesh_geometry.surface_polygons(v, f), [])
        self.assertEqual(len(pc.small_polygons(v, f)), 1)
        v, f = tri(pc.SURFACE_FLOOR * 1.02)
        self.assertEqual(len(mesh_geometry.surface_polygons(v, f)), 1)
        self.assertEqual(pc.small_polygons(v, f), [])


class DaggerGuard(unittest.TestCase):
    def test_the_surface_pass_alone_loses_the_guard(self):
        """Today's rule (the old behaviour): the guard's small triangles are not drawn, the dagger narrows to its blade."""
        v, f = dagger()
        low, high = extent_x(mesh_geometry.surface_polygons(v, f))
        self.assertAlmostEqual(high - low, 2.6 * .25, places=3)

    def test_the_kept_model_is_drawn_at_its_source_width_and_area(self):
        """With the entry the guard is drawn: the drawn box and area are the source's (the census stage's own check)."""
        v, f = dagger()
        polys = list(mesh_geometry.surface_polygons(v, f)) + pc.small_polygons(v, f)
        low, high, area = pc.drawn_measure(polys)
        s_low, s_high, s_area = pc.source_measure(v, f)
        self.assertAlmostEqual(float(high[0] - low[0]), 10.2 * .25, places=3)
        np.testing.assert_allclose(high - low, s_high - s_low, atol=1e-6)
        self.assertAlmostEqual(area, s_area, places=6)
        self.assertEqual(len(pc.small_polygons(v, f)), 8)
        for poly, material, axes, offset, normal in pc.small_polygons(v, f):
            self.assertEqual(poly.shape, (3, 3))
            self.assertAlmostEqual(float(np.linalg.norm(normal)), 1., places=6)

    def test_the_kept_polygons_carry_the_texture_mapping(self):
        """Each kept triangle maps its own texture coordinates as the surface pass maps a triangle."""
        v, f = dagger()
        for (poly, material, axes, offset, normal), face in zip(pc.small_polygons(v, f), f[2:]):
            for corner, index in zip(poly, face[:3]):
                np.testing.assert_allclose(corner @ axes + offset, v[index, 3:5], atol=1e-6)


class Table(unittest.TestCase):
    def test_the_dagger_has_its_entry(self):
        entries = pc.room_item_faces('census')
        entry = entries['meshes/w/w_iron_dagger.nif']
        self.assertEqual(entry['cost'], {'before': 88, 'added': 118, 'total': 206})
        self.assertLessEqual(entry['cost']['added'], entry['extra_faces'])
        self.assertEqual(pc.room_item_faces('prison'), {})

    def test_a_bad_entry_is_refused(self):
        import tempfile
        good = {'room': 'census', 'model': 'meshes/w/x.nif', 'extra_faces': 4, 'reason': 'r',
                'cost': {'before': 1, 'added': 4, 'total': 5}, 'pi_check': 'pending'}
        for bad in ({'extra_faces': 0}, {'reason': ''}, {'cost': {'before': 1, 'added': 5, 'total': 6}},
                    {'cost': {'before': 1, 'added': 2, 'total': 4}}, {'pi_check': ''}, {'model': 'x.nif'}):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'faces.json'
                path.write_text(json.dumps({'schema': 1, 'entries': [dict(good, **bad)]}), encoding='utf-8')
                with self.assertRaises(ValueError, msg=bad):
                    pc.room_item_faces('census', path)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'faces.json'
            path.write_text(json.dumps({'schema': 1, 'entries': [good, good]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                pc.room_item_faces('census', path)

    def test_only_the_census_converter_reads_the_table(self):
        """The table keys the census stage alone: no other tool names it."""
        readers = [p.name for p in (ROOT / 'tools').rglob('*.py') if 'room-item-faces.json' in p.read_text(
            encoding='utf-8', errors='replace')]
        self.assertEqual(readers, ['prepare_census.py'])


class Scope(unittest.TestCase):
    def test_the_converter_hook_is_scoped(self):
        """prepare_mesh_bsp's ordered_map is replaced only inside the census conversion and passes other work on."""
        real = prepare_mesh_bsp.ordered_map
        with pc.items_keep_small_faces({'meshes/w/w_iron_dagger.nif': {'extra_faces': 1}}):
            self.assertIsNot(prepare_mesh_bsp.ordered_map, real)
            self.assertEqual(list(prepare_mesh_bsp.ordered_map(abs, [-1, -2], 1)), [1, 2])
        self.assertIs(prepare_mesh_bsp.ordered_map, real)
        with pc.items_keep_small_faces({}) as kept:
            self.assertIs(prepare_mesh_bsp.ordered_map, real)
            self.assertEqual(kept, {})


if __name__ == '__main__':
    unittest.main()
