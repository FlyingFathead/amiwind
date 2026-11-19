# SPDX-License-Identifier: GPL-3.0-only
# Created by FlyingFathead a.k.a. Horstator. Thanks to ChaosWhisperer.
"""The kinds of the hand-made batches 001-004 (tools/hand_made_kinds.py; method 2, config/model-method-2.json;
MODEL-REDUCTION-BATCHES-67), on synthetic models only (no game data). The batches' own synthetic checks, as they map
to the builder: the profile corners cannot twist, a projected quad keeps its texture mapping, a closed profile is closed
and wound one way, a kept part cannot gain a cut, a tapered side panel bakes as its triangles map it, the simplifier
keeps borders, bounds and its output, the atlas keeps its gutters, a bounds change is fatal, and another source file
is not that model (the archive and ledger checks of the batches have no counterpart: the build reads the game's own
archives and keeps no ledger). Plus the builder's own: the picture's texels, the shipped rows and the intake rule."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import hand_made_kinds as H  # noqa: E402
import model_method2 as M  # noqa: E402


def gradient():
    y, x = np.mgrid[0:16, 0:16]
    rgb = np.stack([x * 16, y * 16, np.full_like(x, 128)], axis=-1).astype(np.uint8)
    return rgb, np.dstack([rgb, np.full((16, 16), 255, np.uint8)]) / 255


def cylinder():
    m, n = H.Model(), 12
    for j in range(4):
        for i in range(n):
            k = (i + 1) % n

            def p(ii, z):
                return [np.cos(ii * 2 * np.pi / n), np.sin(ii * 2 * np.pi / n), z]
            m.quad([p(i, j), p(k, j), p(k, j + 1), p(i, j + 1)],
                   [(i / n, j / 4), ((i + 1) / n, j / 4), ((i + 1) / n, (j + 1) / 4), (i / n, (j + 1) / 4)],
                   'm0', 'source_m0')
    return m


class BatchChecks(unittest.TestCase):
    def test_profile_corner_wrap_cannot_twist_body(self):
        a = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], float)
        b = a.copy()
        b[:, :2] *= .7
        b[:, 2] = 2
        b[0, 0] += .0001
        np.testing.assert_allclose(H.align_rings([a, np.roll(b, 1, axis=0)])[1], b)
        c = b.copy()
        c[:, :2] = c[:, :2] @ np.array([[.707, -.707], [.707, .707]])
        with self.assertRaisesRegex(ValueError, 'incompatible radial'):
            H.align_rings([a, c])

    def test_projected_quad_preserves_tapered_uv_mapping(self):
        m = H.Model()
        points = [[-1, -1, 0], [1, -1, 0], [2, -2, 1], [-2, -2, 1]]
        m.quad(points, [(0, 0), (1, 0), (1, 1), (0, 1)], 'm0')
        rgb, tex = gradient()
        image, missing = H.bake_quad(points, m, {'m0': tex}, [0, 1], 16, 1)
        np.testing.assert_array_equal(image, rgb)
        self.assertEqual(missing, 0)

    def test_closed_profile_caps_and_winding(self):
        m, n = H.Model(), 8
        rings = [np.array([[r * np.cos(i * 2 * np.pi / n), r * np.sin(i * 2 * np.pi / n), z] for i in range(n)])
                 for z, r in [(0, 1), (1, 2)]]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for i in range(n):
            k = (i + 1) % n
            m.quad([rings[0][i], rings[0][k], rings[1][k], rings[1][i]], uv, 'm0')
        for r in (rings[0][::-1], rings[1]):
            for i in range(1, n - 1):
                m.tri(r[[0, i, i + 1]], uv[:3], 'm0', 'shell')
        settings = dict(retain_components=[], rings=[dict(materials=['m0'], z=z, corners=8) for z in [0, 1]],
                        tile_size=12, supersample=1)
        tex = {'m0': np.tile(np.array([120, 90, 60, 255], float) / 255, (16, 16, 1))}
        result, atlas, report = H.profile_shell(m, tex, settings)
        topo = H.statistics(result)['global_topology']
        self.assertEqual(topo, dict(open_edges=0, nonmanifold_edges=0, same_direction_pairs=0, degenerate_triangles=0))
        self.assertEqual(len(result.faces), 28)
        self.assertEqual(atlas.shape, (64, 64, 3))

    def test_retained_component_cannot_cut_new_boundary(self):
        source, uv = H.Model(), [(0, 0), (1, 0), (0, 1)]
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
        for ids in ([0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]):
            source.tri(vertices[ids], uv, 'm0', 'handle')
        H.check_retained_boundaries(source, source, 'm0')
        partial = H.Model()
        for mat, ids, ui in source.faces[:3]:
            partial.tri(np.array(source.v)[ids], np.array(source.uv)[ui], mat, 'handle')
        with self.assertRaisesRegex(ValueError, 'new cut edges'):
            H.check_retained_boundaries(source, partial, 'm0')

    def test_tapered_bake_matches_triangle_uv_mapping(self):
        source = H.Model()
        source.quad([[-1, -1, 0], [1, -1, 0], [2, -2, 1], [-2, -2, 1]], [(0, 0), (1, 0), (1, 1), (0, 1)], 'm0')
        rgb, tex = gradient()
        recipe = dict(rings=[[0, 1], [1, 2]], panel_ring_pair=[0, 1], center_xy=[0, 0],
                      bake=dict(ray_offset=5, background_rgb=[0, 0, 0]))
        out = H.bake_side(0, np.array(source.v), np.array(source.uv), source.faces, {'m0': tex}, recipe, 16, 1)
        np.testing.assert_array_equal(out, rgb)

    def test_border_and_bounds(self):
        a = cylinder()
        v, uv = np.array(a.v), np.array(a.uv)
        p, f, t = H.simplify(v, uv, [(i, u) for _, i, u in a.faces], 40, 10)
        b = H.Model()
        for ids, uu in zip(f, t):
            b.tri(p[ids], uu, 'm0', 'source_m0')
        before, after, error = H.check_pair(a, b)
        self.assertLess(after['triangles'], before['triangles'])
        self.assertEqual(before['groups']['source_m0']['open_edges'], after['groups']['source_m0']['open_edges'])
        self.assertLess(error, 1e-5)
        for q in v[(v[:, 2] == 0) | (v[:, 2] == 4)]:
            self.assertIn(tuple(q), b.v)

    def test_determinism(self):
        a = cylinder()
        args = (np.array(a.v), np.array(a.uv), [(i, u) for _, i, u in a.faces], 40, 10)
        for x, y in zip(H.simplify(*args), H.simplify(*args)):
            np.testing.assert_array_equal(x, y)

    def test_atlas_gutters(self):
        for i in range(4):
            uv = np.array(H.tile_uv(i))
            self.assertTrue(np.all(uv > 0) and np.all(uv < 1))
            np.testing.assert_allclose(np.ptp(uv, axis=0), [28 / 64, 28 / 64])

    def test_bounds_failure_is_fatal(self):
        a, b = cylinder(), H.Model()
        for (m, ids, u), g in zip(a.faces[:-2], a.groups[:-2]):
            b.tri(np.array(a.v)[ids] * 2, np.array(a.uv)[u], m, g)
        with self.assertRaisesRegex(ValueError, 'Bounds'):
            H.check_pair(a, b)


class TheBuildersMesh(unittest.TestCase):
    def test_to_source_and_back_keep_units_and_texture_convention(self):
        # builder vertices: Morrowind units, the NIF's v; the recipes' frame: the same units, v' = 1 - v
        v = np.array([[0, 0, 0, .25, .1, 255, 255, 255, 255], [4, 0, 0, .5, .1, 255, 255, 255, 255],
                      [0, 4, 0, .25, .6, 255, 255, 255, 255]], float)
        model = H.to_source(v, [[0, 1, 2, 3]])
        self.assertEqual(model.faces[0][0], 'm3')
        np.testing.assert_allclose(np.array(model.uv)[0], [.25, .9])
        out_v, out_f = H.to_builder(model, 4)
        np.testing.assert_allclose(out_v[:, :5], v[:, :5])
        self.assertEqual(out_f.tolist(), [[0, 1, 2, 3]])

    def test_panel_coordinates_are_the_pictures_texels(self):
        m = H.Model()
        m.quad([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], [(0, 0), (1, 0), (1, 1), (0, 1)], 'panels')
        atlas = np.zeros((128, 256, 3), np.uint8)
        out_v, out_f = H.to_builder(m, 5, atlas)
        # u spans the picture's 256 texels (4 x 64), v its 128 (2 x 64), the NIF's direction
        self.assertEqual((out_v[:, 3].min(), out_v[:, 3].max()), (0.0, 4.0))
        self.assertEqual((out_v[:, 4].min(), out_v[:, 4].max()), (0.0, 2.0))
        self.assertTrue((out_f[:, 3] == 5).all())
        with self.assertRaisesRegex(ValueError, 'picture'):
            H.to_builder(m, 5)

    def test_conservative_keeps_the_source_textures(self):
        a = cylinder()
        v = np.array([[*p, uv[0], 1 - uv[1], 255, 255, 255, 255] for (m, ids, u) in a.faces
                      for p, uv in zip(np.array(a.v)[ids], np.array(a.uv)[u])], float)
        f = [[3 * k, 3 * k + 1, 3 * k + 2, 0] for k in range(len(a.faces))]
        row = {'kind': 'conservative', 'recipe': {'source_triangles': 96, 'expected_triangles': None,
                                                  'settings': {'kind': 'conservative',
                                                               'shapes': {'m0': {'target': 40, 'qem_error': 10}}}}}
        out_v, out_f, picture, report = H.rebuild(v, f, 1, {}, row)
        self.assertIsNone(picture)
        self.assertEqual(set(out_f[:, 3].tolist()), {0})
        self.assertLess(report['triangles'], 96)
        self.assertEqual(report['open_edges'], report['source_open_edges'])
        row['recipe']['source_triangles'] = 95
        with self.assertRaisesRegex(ValueError, 'the recipe 95'):
            H.rebuild(v, f, 1, {}, row)


class TheShippedRows(unittest.TestCase):
    def test_every_row_records_its_numbers_and_the_rule(self):
        table = M.load_table()
        rows = table['models']
        self.assertEqual(len(rows), 19)
        for src, row in rows.items():
            self.assertIn(row['kind'], M.KINDS, src)
            counts = row['counts']
            if row['kind'] == 'lantern_rings':
                # the intake rule on the panels the row takes (frosted or baked)
                added = counts['texture_bytes_added_frosted' if row['panels'] == 'frosted' else 'texture_bytes_added']
                self.assertLessEqual(added, counts['mesh_bytes_saved_estimate'], src)
                continue
            self.assertLess(counts['triangles'], counts['triangles_before'], src)
            self.assertLessEqual(counts['faces_rooms'], counts['faces_before_rooms'] or 10 ** 6, src)
            if row['method'] == 2:
                # the intake rule: no more texture memory added than mesh memory saved
                self.assertLessEqual(counts['texture_bytes_added'], counts['mesh_bytes_saved_estimate'], src)
            else:
                self.assertIn('FAILS', row['ab'], src)
                self.assertGreater(counts['texture_bytes_added'], counts['mesh_bytes_saved_estimate'], src)
        kinds = {r['kind'] for r in rows.values() if r['method'] == 2}
        self.assertEqual(kinds, {'lantern_rings', 'conservative'})
        text = M.TABLE.read_text(encoding='utf-8').lower()
        for word in ('.dds', '.tga', '.png', '.obj'):
            self.assertNotIn(word, text)

    def test_another_source_file_is_not_that_model(self):
        rows = M.load_table()['models']
        src = 'meshes/l/light_de_lamp_01.nif'
        model = {'source': src, 'source_sha256': '0' * 64}
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(M.METHOD_VARIABLE, None)
            profile = {}
            self.assertIs(M.apply_method2(profile, model, {'format': 1, 'models': {src: rows[src]}}), profile)
            hit = M.apply_method2({}, dict(model, source_sha256=rows[src]['source_sha256']),
                                  {'format': 1, 'models': {src: rows[src]}})
        self.assertEqual(hit['visual_method2']['kind'], 'conservative')


if __name__ == '__main__':
    unittest.main()
