"""Synthetic LOD and readable-font contracts, no extracted game data."""
import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from debug_font import readable_atlas,GLYPHS


class DebugFontTests(unittest.TestCase):
    def test_atlas_size_glyph_coverage_and_cell_margins(self):
        raw=readable_atlas()
        self.assertEqual(len(raw),16384)
        self.assertEqual(set(raw),{0,254})
        for c in range(32,127):
            self.assertIn(chr(c),GLYPHS)
            start=(c//16)*8*128+(c%16)*8
            for y in range(8):
                self.assertEqual(raw[start+y*128],0)
                self.assertEqual(raw[start+y*128+7],0)
            self.assertEqual(raw[start+7*128:start+7*128+8],bytes(8))
        self.assertNotEqual(GLYPHS['0'],GLYPHS['O'])
        self.assertNotEqual(GLYPHS['1'],GLYPHS['l'])


@unittest.skipUnless(all(importlib.util.find_spec(n) for n in
    ('numpy','scipy','fast_simplification')), 'optional geometry dependencies')
class StaticLODTests(unittest.TestCase):
    def test_terrain_rocks_get_a_bounded_visual_target(self):
        from static_lod import rock_profile
        self.assertAlmostEqual(rock_profile('meshes/f/Terrain_rock_BC_18.nif',174)['ratio'],64/174)
        self.assertEqual(rock_profile('meshes/f/terrain_rock_tiny.nif',32)['ratio'],1)
        self.assertEqual(rock_profile('meshes/x/ex_nord_rock_01.nif',35),{})
        self.assertEqual(rock_profile('meshes/x/rock_named_house.nif',400),{})

    def test_structural_material_keeps_original_shape_and_uvs(self):
        import numpy as np
        from static_lod import reduce_mesh
        vv=[];ff=[]
        for y in range(8):
            for x in range(8):vv.append([x,y,(x-3.5)**2,x/7,y/7,255,255,255,255])
        for y in range(7):
            for x in range(7):
                a=y*8+x;ff.extend([[a,a+1,a+9,0],[a,a+9,a+8,0]])
        v=np.array(vv,float);f=np.array(ff)
        kept,faces,report=reduce_mesh(v,f,.08,{0})
        self.assertEqual(len(faces),len(f))
        self.assertTrue(np.array_equal(kept[faces[:,:3]],v[f[:,:3]]))
        self.assertEqual(report['preserved_materials'],[0])
        with self.assertRaises(ValueError):reduce_mesh(v,f,.08,{1})

    def test_planar_materials_and_separate_parts_survive_reduction(self):
        import numpy as np
        from static_lod import reduce_mesh
        from mesh_geometry import connected_components
        vv=[];ff=[]
        for material,offset in [(0,0),(1,100)]:
            base=len(vv)
            for y in range(8):
                for x in range(8):vv.append([offset+x,y,0,(offset+x)/4,y/4,255,255,255,255])
            for y in range(7):
                for x in range(7):
                    a=base+y*8+x
                    ff.extend([[a,a+1,a+9,material],[a,a+9,a+8,material]])
        v,f,report=reduce_mesh(np.array(vv,float),np.array(ff),.2)
        self.assertLess(len(f),len(ff))
        self.assertEqual(set(f[:,3]),{0,1})
        self.assertEqual(len(connected_components(v,f)),2)
        self.assertTrue(np.isfinite(v).all())
        self.assertTrue(np.allclose(v[:,3:5],v[:,:2]/4))
        self.assertTrue(np.allclose(v[:,:3].min(0),[0,0,0],atol=.3))
        self.assertTrue(np.allclose(v[:,:3].max(0),[107,7,0],atol=.3))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'optional numpy dependency')
class CollisionTreeTests(unittest.TestCase):
    def test_hidden_authored_collision_is_separate_and_transformed(self):
        from types import SimpleNamespace as NS
        import numpy as np
        from prepare_scenery import model_geometry
        from mwad.scene import unpack_geometry
        class Node:
            def __init__(self, x=0, hidden=False, children=()):
                self.name=b'';self.flags=int(hidden);self.children=children;self.x=x
            def get_transform(self):
                matrix=np.eye(4);matrix[3,0]=self.x
                return NS(as_list=lambda:matrix.tolist())
        class Collision(Node):pass
        class Shape(Node):
            def __init__(self, x=0, hidden=False):
                super().__init__(x,hidden);self.skin_instance=None;self.properties=[]
                self.data=NS(num_vertices=3,num_triangles=1,num_uv_sets=0,uv_sets=[],
                    has_vertex_colors=False,vertices=[NS(x=0,y=0,z=0),NS(x=1,y=0,z=0),NS(x=0,y=1,z=0)],
                    get_triangles=lambda:[(0,1,2)])
        root=Node(5,children=[Shape(),Shape(30,True),Collision(10,True,[Shape(2)])])
        class Data:
            roots=[root]
            def read(self,f):pass
        N=NS(Data=Data,NiAVObject=Node,RootCollisionNode=Collision,NiTriShape=Shape)
        raw=b'NetImmerse File Format, Version 4.0.0.2\n'
        visual,_,bounds,_=model_geometry(raw,N)
        physical,_,cbounds,_=model_geometry(raw,N,collision=True)
        self.assertEqual(bounds,[[5.,0.,0.],[6.,1.,0.]])
        self.assertEqual(cbounds,[[17.,0.,0.],[18.,1.,0.]])
        self.assertEqual(len(unpack_geometry(visual)[1]),1)
        self.assertEqual(len(unpack_geometry(physical)[1]),1)
