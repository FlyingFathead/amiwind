# SPDX-License-Identifier: GPL-3.0-only
"""CHIM-STRIDER-SCALED-SEAMS-36: every scaled or tilted model variant has the vertices and edges of its base.

A variant is the prepared mesh (one reduction) scaled and turned. Sharing vertices by the placed position
rounded to 1e-5 (the method before v0.0.36-dev3, model weld 'placed') splits a vertex at some scales and not
at others, so a variant had open edges its base does not have (the Seyda Neen silt strider: 926 against 898).
Shared in the base's own frame (model weld 'base', the default), every variant has the base's topology; the
variant audit (tools/chim/variant_audit.py) finds any variant that differs from its base."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.build import model_weld_mode  # noqa: E402
from chim.models import base_frame, variant_unit  # noqa: E402
from chim.terrain import quake_texture_axes  # noqa: E402
from chim import variant_audit as VA  # noqa: E402

TEXSIZE = 64
MODEL = {'source': 'synthetic-plates.nif', 'materials': [{'texture_index': None, 'diffuse': [1, 1, 1]}]}
# The shared corner of the two plates is stored twice, 4e-6 units apart, as a reduction or a texture split
# leaves it (two polygons computing the same point): one rounding cell at some scales, two at others.
SPLIT = 4e-6


def plates():
    """A prepared mesh (prepare_mesh_bsp._prepare_model's form): a strip of quads on one row of corners, each
    quad's own copy of a shared corner a little apart (SPLIT), so the strip is closed only where they are shared."""
    n = np.array([0.0, 0.0, 1.0])
    axes = quake_texture_axes(n) / TEXSIZE
    polys = []
    for k in range(12):
        x0, x1 = 3.1234 * k + 0.3, 3.1234 * (k + 1) + 0.3
        # the quad's right edge, and the next quad's left edge, 4e-6 apart: one edge of the source mesh
        poly = np.array([[x0 + (SPLIT if k else 0.0), 0.7, 1.9], [x1, 0.7, 1.9], [x1, 5.3, 1.9],
                         [x0 + (SPLIT if k else 0.0), 5.3, 1.9]])
        polys.append((poly, 0, axes, np.zeros(2), n))
    corners = np.array([[0.3, 0.7, 1.9], [40, 0.7, 1.9], [40, 5.3, 1.9], [0.3, 5.3, 1.9],
                        [0.3, 0.7, 0.0], [40, 0.7, 0.0], [40, 5.3, 0.0], [0.3, 5.3, 0.0]])
    v = np.column_stack((corners * 4, np.zeros((8, 2))))
    return v, np.array([[0, 1, 2, 0]]), polys, [(corners, None, [], 0.)], {}


def variant(scale, rotation=(0.0, 0.0, 0.0), weld='base'):
    ref = {'model_index': 0, 'number': 1, 'scale': scale, 'rotation_radians': list(rotation),
           'position': [100.0, -40.0, 8.0]}
    res = variant_unit({'ref': ref, 'data': plates(), 'texsize': TEXSIZE, 'centre': [0.0, 0.0], 'model': MODEL,
                        'exact': False, 'hollow': False, 'qbsp': None, 'collision_cache': None, 'weld': weld,
                        'keep_chain': True})
    return F.brush_image(res['lumps'])[0]


SCALES = [round(0.5 + 0.01 * k, 2) for k in range(151)]


class VariantWeldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = VA.topology(*VA.decode(variant(1.0)))

    def test_placed_sharing_changes_with_the_scale(self):
        """The old method: some scales split the shared corners (the defect this repairs)."""
        counts = {VA.topology(*VA.decode(variant(s, weld='placed')))['open_edges'] for s in SCALES[::5]}
        self.assertGreater(len(counts), 1)

    def test_base_sharing_is_the_same_at_every_scale_and_tilt(self):
        for s in SCALES[::5]:
            self.assertEqual(VA.topology(*VA.decode(variant(s)))['open_edges'], self.base['open_edges'], s)
            self.assertEqual(VA.topology(*VA.decode(variant(s)))['vertices'], self.base['vertices'], s)
        for rot in ((0.1, 0.05, 0.4), (6.08, 0.4, 3.18), (0.0, 0.0, -2.1)):
            top = VA.topology(*VA.decode(variant(0.89, rot)))
            self.assertEqual((top['vertices'], top['open_edges']), (self.base['vertices'], self.base['open_edges']))

    def test_scale_one_at_yaw_zero_unchanged(self):
        """Untilted at scale 1 and yaw 0 the base frame is the placed frame: the same record as before."""
        self.assertEqual(variant(1.0, (0.0, 0.0, 0.0)), variant(1.0, (0.0, 0.0, 0.0), weld='placed'))

    def test_untilted_variant_does_not_depend_on_the_first_placements_yaw(self):
        """The yaw is the entity's: two frames whose first placement of a variant is turned differently store
        one record (before: the yaw's rounding made two, stored as name#2)."""
        for s in (1.0, 0.89, 1.27):
            records = {variant(s, (0.0, 0.0, yaw)) for yaw in (0.0, 1.3, -2.1, 3.0)}
            self.assertEqual(len(records), 1, s)
        placed = {variant(0.89, (0.0, 0.0, yaw), weld='placed') for yaw in (0.0, 1.3, -2.1, 3.0)}
        self.assertGreater(len(placed), 1)

    def test_base_frame_inverts_the_placement(self):
        ref = {'scale': 0.89, 'rotation_radians': [0.1, 0.2, 0.3], 'position': [0, 0, 0], '_visual_offset': [1, 2, 3]}
        from prepare_mesh_bsp import _placement_frame
        from prepare_scenery import reference_rotation
        _, rotation = _placement_frame(ref, (0, 0))
        r = rotation.T @ reference_rotation(ref)
        p = np.array([1.5, -2.25, 7.0])
        placed = p @ r.T * 0.89 + r @ np.array([1, 2, 3.0]) * 0.89
        np.testing.assert_allclose(base_frame(ref, (0, 0))(placed), p, atol=1e-12)
        self.assertIsNone(base_frame(dict(ref, _flatten_shift=0.5), (0, 0)))

    def test_weld_setting(self):
        self.assertEqual(model_weld_mode(None), 'base')
        self.assertEqual(model_weld_mode({'model_weld': 'placed'}), 'placed')
        with self.assertRaises(ValueError):
            model_weld_mode({'model_weld': 'nearest'})


class VariantAuditTests(unittest.TestCase):
    def models(self, weld):
        out = [{'name': 'x/plates@s1', 'image': variant(1.0)}]
        for s in SCALES[::5]:
            if s != 1.0:
                out.append({'name': 'x/plates@s%g' % s, 'image': variant(s, weld=weld)})
        return out

    def test_audit_passes_base_sharing(self):
        report = VA.audit_models(self.models('base'), references={'x/plates'})
        self.assertEqual(report['derived'], report['compared'])
        self.assertEqual(report['topology_differences'], [])
        self.assertEqual(report['failures'], [])

    def test_audit_finds_split_seams(self):
        report = VA.audit_models(self.models('placed'), references=())
        self.assertEqual(report['derived'], report['compared'])
        self.assertTrue(report['topology_differences'])

    def test_reference_model_needs_one_reduction(self):
        """A reference model's variant from another reduction (another face count) fails; another mesh's is listed."""
        other = plates()
        other[2].pop()
        ref = {'model_index': 0, 'number': 1, 'scale': 0.89, 'rotation_radians': [0, 0, 0], 'position': [0, 0, 0]}
        res = variant_unit({'ref': ref, 'data': other, 'texsize': TEXSIZE, 'centre': [0.0, 0.0], 'model': MODEL,
                            'exact': False, 'hollow': False, 'qbsp': None, 'collision_cache': None, 'keep_chain': True})
        models = [{'name': 'x/plates@s1', 'image': variant(1.0)},
                  {'name': 'x/plates@s0.89', 'image': F.brush_image(res['lumps'])[0]}]
        self.assertEqual(len(VA.audit_models(models, references={'x/plates'})['failures']), 1)
        report = VA.audit_models(models, references=())
        self.assertEqual((len(report['failures']), len(report['other_reductions'])), (0, 1))

    def test_names(self):
        self.assertEqual(VA.parse_name('r/siltstrider@s0.89'), ('r/siltstrider', 0.89, True, False, 0))
        self.assertEqual(VA.parse_name('f/flora_bc_tree_05@s2#2'), ('f/flora_bc_tree_05', 2.0, True, False, 2))
        self.assertEqual(VA.parse_name('x/a@s1@t0.1,0.2,0.3')[2], False)
        self.assertEqual(VA.parse_name('x/a@s1@f0.5')[3], True)

    def test_reference_list_names_the_base_strider(self):
        self.assertIn('r/siltstrider', VA.reference_stems())


if __name__ == '__main__':
    unittest.main()
