# SPDX-License-Identifier: GPL-3.0-only
"""The general underside rules (B16, CHIM-VOS-TEMPLE-WALKWAY-41; EXPERIMENTAL, AMIWIND_COLLISION_UNDERSIDE rule /
split / whole): a convex collision piece that passes through an authored downward-facing surface (the underside of a
slab a walkway runs under) and fills more than a unit under it becomes the authored plates of its triangles (rule),
is split first (split), or makes its whole mesh keep its authored surfaces (whole). The name list
town_regions.UNDERPASS_NAMES stays the default (names)."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402

import mesh_geometry as mg  # noqa: E402
import mesh_geometry_env  # noqa: E402
import town_regions  # noqa: E402


def boxes_mesh(boxes, flip_top=False):
    """(v, f) of axis-aligned boxes in mesh units (four per Quake unit), sharing coincident corners; flip_top: the
    top faces wound the wrong way (they look downward)."""
    index, verts, faces = {}, [], []

    def vid(p):
        key = tuple(round(c, 4) for c in p)
        if key not in index:
            index[key] = len(verts)
            verts.append(list(key) + [0., 0.])
        return index[key]
    for (x0, y0, z0), (x1, y1, z1) in boxes:
        c = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        # outward-facing quads as two triangles each
        for quad in ((1, 3, 2, 0), (6, 7, 5, 4), (4, 5, 1, 0), (3, 7, 6, 2), (2, 6, 4, 0), (5, 7, 3, 1)):
            if flip_top and quad == (5, 7, 3, 1):
                quad = tuple(reversed(quad))
            a, b, cc, d = (vid(c[k]) for k in quad)
            faces += [[a, b, cc, 0], [a, cc, d, 0]]
    return np.array(verts, float), np.array(faces, int)


def overhang(lip=7.2):
    """A slab 100 x 100 Quake units, 8 thick, with a lip LIP mesh units deep along two edges: its convex hull
    reaches LIP / 4 Quake units below the slab's underside between the lips (the temple slab of Vos: 2 units)."""
    return boxes_mesh([((0., 0., 0.), (400., 400., 32.)),
                       ((0., 0., -lip), (20., 400., 0.)), ((380., 0., -lip), (400., 400., 0.))])


class UndersideRule(unittest.TestCase):
    def test_a_hull_under_an_authored_ceiling_becomes_plates(self):
        v, f = overhang()
        plain = mg.collision_parts(v, f, 2, plates=[])
        self.assertEqual(len(plain), 1)                 # closes 1.8 units: within the tolerance, one convex piece
        plates = []
        ruled = mg.collision_parts(v, f, 2, plates=plates, underside=mg.UNDERSIDE_DEPTH)
        self.assertGreater(len(ruled), 1)
        # split first; the pieces that still close space under the slab and cannot be split are authored plates
        # (exact bevels); no convex piece left closes space under an authored ceiling
        self.assertGreater(len(plates), 0)
        tris = v[f[:, :3], :3] * .25
        for k, (points, hull, ids, error) in enumerate(ruled):
            if k not in plates:
                self.assertFalse(mg._closes_under_ceiling(hull, mg._ceiling_samples(tris)), k)

    def test_a_lip_within_a_unit_keeps_the_convex_piece(self):
        v, f = overhang(lip=3.2)                        # 0.8 units under the underside
        self.assertEqual(len(mg.collision_parts(v, f, 2, plates=[], underside=mg.UNDERSIDE_DEPTH)), 1)

    def test_a_plain_box_is_never_caught(self):
        v, f = boxes_mesh([((0., 0., 0.), (400., 400., 32.))])
        self.assertEqual(len(mg.collision_parts(v, f, 2, plates=[], underside=mg.UNDERSIDE_DEPTH)), 1)

    def test_a_top_face_wound_downward_is_no_ceiling(self):
        v, f = boxes_mesh([((0., 0., 0.), (400., 400., 32.))], flip_top=True)
        t = v[f[:, :3], :3]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        self.assertEqual(int((n[:, 2] < 0).sum()), 4)   # bottom and the flipped top
        self.assertEqual(len(mg.collision_parts(v, f, 2, plates=[], underside=mg.UNDERSIDE_DEPTH)), 1)

    def test_the_profile_switch(self):
        v, f = overhang()
        base = {'collision_source': 'root_node_or_visual', 'stair_plates': True}
        plain, _, _ = mg.collision_pieces(v, f, base, stairs='on')
        ruled, exact, note = mg.collision_pieces(v, f, dict(base, underside_plates=mg.UNDERSIDE_DEPTH), stairs='on')
        self.assertEqual(len(plain), 1)
        self.assertGreater(len(ruled), 1)
        self.assertIn('authored plates', note)
        self.assertTrue(exact)

    def test_whole_mode_keeps_every_authored_surface(self):
        v, f = overhang()
        base = {'collision_source': 'root_node_or_visual', 'stair_plates': True}
        pieces, exact, note = mg.collision_pieces(v, f, dict(base, underside_whole=mg.UNDERSIDE_DEPTH), stairs='on')
        self.assertEqual(len(pieces), len(mg.shell_collision_parts(v, f)))
        self.assertIs(exact, True)
        self.assertIn('under an authored ceiling', note)
        box_v, box_f = boxes_mesh([((0., 0., 0.), (400., 400., 32.))])
        plain, _, _ = mg.collision_pieces(box_v, box_f, dict(base, underside_whole=mg.UNDERSIDE_DEPTH), stairs='on')
        self.assertEqual(len(plain), 1)

    def test_classic_profiles_ignore_it(self):
        # legacy open-world maps (no stair_plates) keep collision_pieces_classic: the rule is never applied there
        v, f = overhang()
        pieces, _, _ = mg.collision_pieces(v, f, {'underside_plates': mg.UNDERSIDE_DEPTH}, stairs='on')
        self.assertEqual(len(pieces), 1)


class NameListStaysSelectable(unittest.TestCase):
    def test_names_keep_the_temples_hollow_and_rule_mode_does_not(self):
        for name in town_regions.UNDERPASS_NAMES:
            source = 'meshes/x/' + name
            with self.subTest(name=name):
                self.assertTrue(town_regions.visual_profile(source, 1000)['hollow_collision'])
                rule = town_regions.visual_profile(source, 1000, underpass_names=False)
                self.assertNotIn('hollow_collision', rule)
                self.assertIn('surface_collision_beyond', rule)     # as every other exterior architecture
        # the other underpass meshes of the list are untouched
        self.assertTrue(town_regions.visual_profile('meshes/x/ex_hlaalu_b_01.nif', 1000,
                                                    underpass_names=False)['hollow_collision'])

    def test_the_mode(self):
        with patch.dict(os.environ, {mesh_geometry_env.UNDERSIDE_VARIABLE: ''}):
            self.assertEqual(mesh_geometry_env.underside_mode(), 'names')     # the list stays the default
        for mode in ('rule', 'split', 'whole', 'names'):
            with patch.dict(os.environ, {mesh_geometry_env.UNDERSIDE_VARIABLE: mode}):
                self.assertEqual(mesh_geometry_env.underside_mode(), mode)
        with patch.dict(os.environ, {mesh_geometry_env.UNDERSIDE_VARIABLE: 'maybe'}):
            with self.assertRaises(ValueError):
                mesh_geometry_env.underside_mode()

    def test_the_chim_model_builder_sets_it(self):
        text = (ROOT / 'tools' / 'chim' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("underpass_names=underside == 'names'", text)
        self.assertIn("profile['underside_plates'] = UNDERSIDE_DEPTH", text)


if __name__ == '__main__':
    unittest.main()
