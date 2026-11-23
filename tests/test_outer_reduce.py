# SPDX-License-Identifier: GPL-3.0-only
"""The outer-measures reduction of an actor model (tools/outer_reduce.py; MESH-SEAM-METHOD-62): the switch, the weld,
the relative-error weights, the reducer's weights held to one call, a reduction that keeps the girth of a thin limb
where the plain one thins it, and the bake's own texture work on the already reduced geometry (outer_reduce.given:
npc_geometry._bake unchanged, its reducer replaced for one bake). Synthetic shapes, no game files."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import outer_reduce as R  # noqa: E402

GEOMETRY = all(importlib.util.find_spec(n) for n in ('scipy', 'PIL'))
if GEOMETRY:
    # imported while src/ is ahead of tools/ (npc_seam_audit, imported later by the check, puts tools/ first)
    import npc_geometry as G  # noqa: E402


def tube(radius, z0, z1, around=16, rings=8, bottom=False, top=False, centre=(0.0, 0.0)):
    pts = []
    for k in range(rings + 1):
        z = z0 + (z1 - z0) * k / rings
        for i in range(around):
            a = 2 * np.pi * i / around
            pts.append((centre[0] + radius * np.cos(a), centre[1] + radius * np.sin(a), z))
    faces = []
    for k in range(rings):
        for i in range(around):
            a, b = k * around + i, k * around + (i + 1) % around
            faces += [(a, b, b + around), (a, b + around, a + around)]
    if bottom:
        pts.append((centre[0], centre[1], z0))
        faces += [(len(pts) - 1, (i + 1) % around, i) for i in range(around)]
    if top:
        pts.append((centre[0], centre[1], z1))
        base = rings * around
        faces += [(len(pts) - 1, base + i, base + (i + 1) % around) for i in range(around)]
    return np.array(pts, float), np.array(faces, int)


def shape(name, pts, faces, part=3, bone='bip01 spine'):
    return {'name': name, 'part': part, 'positions': np.asarray(pts, float)[None], 'faces': np.asarray(faces, int),
            'uv': np.zeros((len(pts), 2)), 'colours': np.ones((len(pts), 4)), 'material': 0,
            'bone_name': np.array([bone] * len(pts), dtype=object)}


def body_and_limb():
    """A thick closed body and a thin closed limb beside it, each on its own bone."""
    return [shape('Tri Body', *tube(6.0, 0.0, 20.0, around=24, rings=12, bottom=True, top=True)),
            shape('Tri Arm', *tube(0.8, 2.0, 18.0, around=12, rings=16, bottom=True, top=True, centre=(9.0, 0.0)),
                  part=13, bone='bip01 r upperarm')]


class SwitchTests(unittest.TestCase):
    def test_default_is_outer_and_today_is_kept(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_ACTOR_REDUCER', None)
            self.assertEqual(R.mode(), 'outer')
        with mock.patch.dict(os.environ, {'AMIWIND_ACTOR_REDUCER': 'today'}):
            self.assertEqual(R.mode(), 'today')
        with mock.patch.dict(os.environ, {'AMIWIND_ACTOR_REDUCER': 'free'}):
            with self.assertRaises(ValueError):
                R.mode()
        for value in ('shared', 'needed'):          # the shared-vertex A/B modes
            with mock.patch.dict(os.environ, {'AMIWIND_ACTOR_REDUCER': value}):
                self.assertEqual(R.mode(), value)


class WeldTests(unittest.TestCase):
    def test_shared_points_become_one_and_repeats_go(self):
        pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1.00001, 0, 0], [1, 1, 0]], float)
        faces = np.array([[0, 1, 2], [3, 4, 2], [0, 1, 2], [0, 0, 1]])
        w, ff, src = R.weld(pts, faces)
        self.assertEqual(len(w), 4)
        self.assertEqual(len(ff), 2)
        self.assertEqual(sorted(src.tolist()), [0, 1])

    def test_a_thin_group_weighs_more(self):
        shapes = body_and_limb()
        import outer_hull as H
        sp, sf = H.source_whole(shapes)
        groups = H.bone_faces(shapes)
        w = R.weights(sp, sf, R.group_of_faces(groups, len(sf)))
        body = len(shapes[0]['faces'])
        self.assertGreater(w[body:].mean(), w[:body].mean())

    def test_the_weights_hold_for_one_call_only(self):
        import mold_shell
        original = mold_shell._plane_quadric
        with R.weighted(np.array([2.0])):
            self.assertIsNot(mold_shell._plane_quadric, original)
            p = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float)
            np.testing.assert_allclose(mold_shell._plane_quadric(*p), 2 * original(*p))
        self.assertIs(mold_shell._plane_quadric, original)


@unittest.skipUnless(GEOMETRY, 'scipy and PIL are needed for the reduction and its check')
class ReduceTests(unittest.TestCase):
    def test_reduction_keeps_the_thin_limb_and_passes(self):
        import outer_hull as H
        shapes = body_and_limb()
        groups = H.bone_faces(shapes)
        total = sum(len(s['faces']) for s in shapes)
        found = R.reduce(shapes, total // 2, groups)
        self.assertIsNotNone(found)
        v, f, row = found
        self.assertLessEqual(len(f), total // 2)
        self.assertEqual(row['problems'], [])
        self.assertGreaterEqual(row['girth']['bip01 r upperarm'], H.GIRTH_KEEP)

    def test_nothing_to_reduce_keeps_today(self):
        import outer_hull as H
        shapes = body_and_limb()
        self.assertIsNone(R.reduce(shapes, 10 ** 6, H.bone_faces(shapes)))

    def test_the_bake_takes_the_reduced_geometry_as_given(self):
        shapes = body_and_limb()
        pts = np.concatenate([s['positions'][0] for s in shapes])
        off = len(shapes[0]['positions'][0])
        entries = [(False, pts, shapes[0]['faces'][:40]), (False, pts, shapes[1]['faces'][:20] + off)]
        materials = [{'texture_index': None, 'diffuse': [1.0, 1.0, 1.0]}]
        palette = bytes(range(256)) * 3
        parts, owners = [], []
        before = (G.simplify_shape, G.keep_head_inside_cover, G.keep_outside_surface)
        with R.given(shapes, entries) as complete:
            frames, faces, uv, skin = G._bake(shapes, materials, {}, palette, 666, None, [0, 0], None, frozenset(),
                                              False, face_parts=parts, face_shapes=owners)
            self.assertTrue(complete())
        self.assertEqual((G.simplify_shape, G.keep_head_inside_cover, G.keep_outside_surface), before)
        self.assertEqual(len(faces), 60)
        self.assertEqual(owners, [0] * 40 + [1] * 20)
        self.assertEqual(parts, [3] * 40 + [13] * 20)
        np.testing.assert_allclose(frames[0][faces[0][[0, 2, 1]]], pts[shapes[0]['faces'][0]], atol=1e-6)

    def test_a_reducer_call_out_of_order_is_refused(self):
        shapes = body_and_limb()
        pts = np.concatenate([s['positions'][0] for s in shapes])
        entries = [(False, pts, shapes[0]['faces'][:40]), (False, pts, shapes[1]['faces'][:20])]
        with R.given(shapes, entries) as complete:
            limb = np.unique(np.round(shapes[1]['positions'][0], 5), axis=0)
            with self.assertRaises(R.OutOfOrder):
                G.simplify_shape(limb, shapes[1]['faces'], 0)
            self.assertFalse(complete())

    def test_the_bake_module_is_not_changed(self):
        # npc_geometry is in the key of most build stages: the reduction reaches it only for the length of a bake
        source = (ROOT / 'tools' / 'npc_geometry.py').read_text(encoding='utf-8')
        self.assertNotIn('outer_reduce', source)
        self.assertNotIn('reduced_override', source)


class SharedVertices(unittest.TestCase):
    """The shared-vertex output (outer_reduce.shared_shapes, charts, tinted, closest_bary)."""

    def test_the_closest_point_of_a_triangle(self):
        a, b, c = np.array([[0.0, 0, 0]]), np.array([[1.0, 0, 0]]), np.array([[0.0, 1, 0]])
        inside = R.closest_bary(np.array([[0.25, 0.25, 3.0]]), a, b, c)
        np.testing.assert_allclose(inside, [[0.5, 0.25, 0.25]], atol=1e-9)
        np.testing.assert_allclose(R.closest_bary(np.array([[-1.0, -1, 0]]), a, b, c), [[1, 0, 0]])
        np.testing.assert_allclose(R.closest_bary(np.array([[0.5, -2.0, 0]]), a, b, c), [[0.5, 0.5, 0]], atol=1e-9)

    def test_a_texture_seam_is_two_charts(self):
        joined = np.array([[0, 1, 2], [1, 3, 2]])
        self.assertEqual(len(set(R.charts(joined, 4))), 1)
        seam = np.array([[0, 1, 2], [4, 3, 5]])           # the second face repeats points 1 and 2 as 4 and 5
        self.assertEqual(len(set(R.charts(seam, 6))), 2)

    def seam_quad(self):
        """A unit quad of two faces on two texture charts: its middle edge on two vertices with other coordinates."""
        pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 1, 0]], float)
        uv = np.array([[0, 0], [0.5, 0], [0, 0.5], [1, 1], [1, 0.5], [0.5, 1]], float)
        return {'name': 'Tri Quad', 'part': 3, 'positions': pts[None], 'faces': np.array([[0, 1, 2], [3, 5, 4]]),
                'uv': uv, 'colours': np.ones((6, 4)), 'material': 0}

    def test_faces_share_vertices_within_a_chart_and_split_on_its_seam(self):
        quad = self.seam_quad()
        welded = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], float)
        faces = np.array([[0, 1, 2], [3, 2, 1]])
        parts, facts = R.shared_shapes([quad], welded, faces, np.array([0, 0]))
        self.assertEqual((facts['vertices'], facts['charts']), (6, 2))      # the seam's two points, once per chart
        shape = parts[0]
        corners = shape['uv'][shape['faces']]
        np.testing.assert_allclose(sorted(map(tuple, corners[0])), [(0, 0), (0, 0.5), (0.5, 0)], atol=1e-9)
        np.testing.assert_allclose(sorted(map(tuple, corners[1])), [(0.5, 1), (1, 0.5), (1, 1)], atol=1e-9)

    def test_one_chart_shares_every_vertex(self):
        pts, faces = tube(1.0, 0.0, 4.0, around=8, rings=4)
        uv = np.column_stack((np.arange(len(pts)) % 8 / 8.0, np.arange(len(pts)) // 8 / 5.0))
        body = shape('Tri Body', pts, faces)
        body['uv'] = uv
        parts, facts = R.shared_shapes([body], pts, faces, np.zeros(len(faces), int))
        self.assertEqual(facts['vertices'], len(pts))
        self.assertLess(facts['vertices'], 3 * len(faces))

    def test_a_tint_moves_into_a_texture_of_its_own(self):
        plain = {'material': 0, 'colours': np.ones((3, 4))}
        tinted = {'material': 1, 'colours': np.ones((3, 4))}
        materials = [{'texture_index': 'a', 'diffuse': [1.0, 1.0, 1.0]}, {'texture_index': 'a', 'diffuse': [0.5, 1.0, 1.0]}]
        textures = {'a': np.full((2, 2, 4), 200, np.uint8)}
        shapes, mats, tex = R.tinted([plain, tinted], materials, textures)
        self.assertIs(shapes[0], plain)
        self.assertEqual(mats[shapes[1]['material']]['diffuse'], [1.0, 1.0, 1.0])
        image = tex[mats[shapes[1]['material']]['texture_index']]
        self.assertEqual(int(image[0, 0, 0]), 100)
        self.assertEqual(int(textures['a'][0, 0, 0]), 200)             # the original texture unchanged

    @unittest.skipUnless(GEOMETRY, 'scipy and PIL are needed')
    def test_the_shared_encoding_writes_the_chart_vertices(self):
        quad = self.seam_quad()
        welded = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], float)
        parts, _ = R.shared_shapes([quad], welded, np.array([[0, 1, 2], [3, 2, 1]]), np.array([0, 0]))
        parts = [{**s, 'positions': np.concatenate((s['positions'], s['positions'] + [8.0, 0, 0]))} for s in parts]
        materials = [{'texture_index': 'a', 'diffuse': [1.0, 1.0, 1.0]}]
        frames, faces, st, skin = G.shared_vertex_mdl(parts, materials, {'a': np.full((8, 8, 4), 90, np.uint8)},
                                                      bytes(range(256)) * 3)
        self.assertEqual(frames.shape, (2, 6, 3))
        self.assertEqual(len(faces), 2)

    @unittest.skipUnless(GEOMETRY, 'scipy and PIL are needed for the reduction and its check')
    def test_keep_failing_returns_the_reduction_with_its_problems(self):
        import outer_hull as H
        shapes = body_and_limb()
        groups = H.bone_faces(shapes)
        with mock.patch.object(H, 'problems', return_value=['a measure under its limit']):
            self.assertIsNone(R.reduce(shapes, 200, groups, rounds=1))
            v, f, row = R.reduce(shapes, 200, groups, rounds=1, keep_failing=True)
        self.assertLessEqual(len(f), 200)
        self.assertEqual(row['problems'], ['a measure under its limit'])
        # nothing to reduce: the welded whole itself, measured
        v, f, row = R.reduce(shapes, 10 ** 6, groups, keep_failing=True)
        self.assertEqual(len(f), sum(len(s['faces']) for s in shapes))
        self.assertEqual(row['problems'], [])


if __name__ == '__main__':
    unittest.main()
