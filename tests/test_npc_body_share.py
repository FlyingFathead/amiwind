"""NPC-BODY-REGRESSION-62: the body share of an original-head bake and the body check."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import numpy as np  # noqa: E402
import npc_geometry as ng  # noqa: E402


def box(part, lo, hi, name, split=4, caps=True):
    """A closed box shape split into many faces (split x split per side); caps=False: an open tube along z."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    pts, faces = [], []
    for axis in range(3 if caps else 2):
        for side in (0, 1):
            a, b = [i for i in range(3) if i != axis]
            base = len(pts)
            for u in range(split + 1):
                for v in range(split + 1):
                    p = lo.copy()
                    p[axis] = (lo, hi)[side][axis]
                    p[a] = lo[a] + (hi[a] - lo[a]) * u / split
                    p[b] = lo[b] + (hi[b] - lo[b]) * v / split
                    pts.append(p)
            for u in range(split):
                for v in range(split):
                    i = base + u * (split + 1) + v
                    faces += [(i, i + 1, i + split + 2), (i, i + split + 2, i + split + 1)]
    return {'part': part, 'name': name, 'positions': np.array([pts]), 'faces': np.array(faces)}


class BodyShareTest(unittest.TestCase):
    def setUp(self):
        self.env = {k: os.environ.get(k) for k in ('AMIWIND_NPC_BODY_SHARE', 'AMIWIND_NPC_BODY_CHECK')}

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def shapes(self):
        return [box(0, (-4, -4, 60), (4, 4, 70), 'head', 7),        # 588 faces, kept whole
                box(1, (-5, -5, 64), (5, 5, 72), 'hair', 5),        # 300 faces
                box(2, (-2, -2, 56), (2, 2, 60), 'neck', 3),
                box(3, (-8, -4, 34), (8, 4, 56), 'chest', 5),
                box(21, (-6, -3, 18), (-1, 3, 34), 'leg', 5),
                box(22, (1, -3, 18), (6, 3, 34), 'leg', 5)]

    def test_shares(self):
        self.assertEqual(ng.BODY_SHARES, ('body', 'budget'))
        os.environ.pop('AMIWIND_NPC_BODY_SHARE', None)
        self.assertEqual(ng.body_share(), 'body')
        os.environ['AMIWIND_NPC_BODY_SHARE'] = 'nonsense'
        with self.assertRaises(ValueError):
            ng.body_share()

    def test_body_quotas_ignore_head_and_hair(self):
        shapes = self.shapes()
        classes = ['head', 'hair', 'detail', 'torso', 'limb', 'limb']
        q = ng.body_quotas(shapes, 480, classes)
        self.assertEqual(q[0], 0)
        self.assertEqual(q[1], 0)
        self.assertLessEqual(int(q.sum()), 480)
        self.assertGreater(int(q[4]), 100)        # a leg gets a real share, not the 4-face minimum

    def test_legs_kept_under_whole_head(self):
        shapes = self.shapes()
        classes = ['head', 'hair', 'detail', 'torso', 'limb', 'limb']
        old = ng.head_plan(shapes, 480, 666, classes=classes, share='budget', head_detail='original')
        new = ng.head_plan(shapes, 480, 666, classes=classes, share='body', head_detail='original',
                           ceiling=int(old['quotas'].sum()))
        self.assertGreater(int(new['quotas'][4]), int(old['quotas'][4]))
        self.assertLessEqual(int(new['quotas'].sum()), int(old['quotas'].sum()))   # no more triangles

    def test_body_check(self):
        shapes = self.shapes()
        whole = [s for s in shapes]
        frame = np.concatenate([s['positions'][0] for s in whole])
        faces, base = [], 0
        for s in whole:
            faces.append(s['faces'] + base)
            base += len(s['positions'][0])
        faces = np.concatenate(faces)
        parts = [s['part'] for s in whole for _ in s['faces']]
        self.assertEqual(ng.body_check(shapes, frame, faces, parts), [])
        # a stick leg: one leg squeezed to a thin strip
        thin = frame.copy()
        start = sum(len(s['positions'][0]) for s in shapes[:4])
        leg = slice(start, start + len(shapes[4]['positions'][0]))
        thin[leg, 0] = thin[leg, 0].mean()
        thin[leg, 1] = thin[leg, 1].mean()
        found = ng.body_check(shapes, thin, faces, parts)
        self.assertTrue(any(k == 'thin limb' and p == 21 for _, p, _, _, k in found))
        self.assertLess(ng.limb_widths(shapes, thin, faces, parts)[21][0], ng.BODY_LIMB_WIDTH)
        self.assertGreater(ng.limb_widths(shapes, frame, faces, parts)[22][0], .95)
        # a neck gap: the neck pulled down into the chest
        gap = frame.copy()
        start = sum(len(s['positions'][0]) for s in shapes[:2])
        neck = slice(start, start + len(shapes[2]['positions'][0]))
        gap[neck, 2] -= 12
        found = ng.body_check(shapes, gap, faces, parts)
        self.assertTrue(any(k == 'neck gap' for *_, k in found))


class Step1Floors(unittest.TestCase):
    """Design step 1: classes by slot; a part's floor from its own girth and surface."""
    def test_hand_slot_is_never_detail(self):
        small = box(6, (0, 0, 0), (1, 1, 1), 'hand', 3)
        self.assertEqual(ng.slot_classes([small], 33.0), ['limb'])
        belt = box(3, (0, 0, 0), (1, 1, 1), 'belt', 3)
        self.assertEqual(ng.slot_classes([belt], 33.0), ['detail'])

    def test_floor_holds_girth(self):
        leg = box(21, (-1, -1, 0), (1, 1, 16), 'leg', 6)
        floor = ng.part_floors([leg], ['limb'])[0]
        self.assertGreater(floor, 4)
        self.assertLessEqual(floor, len(leg['faces']))
        p, ix = np.unique(np.round(leg['positions'][0], 5), axis=0, return_inverse=True)
        ff = ix[leg['faces']].astype(np.int32)
        rp, rf = ng.simplify_shape(p, ff, floor, True) if floor < len(ff) else (p, ff)
        self.assertGreaterEqual(ng.girth_ratio(p, ff, rp, rf), ng.GIRTH_KEEP)


class Step2Audit(unittest.TestCase):
    """Design step 2: the receipt measures the joints; a pulled-back part opens them."""
    def test_receipt_and_open_joint(self):
        upper = box(21, (-1, -1, 10), (1, 1, 20), 'upper', 4, caps=False)
        lower = box(19, (-1, -1, 0), (1, 1, 10), 'lower', 4, caps=False)
        shapes = [upper, lower]
        frame = np.concatenate([s['positions'][0] for s in shapes])
        faces = np.concatenate([shapes[0]['faces'], shapes[1]['faces'] + len(shapes[0]['positions'][0])])
        parts = [21] * len(shapes[0]['faces']) + [19] * len(shapes[1]['faces'])
        receipt, failures = ng.body_audit(shapes, frame, faces, parts)
        self.assertEqual(receipt['faces'], len(faces))
        self.assertEqual(receipt['open_share'], 0.0)
        self.assertFalse([f for f in failures if f[4] == 'open joint'])
        pulled = frame.copy()
        n = len(shapes[0]['positions'][0])
        pulled[n:, 2] -= 2.0          # the lower part pulled 2 units away from the joint
        receipt, failures = ng.body_audit(shapes, pulled, faces, parts)
        self.assertGreater(receipt['open_share'], ng.JOINT_OPEN_SHARE)


class CoveredOpenings(unittest.TestCase):
    """MESH-REDUCTION-SEAMS-62: an opening counts as covered only on a head patch the bake removed under the hair;
    a visible gap, or one at a join, stays uncovered."""
    def setUp(self):
        import mesh_seam_check
        self.msc = mesh_seam_check
        self.head = box(0, (-4, -4, 60), (4, 4, 70), 'head', 4)
        self.hair = box(1, (-5, -5, 66), (5, 5, 72), 'hair', 2)
        self.shapes = [self.head, self.hair]
        p = self.head['positions'][0]
        f = self.head['faces']
        centre = p[f].mean(1)
        self.top = centre[:, 2] > 69.9            # the head's top, under the hair
        self.low = centre[:, 2] < 60.1            # its bottom: a visible gap if removed
        self.p, self.f = p, f

    def model(self, keep):
        frame = np.concatenate([self.p, self.hair['positions'][0]])
        faces = np.concatenate([self.f[keep], self.hair['faces'] + len(self.p)])
        shapes = [0] * int(keep.sum()) + [1] * len(self.hair['faces'])
        return frame, faces, shapes

    def test_removed_patch_under_hair_is_covered(self):
        frame, faces, owner = self.model(~self.top)
        covered, uncovered = self.msc.classify(self.shapes, frame, faces, owner, self.p[self.f[self.top]])
        self.assertTrue(covered)
        self.assertEqual(uncovered, [])

    def test_visible_gap_still_fails(self):
        frame, faces, owner = self.model(~(self.top | self.low))
        covered, uncovered = self.msc.classify(self.shapes, frame, faces, owner, self.p[self.f[self.top]])
        self.assertTrue(uncovered)
        self.assertTrue(all(abs(pos[2] - 60) < 1.0 for _, _, pos in uncovered))

    def test_a_join_is_never_covered(self):
        neck = box(2, (-4, -4, 50), (4, 4, 70.05), 'neck', 2)   # meets the removed patch's rim: a join there
        shapes = [self.head, self.hair, neck]
        frame = np.concatenate([self.p, self.hair['positions'][0], neck['positions'][0]])
        keep = ~self.top
        faces = np.concatenate([self.f[keep], self.hair['faces'] + len(self.p),
                                neck['faces'] + len(self.p) + len(self.hair['positions'][0])])
        owner = [0] * int(keep.sum()) + [1] * len(self.hair['faces']) + [2] * len(neck['faces'])
        covered, uncovered = self.msc.classify(shapes, frame, faces, owner, self.p[self.f[self.top]])
        self.assertTrue(uncovered)


if __name__ == '__main__':
    unittest.main()
