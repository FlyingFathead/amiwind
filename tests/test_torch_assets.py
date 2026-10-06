"""Synthetic attachment checks; no original game meshes are embedded."""
import unittest
import numpy as np
from npc_geometry import rigid_attachment
from prepare_torch import TorchSkeleton, camera_space, view_parts


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


    def test_first_person_torch_profile_preserves_distal_parts_and_legacy(self):
        # Public synthetic attachment records, no original mesh coordinates.
        parts=[{'slot':slot,'attach':name,'mesh':'synthetic/'+name,'weight':[1,2,3]}
               for slot,name in ((6,'Right Hand'),(7,'Left Hand'),(8,'Right Wrist'),
                                 (9,'Left Wrist'),(11,'Right Forearm'),(12,'Left Forearm'),
                                 (13,'Right Upper Arm'),(14,'Left Upper Arm'),(10,'Shield Bone'))]
        before=[dict(part) for part in parts]
        selected=view_parts(parts)
        self.assertEqual([p['slot'] for p in selected],[6,7,8,9,11,12,10])
        for part in selected:
            self.assertIs(part,parts[[p['slot'] for p in parts].index(part['slot'])])
        self.assertEqual(parts,before)
        self.assertEqual(view_parts(parts,'legacy'),before)
        self.assertEqual(view_parts(selected),selected)
        self.assertEqual(view_parts([], 'hidden'),[])
        with self.assertRaises(ValueError):view_parts(parts,'unknown')


    def test_batch_cache_is_bound_to_owned_data_and_reuses_inputs(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from prepare_torch import TorchSource
        with TemporaryDirectory() as folder:
            owned=Path(folder)/'owned';owned.mkdir()
            (owned/'Morrowind.esm').write_bytes(b'synthetic master')
            (owned/'Morrowind.bsa').write_bytes(b'synthetic archive')
            fields=[('NAME',b'torch\0'),('MODL',b'synthetic-torch.nif\0')]
            kinds={'BODY':{},'RACE':{}}
            with patch('prepare_torch.load_master',return_value=(kinds,None,None)) as master, \
                 patch('prepare_torch.records',return_value=[('LIGH',0,b'synthetic')]), \
                 patch('prepare_torch.subrecords',return_value=fields), \
                 patch('prepare_torch.BSA') as archive, \
                 patch('prepare_torch.Assets') as assets, \
                 patch('prepare_torch.TorchSkeleton') as skeleton:
                source=TorchSource(owned)
                for unused in range(3):
                    actual=source.for_data(owned)
                    self.assertIs(actual[0],kinds)
                    self.assertIs(actual[1],assets.return_value)
                    self.assertEqual(actual[2],'synthetic-torch.nif')
                    self.assertIs(actual[3],skeleton.return_value)
                master.assert_called_once();archive.assert_called_once()
                assets.assert_called_once();skeleton.assert_called_once()
                with self.assertRaises(ValueError):source.for_data(Path(folder)/'different')
