"""The hair or helmet takes the head's share of a budget-head bake (NPC-HAIR-BACK-MISSING-53).

Up to v0.0.53 the budget split weighted only the head (body part slot 0) and gave it a floor of up to 120 faces; the
hair (slot 1) got 4 faces plus a plain share (AMIWIND_NPC_HAIR_SHARE=plain keeps that split). The Suran dancers' hair
caps kept 24 to 43 of their 174 to 435 triangles over heads that kept about 185 of 502: the coarse cap's chords sank
under the scalp and the back of the head showed skin. Under 'head' (the default from v0.0.54) the hair shares the
head's rule. Synthetic meshes only (no game data in the suite): a dense head ball, a hair cap a little outside
its back half, a dense body, more than 8 frames (the skeletal resident's sample count)."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from test_npc_head_detail import needs_numpy  # noqa: E402

FRAMES = 10


def ball(name, part, radius, rows, cols, back_only=False):
    """A UV sphere (outward winding); back_only: the half with y > 0 (the back of the head) as an open cap."""
    import numpy as np
    top = np.pi / 2 if back_only else np.pi
    theta = np.linspace(0, top, cols + 1) if back_only else np.linspace(0, 2 * np.pi, cols + 1)[:-1]
    phi = np.linspace(0.05, np.pi - .05, rows + 1)
    points = []
    for p in phi:
        for t in theta:
            angle = t + (np.pi / 4 if back_only else 0)     # the cap spans y > 0 around the back
            points.append((radius * np.sin(p) * np.cos(angle), radius * np.sin(p) * np.sin(angle),
                           30 + radius * np.cos(p)))
    points = np.array(points)
    width = len(theta)
    faces = []
    for j in range(rows):
        for i in range(cols if back_only else width):
            a, b = j * width + i, j * width + (i + 1) % width
            c, d = a + width, b + width
            faces += [(a, c, b), (b, c, d)]
    faces = np.array(faces)
    # outward winding: flip the faces whose normal points to the centre
    centre = np.array([0, 0, 30.])
    n = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    inward = np.einsum('ij,ij->i', n, points[faces].mean(axis=1) - centre) < 0
    faces[inward] = faces[inward][:, [0, 2, 1]]
    positions = np.repeat(points[None], FRAMES, axis=0)
    uv = np.zeros((len(points), 2))
    return {'name': name, 'part': part, 'positions': positions, 'faces': faces, 'uv': uv,
            'colours': np.ones((len(points), 4)), 'material': 0}


def body():
    from test_npc_head_detail import grid
    import numpy as np
    shape = grid('tri chest', 3, 24, 20, 10)
    shape['positions'] = np.repeat(shape['positions'][:1], FRAMES, axis=0)
    return shape


def skin_share(frames, faces, parts):
    """Share of the rays from behind (y > 0) whose first front-facing hit is head skin, not hair."""
    import numpy as np
    points = frames[0]
    faces = np.asarray(faces)[:, [0, 2, 1]]          # the bake writes Quake's winding: back to the source's
    keep = np.isin(parts, (0, 1))
    faces, labels = faces[keep], np.asarray(parts)[keep]
    a, b, c = (points[faces[:, i]] for i in range(3))
    e1, e2 = b - a, c - a
    normal = np.cross(e1, e2)
    centre = np.array([0, 0, 30.])
    seen = []
    for theta in np.linspace(.25 * np.pi, .75 * np.pi, 15):        # around the back, y > 0
        for z in np.linspace(-.6, .6, 9):
            d = np.array([np.cos(theta), np.sin(theta), z])
            d /= np.linalg.norm(d)
            o, r = centre + d * 40, -d
            p = np.cross(r, e2)
            det = np.einsum('ij,ij->i', e1, p)
            ok = (normal @ r < 0) & (np.abs(det) > 1e-12)
            inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
            s = o - a
            u = np.einsum('ij,ij->i', s, p) * inv
            q = np.cross(s, e1)
            v = (q @ r) * inv
            t = np.einsum('ij,ij->i', e2, q) * inv
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
            if hit.any():
                seen.append(labels[np.flatnonzero(hit)[np.argmin(t[hit])]])
    seen = np.array(seen)
    return float(np.mean(seen == 0)), len(seen)


def open_edges(points, faces):
    """Edges used by one triangle only, after welding the points by position (a closed shell has none)."""
    import numpy as np
    _, ix = np.unique(np.round(np.asarray(points), 4), axis=0, return_inverse=True)
    w = ix.reshape(-1)[np.asarray(faces)]
    edges = np.sort(np.concatenate([w[:, [0, 1]], w[:, [1, 2]], w[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts == 1).sum())


class HairShare(unittest.TestCase):
    palette = bytes(range(256)) * 3
    materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]

    def shapes(self):
        return [ball('tri head', 0, 4.0, 16, 32), ball('tri hair', 1, 4.12, 16, 16, back_only=True), body()]

    @needs_numpy
    def test_quotas(self):
        from npc_geometry import _budget_quotas
        shapes = self.shapes()
        n = [len(s['faces']) for s in shapes]
        with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': 'plain'}):
            plain = _budget_quotas(shapes, 480, 666, None, None)
        with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': 'head'}):
            head = _budget_quotas(shapes, 480, 666, None, None)
        self.assertGreaterEqual(head[1], min(120, n[1]))             # the head's floor for the hair
        self.assertLess(plain[1], 120)                                # previously a plain share
        self.assertLess(head[0], plain[0])                            # the head gives some up
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_NPC_HAIR_SHARE', None)          # unset: the default, whole; this cap does not
            self.assertEqual(list(_budget_quotas(shapes, 480, 666, None, None)), list(head))   # fit: the head split

    @needs_numpy
    def test_hair_covers_the_back_of_the_head(self):
        from npc_geometry import bake
        out = {}
        for mode in ('plain', 'head'):
            parts = []
            with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': mode, 'AMIWIND_NPC_HEAD_REDUCER': 'locked'}):
                frames, faces, _, _ = bake(self.shapes(), self.materials, {}, self.palette, budget=480,
                                           head_detail='budget', face_parts=parts)
            out[mode] = skin_share(frames, faces, parts) + (parts.count(1),)
        share, rays, hair_faces = out['head']
        self.assertGreater(rays, 100)
        # the hair covers the back of the head (the rest: grazing rays at the cap's rim); measured on this fixture
        # 27 October 2026: plain 37 % of the rays see skin, head 5 %
        self.assertLessEqual(share, .1, out)
        self.assertGreater(out['plain'][0], 4 * share, out)   # the previous split lets the scalp through
        self.assertGreater(hair_faces, out['plain'][2])

    @needs_numpy
    def test_whole_hair_when_it_fits(self):
        """'whole' (the default): a hair cap that fits the model's face limit keeps every authored triangle, so it
        stays one closed shell: no open edge the original does not have, no scalp seen from behind. A cap that
        does not fit falls back to the 'head' split; lower budgets (levels, parts) keep the 'head' split."""
        import numpy as np
        from npc_geometry import _budget_quotas, bake, HAIR_WHOLE_MARGIN
        small = [ball('tri head', 0, 4.0, 16, 32), ball('tri hair', 1, 4.12, 8, 16, back_only=True), body()]
        n = [len(s['faces']) for s in small]
        with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': 'head'}):
            head = _budget_quotas(small, 480, 666, None, None)
            low_head = _budget_quotas(small, 300, 666, None, None)
        self.enterContext(patch.dict(os.environ, {}))                    # restored when the test ends
        os.environ.pop('AMIWIND_NPC_HAIR_SHARE', None)
        whole = _budget_quotas(small, 480, 666, None, None)              # unset: the default, whole
        self.assertEqual(whole[1], n[1])
        # the whole hair sits outside the budget: the head and the body share the budget alone, so the head keeps
        # at least what the 'head' split gave it
        # (a reader of extended models: within 666 the hair takes its whole beside the 'head' split's head)
        self.assertEqual(list(whole[[0, 2]]), list(head[[0, 2]]))
        wide = _budget_quotas(small, 480, 666, None, None, whole_limit=1024)
        self.assertEqual(wide[1], n[1])
        self.assertGreaterEqual(wide[0], head[0])
        self.assertLessEqual(int(wide[0] + wide[2]), 480)
        self.assertGreater(int(wide[0] + wide[2]), 480 - 8)
        self.assertLessEqual(int(whole.sum()), 666 - HAIR_WHOLE_MARGIN)
        self.assertEqual(list(_budget_quotas(small, 300, 666, None, None)), list(low_head))
        # the big cap of self.shapes() does not fit: the 'head' split
        with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': 'head'}):
            big_head = _budget_quotas(self.shapes(), 480, 666, None, None)
        self.assertEqual(list(_budget_quotas(self.shapes(), 480, 666, None, None)), list(big_head))
        parts = []
        with patch.dict(os.environ, {'AMIWIND_NPC_HEAD_REDUCER': 'locked'}):
            frames, faces, _, _ = bake(small, self.materials, {}, self.palette, budget=480, head_detail='budget',
                                       face_parts=parts)
        share, rays = skin_share(frames, faces, parts)
        self.assertGreater(rays, 100)
        # the original meshes, unreduced, seen the same way: the rays at the cap's rim see the head there too
        points, tris, labels, base = [], [], [], 0
        for s in small[:2]:
            points.append(s['positions'][0]); tris.append(np.asarray(s['faces'])[:, [0, 2, 1]] + base)
            labels += [s['part']] * len(s['faces']); base += len(s['positions'][0])
        original, _ = skin_share(np.concatenate(points)[None], np.concatenate(tris), labels)
        self.assertLessEqual(share, original + .005, (share, original))   # no more scalp than the original shows
        self.assertEqual(parts.count(1), n[1])
        hair = np.asarray(faces)[np.asarray(parts) == 1]
        self.assertEqual(open_edges(frames[0], hair), open_edges(small[1]['positions'][0], small[1]['faces']))

    def test_setting_values(self):
        from npc_geometry import hair_share
        for value in ('whole', 'head', 'plain'):
            with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': value}):
                self.assertEqual(hair_share(), value)
        with patch.dict(os.environ, {'AMIWIND_NPC_HAIR_SHARE': 'more'}):
            with self.assertRaises(ValueError):
                hair_share()


if __name__ == '__main__':
    unittest.main()
