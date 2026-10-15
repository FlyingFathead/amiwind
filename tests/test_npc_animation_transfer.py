# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic regression for converted limb offsets; no proprietary inputs."""
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src'), str(Path(__file__).resolve().parents[1] / 'tools')]

class AnimationTransfer(unittest.TestCase):
    def setUp(self):
        try:
            import numpy
            import scipy
            from PIL import Image
        except ImportError:
            self.skipTest('Install optional NPC conversion dependencies')

    def bake_transform(self, matrix):
        import numpy as np
        from npc_geometry import bake
        points = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [1., 1., 0.]])
        reduced = np.array([[-.2, .1, .2], [1.1, .1, .2], [.1, 1.1, .2]])
        shift = np.array([2., -3., 4.])
        shape = {'name': 'synthetic calf', 'part': 17,
                 'positions': np.stack([points, points @ matrix.T + shift]),
                 'faces': np.array([[0, 1, 2], [1, 3, 2]]),
                 'uv': points[:, :2], 'colours': np.ones((4, 4)), 'material': 0}
        materials = [{'texture_index': None, 'diffuse': [1., 1., 1.], 'alpha': 1.}]
        with patch('npc_geometry.simplify_shape', return_value=(reduced, np.array([[0, 1, 2]]))):
            frames, faces, uv, skin = bake([shape], materials, {}, bytes(range(256))*3,
                                          quotas=[1], preserve=[False], head_detail='budget')
        np.testing.assert_allclose(frames[0], reduced, atol=1e-12)
        self.assertEqual(frames.shape, (2, 3, 3))
        return frames[1], reduced @ matrix.T + shift

    def test_translation_preserves_offset(self):
        import numpy as np
        actual, expected = self.bake_transform(np.eye(3))
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_rotating_limb_carries_simplification_offset(self):
        import numpy as np
        actual, expected = self.bake_transform(np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]]))
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_scaled_rotating_limb_carries_simplification_offset(self):
        import numpy as np
        actual, expected = self.bake_transform(2*np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]]))
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_arbitrary_rotations_and_uniform_scales(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        rng=np.random.default_rng(846)
        for _ in range(20):
            points=rng.normal(size=(3,3)); point=rng.normal(size=3)
            rotation,_=np.linalg.qr(rng.normal(size=(3,3)))
            if np.linalg.det(rotation)<0:rotation[:,0]*=-1
            scale=rng.uniform(.2,3.); shift=rng.normal(size=3)
            triangles=np.stack((points,scale*points@rotation.T+shift))
            actual=transfer_vertex(point,triangles)
            np.testing.assert_array_equal(actual[0],point)
            np.testing.assert_allclose(actual[1],scale*point@rotation.T+shift,atol=1e-10)

    def test_surface_vertex_follows_triangle_deformation(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        triangles=np.array([[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]],
                            [[1.,2.,3.],[3.,2.,3.],[1.,5.,4.]]])
        weights=np.array([.2,.3,.5]); point=weights@triangles[0]
        np.testing.assert_allclose(transfer_vertex(point,triangles),
                                   np.einsum('v,fvc->fc',weights,triangles),atol=1e-12)

    def test_degenerate_reference_retains_translation_without_nan(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        for points in (np.zeros((3,3)),np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]])):
            point=np.array([.2,.3,.4]); shift=np.array([2.,3.,4.])
            result=transfer_vertex(point,np.stack((points,points+shift)))
            self.assertTrue(np.isfinite(result).all())
            np.testing.assert_allclose(result,[point,point+shift],atol=1e-12)

    def test_collapsed_later_frame_stays_finite(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        triangles=np.array([[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]],np.zeros((3,3))])
        result=transfer_vertex(np.array([.2,.3,.4]),triangles)
        self.assertTrue(np.isfinite(result).all())
        np.testing.assert_array_equal(result[1],np.zeros(3))

    def test_sliver_deformation_does_not_amplify_residual(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        rest=np.array([[0.,0.,0.],[1.,0.,0.],[1.,1e-9,0.]])
        deformed=rest.copy();deformed[2,2]=1e-5
        point=np.array([0.,1.,.2])
        actual=transfer_vertex(point,np.stack((rest,deformed)))
        self.assertTrue(np.isfinite(actual).all())
        self.assertLess(np.linalg.norm(actual[1]),3.)

    def test_nonuniform_deformation_keeps_residual_bounded(self):
        import numpy as np
        from npc_geometry import transfer_vertex
        rest=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
        target=rest*np.array([.01,5.,2.])+[3.,4.,5.]
        point=np.array([.2,.3,2.])
        actual=transfer_vertex(point,np.stack((rest,target)))
        anchor=np.array([.5,.2,.3])@target
        ratio=np.linalg.norm(target-target.mean(axis=0))/np.linalg.norm(rest-rest.mean(axis=0))
        self.assertAlmostEqual(np.linalg.norm(actual[1]-anchor),2.*ratio,places=10)

if __name__ == '__main__':
    unittest.main()
