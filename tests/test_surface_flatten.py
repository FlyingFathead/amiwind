"""Panel projection preserves source geometry and supports an off switch."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from surface_flatten import bake_panel, load_profiles, mounting_shift

class SurfaceFlattenTests(unittest.TestCase):
    def test_front_texture_winding_and_sources(self):
        v=np.array([[x,y,z,u,w,255,255,255,255] for y in (-2,2)
                    for x,z,u,w in [(0,0,0,0),(2,0,1,0),(2,2,1,1),(0,2,0,1)]],float)
        f=np.array([[0,1,2,0],[0,2,3,0],[4,5,6,1],[4,6,7,1]])
        before_v,before_f=v.copy(),f.copy()
        colors=[np.full((2,2,3),[120,30,10],dtype=np.uint8),np.full((2,2,3),[10,30,120],dtype=np.uint8)]
        out,faces,rgb,report=bake_panel(v,f,[{'diffuse':[1,1,1]}]*2,lambda i:colors[i],
            {'axis':1,'facing':-1,'plane':0,'texture_size':16,'type':'decorative_windows'})
        np.testing.assert_array_equal(v,before_v)
        np.testing.assert_array_equal(f,before_f)
        np.testing.assert_array_equal(out[:,1],0)
        np.testing.assert_array_equal(rgb,np.broadcast_to([120,30,10],rgb.shape))
        self.assertLess(np.cross(out[1,:3]-out[0,:3],out[2,:3]-out[0,:3])[1],0)
        self.assertEqual(len(faces),2)
        self.assertEqual(report['collision'],'unchanged source geometry')

    def test_type_off_removes_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            for enabled in (True,False):
                p.write_text(json.dumps({'types':{'windows':{'flatten':enabled,'models':{'window.nif':{'axis':1}}}}}))
                self.assertEqual(bool(load_profiles(p)),enabled)
            p.write_text('{"types":{"windows":{"flatten":"false","models":{}}}}')
            with self.assertRaises(ValueError):load_profiles(p)

    def test_mounting_follows_wall_and_rejects_missing_support(self):
        wall=np.array([[[0,2,0],[2,2,0],[2,2,2]],[[0,2,0],[2,2,2],[0,2,2]]],float)
        self.assertAlmostEqual(mounting_shift([1,0,1],[0,-1,0],wall),-1.5)
        with self.assertRaises(ValueError):mounting_shift([10,0,1],[0,-1,0],wall)
        with self.assertRaises(ValueError):mounting_shift([1,0,1],[0,1,0],wall)

    def test_flatten_only_profile_runs_through_converter(self):
        from mwad.scene import pack_geometry
        from prepare_mesh_bsp import _prepare_model
        import hashlib
        v=[[x,y,z,u,w,255,255,255,255] for y in (-2,2)
           for x,z,u,w in [(0,0,0,0),(8,0,1,0),(8,8,1,1),(0,8,0,1)]]
        f=[[0,1,2,0],[0,2,3,0],[4,5,6,0],[4,6,7,0]]
        raw=pack_geometry(v,f,1)
        record={'source':'window.nif','offset':0,'bytes':len(raw),
                'sha256':hashlib.sha256(raw).hexdigest(),
                'materials':[{'texture_index':None,'diffuse':[1,1,1]}]}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'scene.mwpak';p.write_bytes(raw)
            _,data=_prepare_model((0,record,{'flatten':{'axis':1,'facing':-1,'plane':0,
                                  'type':'windows'}},p,[]))
            self.assertEqual(len(data[2]),1)
            self.assertTrue(data[3])
            self.assertEqual(p.read_bytes(),raw)
            np.testing.assert_array_equal(data[0],v)
