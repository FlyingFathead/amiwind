"""Synthetic tilted scenery must compose to the same TES3 world transform."""
import math
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_scenery import reference_rotation, world_bounds
from prepare_mesh_bsp import _instance_key, _prepare_placement


class ReferenceRotationTests(unittest.TestCase):
    def test_tilted_shape_bounds_vertices_and_uvs(self):
        ref={'model_index':1, 'scale':2, 'position':[0,0,0],
             'rotation_radians':[math.pi/2, 0, math.pi/2]}
        # Clockwise Z sends +X to -Y, then clockwise X sends -Y to +Z.
        np.testing.assert_allclose(reference_rotation(ref) @ [1,0,0], [0,0,1], atol=1e-12)
        p=np.array([[1.,0,0],[1,1,0],[1,0,1]])
        axes=np.array([[0.,0],[1,0],[0,1]])
        data=(np.column_stack((p*4,np.zeros((3,2)))), np.array([[0,1,2,0]]),
              [(p,0,axes,np.zeros(2),np.array([1.,0,0]))], [], {})
        surfaces,_,low,high=_prepare_placement((ref,data,64,(0,0),None))
        q,normal,uv,offset,_,_=surfaces[0]
        yaw=np.array([[0.,1,0],[-1,0,0],[0,0,1]])
        np.testing.assert_allclose(q @ yaw.T, p @ reference_rotation(ref).T*2, atol=1e-12)
        np.testing.assert_allclose(q@uv+offset, p@axes*64, atol=1e-12)
        bounds=world_bounds([[0,0,0],[1,0,0]],ref)
        np.testing.assert_allclose(bounds, [[0,0,0],[0,0,2]], atol=1e-12)

    def test_tilted_instances_with_different_yaws_do_not_share(self):
        ref={'model_index':1, 'scale':1, 'rotation_radians':[.2,.3,0]}
        other={**ref, 'rotation_radians':[.2,.3,1]}
        self.assertNotEqual(_instance_key(ref,None),_instance_key(other,None))
        ref['rotation_radians']=[0,0,0];other['rotation_radians']=[0,0,1]
        self.assertEqual(_instance_key(ref,None),_instance_key(other,None))
