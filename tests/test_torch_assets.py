"""Synthetic attachment checks; no original game meshes are embedded."""
import unittest
import numpy as np
from npc_geometry import rigid_attachment
from prepare_torch import TorchSkeleton, camera_space


class TorchAssets(unittest.TestCase):
    def test_carried_light_rotation_precedes_offset_and_bone(self):
        part={'attach':'Shield Bone','carried_light':True}
        offset=np.array([-11.,1.,-2.])
        grip=rigid_attachment(part,offset)
        tip=np.array([0.,0.,22.,1.])
        np.testing.assert_allclose((tip@grip)[:3],offset+[0,22,0])
        np.testing.assert_allclose((np.array([0.,0.,0.,1.])@grip)[:3],offset)
        # Ordinary body attachment still mirrors left parts; torch does not.
        self.assertAlmostEqual(np.linalg.det(grip[:3,:3]),1)
        self.assertAlmostEqual(np.linalg.det(rigid_attachment({'attach':'Left Hand'},offset)[:3,:3]),-1)
        camera=np.array([1.,2.,3.]);base=(tip@grip)[:3]
        np.testing.assert_allclose(camera_space([base,base+[0,0,2]],camera)[1]-camera_space(base,camera),[0,0,2])

    def test_only_left_arm_uses_torch_timeline(self):
        skeleton=TorchSkeleton.__new__(TorchSkeleton)
        skeleton.parents={'root':None,'bip01 l clavicle':'root','left hand':'bip01 l clavicle',
                          'shield bone':'left hand','right hand':'root','camera':'root'}
        skeleton.nodes=dict.fromkeys(skeleton.parents)
        skeleton.events={'torch: start':46.,'torch: stop':48.,'idlehh: start':100.,'idlehh: stop':104.}
        calls={}
        def local(name,time):
            calls[name]=time
            result=np.eye(4);result[3,0]=time;return result
        skeleton.local=local
        pose=skeleton.pose(47.)
        np.testing.assert_allclose(pose('Shield Bone')[3,0],102+47*3)
        pose('right hand');pose('camera')
        self.assertEqual(calls,{'root':102.,'bip01 l clavicle':47.,'left hand':47.,
                               'shield bone':47.,'right hand':102.,'camera':102.})
