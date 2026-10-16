"""The compiled union must retain free passages and expanded obstacle volumes."""
from pathlib import Path
import os
import tempfile
import unittest
from itertools import product
import numpy as np
from scipy.spatial import ConvexHull
from collision_bsp import compile_standing
from player_hull import MINS, MAXS


class CompiledCollisionTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('AMIWIND_TEST_QBSP'), 'requires external qbsp')
    def test_open_arch_and_ramp_match_independent_convex_union(self):
        # Two piers and a lintel leave a genuine passage. A separate tilted
        # slab exercises nonaxial planes and player-box edge bevels.
        boxes=[((-40,-8,0),(-24,8,72)),((24,-8,0),(40,8,72)),
               ((-40,-8,56),(40,8,72)),((55,-12,0),(90,12,2))]
        pieces=[];oracle=[]
        corners=np.array(list(product(*zip(MINS,MAXS))))
        for i,(lo,hi) in enumerate(boxes):
            points=np.array(list(product(*zip(lo,hi))),dtype=float)
            if i==3:points[:,2]+=(points[:,0]-55)*.8
            pieces.append((points,ConvexHull(points),[],0))
            expanded=(points[:,None,:]-corners[None,:,:]).reshape(-1,3)
            oracle.append(ConvexHull(expanded).equations)
        with tempfile.TemporaryDirectory() as tmp:
            nodes,root=compile_standing(pieces,Path(os.environ['AMIWIND_TEST_QBSP']),Path(tmp))
            self.assertEqual((nodes,root),compile_standing(pieces,Path(os.environ['AMIWIND_TEST_QBSP']),Path(tmp)))
        def solid(p):
            n=root;seen=set()
            while n>=0:
                self.assertNotIn(n,seen);seen.add(n)
                plane,front,back=nodes[n]
                n=front if np.dot(p,plane[:3])>=plane[3] else back
            self.assertIn(n,(-1,-2))
            return n==-2
        tested=0
        for p in product(range(-52,105,7),range(-25,26,5),range(-20,95,7)):
            distances=[np.max(np.dot(p,e[:,:3].T)+e[:,3]) for e in oracle]
            # Exclude the quantization/clipper epsilon band at source boundaries.
            if any(abs(d)<.04 for d in distances):continue
            self.assertEqual(solid(p),any(d<0 for d in distances),p);tested+=1
        self.assertGreater(tested,2000)
        self.assertFalse(solid((0,0,25)))
        self.assertTrue(solid((0,0,60)))

class CoplanarRetryTests(unittest.TestCase):
    """CHIM-COLLISION-UNION-FALLBACK-41: a non-convex-face refusal is retried once with coplanar facets merged;
    hulls that compile keep their first result, and every other error is raised as before."""

    def run_with(self, outcomes):
        import collision_bsp
        calls = []

        def fake(pieces, qbsp, cache, grid=64, check_box=None, patch=True, merge_coplanar=False):
            calls.append(merge_coplanar)
            out = outcomes[len(calls) - 1]
            if isinstance(out, Exception):
                raise out
            return out
        saved = collision_bsp.compile_standing_checked_once
        collision_bsp.compile_standing_checked_once = fake
        try:
            return collision_bsp.compile_standing_checked([], 'qbsp', 'cache'), calls
        finally:
            collision_bsp.compile_standing_checked_once = saved

    def test_compiling_hull_is_not_retried(self):
        self.assertEqual(self.run_with(['first']), ('first', [False]))

    def test_non_convex_face_is_retried_with_merged_facets(self):
        error = ValueError('Collision compiler failed (exit 1): CheckFace: Found a non-convex face (error size 28.4)')
        self.assertEqual(self.run_with([error, 'merged']), ('merged', [False, True]))

    def test_other_errors_are_not_retried(self):
        with self.assertRaises(ValueError):
            self.run_with([ValueError('Collision compiler failed (exit 1): leak')])

    def test_failed_retry_names_both_errors(self):
        with self.assertRaises(ValueError) as caught:
            self.run_with([ValueError('a non-convex face'), ValueError('still a non-convex face')])
        self.assertIn('retried with coplanar facets merged', str(caught.exception))
