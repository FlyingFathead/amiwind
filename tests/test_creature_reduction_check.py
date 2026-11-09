"""The creature bake's lost-surface check (CREATURE-RACER-MESH-SPIKE-58): a thin chain whose faces the reduction
collapsed is found, kept whole in a second bake with the budget grown by its faces, and the second bake is kept only
when it loses less."""
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'src'), os.path.join(ROOT, 'tools')]

import creature_library as L  # noqa: E402
import npc_geometry as G  # noqa: E402


def strip(n, x0=0.0, length=40.0, width=1.0):
    """A thin chain along -z: n segments of two triangles."""
    v, f = [], []
    for i in range(n + 1):
        z = -length * i / n
        v += [(x0, 0, z), (x0 + width, 0, z)]
    for i in range(n):
        a = 2 * i
        f += [(a, a + 1, a + 2), (a + 1, a + 3, a + 2)]
    return np.array(v, float), np.array(f, int)


def shape(name, v, f):
    return {'name': name, 'part': -1, 'positions': v[None], 'faces': f}


class FakeBake:
    """Stands in for npc_geometry.bake: a shape keeps its faces when minimum_faces asks for them, else the chain loses
    its lower half (vertices kept, faces gone, as the cliff racer's tail did)."""
    def __init__(self):
        self.budgets = []

    def __call__(self, shapes, materials, textures, palette, budget, minimum_faces=None):
        self.budgets.append(budget)
        verts, faces, off = [], [], 0
        for s in shapes:
            v, f = s['positions'][0], s['faces']
            keep = f if (minimum_faces or {}).get(s['name'], 0) >= len(f) else f[:max(1, len(f) // 2)]
            verts.append(v)
            faces.append(keep + off)
            off += len(v)
        return np.concatenate(verts)[None], np.concatenate(faces), None, None


class CreatureReductionCheck(unittest.TestCase):
    def setUp(self):
        body = strip(4, x0=-20, length=40, width=40)
        tail = strip(10, x0=0, length=40, width=1)
        self.shapes = [shape('body', *body), shape('tail', *tail)]

    def test_lost_surface_found(self):
        v, f = self.shapes[1]['positions'][0], self.shapes[1]['faces']
        lost = G.lost_shapes(self.shapes[1:], v[None][0], f[:len(f) // 2])
        self.assertIn('tail', lost)
        self.assertGreater(lost['tail'][1], 10)

    def test_whole_model_not_flagged(self):
        allv = np.concatenate([s['positions'][0] for s in self.shapes])
        allf = np.concatenate([self.shapes[0]['faces'], self.shapes[1]['faces'] + len(self.shapes[0]['positions'][0])])
        self.assertEqual(G.lost_shapes(self.shapes, allv, allf), {})

    def test_chain_kept_whole_with_grown_budget(self):
        from unittest import mock
        import model_face_overrides
        # without an entry in config/model-face-overrides.json the grown bake is refused (NPC-BODY-REGRESSION-62)
        with mock.patch.object(model_face_overrides, 'extra_faces', lambda model, kind='npc', path=None: 0):
            *_r, check = L.checked_bake(FakeBake(), self.shapes, [], {}, b'', 480, None, model='test.nif')
        self.assertEqual(check['kept_whole'], [])
        bake = FakeBake()
        with mock.patch.object(model_face_overrides, 'extra_faces', lambda model, kind='npc', path=None: 1000):
            *_r, check = L.checked_bake(bake, self.shapes, [], {}, b'', 480, None, model='test.nif')
        self.assertIn('tail', check['kept_whole'])
        self.assertNotIn('tail', check['lost'])
        self.assertEqual(bake.budgets[0], 480)
        kept = sum(len(s['faces']) for s in self.shapes if s['name'] in check['kept_whole'])
        self.assertEqual(bake.budgets[1], 480 + kept)
        self.assertLessEqual(max(bake.budgets), L.KEEP_BUDGET_CAP)

    def test_worse_rebake_rejected(self):
        calls = []

        def bake(shapes, materials, textures, palette, budget, minimum_faces=None):
            calls.append(budget)
            r = FakeBake()(shapes, materials, textures, palette, budget, None)
            return r        # the second bake is no better: the first stands
        *_r, check = L.checked_bake(bake, self.shapes, [], {}, b'', 480, None)
        self.assertEqual(check['kept_whole'], [])
        self.assertEqual(check['budget'], 480)


class WholeCreature(unittest.TestCase):
    """A profile with 'whole' (the cliff racer, CREATURE-RACER-MESH-SPIKE-58) bakes every source triangle on its
    source vertices (the shared-vertex encoding), never through the reducing bake; past 1,999 vertices it is refused."""
    def test_whole_uses_shared_vertices(self):
        seen = []

        def whole_model(shapes, materials, textures, palette):
            seen.append(len(shapes))
            v = np.concatenate([s['positions'] for s in shapes], axis=1)
            off = np.cumsum([0] + [s['positions'].shape[1] for s in shapes[:-1]])
            return v, np.concatenate([s['faces'] + o for s, o in zip(shapes, off)]), None, None

        def reducing(*a, **k):
            raise AssertionError('a whole creature never goes through the reducing bake')
        shapes = [shape('body', *strip(300, width=40)), shape('tail', *strip(200, width=1))]
        *_r, check = L.checked_bake(reducing, shapes, [], {}, b'', 480, None, whole=True, whole_model=whole_model)
        self.assertEqual(seen, [2])
        self.assertEqual(check['lost'], {})
        self.assertEqual(check['budget'], 1000)

    def test_too_many_vertices_refused(self):
        shapes = [shape('body', *strip(1000, width=40))]       # 2,002 vertices
        with self.assertRaises(ValueError):
            L.checked_bake(FakeBake(), shapes, [], {}, b'', 480, None, whole=True)

    def test_racer_profile_whole(self):
        from prepare_gallery import quality_profiles
        self.assertTrue(quality_profiles()['r/cliffracer.nif'].get('whole'))


if __name__ == '__main__':
    unittest.main()
