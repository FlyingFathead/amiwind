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

    def test_shared_material_rim_keeps_source_geometry_and_uvs(self):
        import numpy as np
        from static_lod import reduce_mesh
        vertices = []
        faces = []
        for material in (0, 1):
            base = len(vertices)
            for y in range(5):
                for x in range(5):
                    vertices.append([x, y, material*y, x/4, y/4])
            for y in range(4):
                for x in range(4):
                    a = base + y*5 + x
                    faces.extend([[a, a+1, a+6, material], [a, a+6, a+5, material]])
        v, f = np.array(vertices, float), np.array(faces)
        reduced, triangles, report = reduce_mesh(v, f, .2, preserve_shared_seams=True)
        self.assertEqual(report['preserved_materials'], [0, 1])
        self.assertTrue(np.array_equal(reduced[triangles[:, :3]], v[f[:, :3]]))
        self.assertEqual(len(triangles), len(f))

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


def _two_plates():
    """Two curved open plates (materials 0 and 1) meeting along one rim, like
    the Silt Strider's shell plates; synthetic, no game data."""
    import numpy as np
    vv, ff = [], []
    for material, (y0, z0) in enumerate(((0, 0.), (9, 0.))):
        base = len(vv)
        for y in range(10):
            for x in range(10):
                yy = y0 + y
                vv.append([x, yy, z0 + 3 * np.sin(x / 3) + 2 * np.cos(yy / 4), x / 9, y / 9, 255, 255, 255, 255])
        for y in range(9):
            for x in range(9):
                a = base + y * 10 + x
                ff.extend([[a, a + 1, a + 11, material], [a, a + 11, a + 10, material]])
    return np.array(vv, float), np.array(ff)


@unittest.skipUnless(all(importlib.util.find_spec(n) for n in
    ('numpy','scipy','fast_simplification')), 'optional geometry dependencies')
class BoundaryLockedLODTests(unittest.TestCase):
    """MESH-LOD-OPEN-SEAMS-33: reduced open parts must stay joined at their rims."""

    def _rim(self, v, f, material):
        from static_lod import boundary_vertices
        import numpy as np
        mf = f[f[:, 3] == material]
        points, inverse = np.unique(v[mf[:, :3], :3].reshape(-1, 3), axis=0, return_inverse=True)
        return {tuple(points[i]) for i in boundary_vertices(inverse.reshape(-1, 3))}

    def test_locked_reduction_keeps_every_rim_and_the_shared_seam(self):
        import numpy as np
        from static_lod import reduce_mesh
        v, f = _two_plates()
        out_v, out_f, report = reduce_mesh(v, f, .3, lock_boundaries=True)
        self.assertLess(len(out_f), len(f))
        self.assertEqual(set(out_f[:, 3]), {0, 1})
        self.assertGreater(report['locked_vertices'], 0)
        for material in (0, 1):
            kept = {tuple(p) for p in out_v[out_f[out_f[:, 3] == material, :3], :3].reshape(-1, 3)}
            self.assertTrue(self._rim(v, f, material) <= kept)
        seam = self._rim(v, f, 0) & self._rim(v, f, 1)
        self.assertEqual(len(seam), 10)

    def test_locked_reduction_keeps_source_winding(self):
        import numpy as np
        from static_lod import reduce_mesh
        v, f = _two_plates()
        out_v, out_f, _ = reduce_mesh(v, f, .3, lock_boundaries=True)
        t = out_v[out_f[:, :3], :3]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        s = v[f[:, :3], :3]
        sn = np.cross(s[:, 1] - s[:, 0], s[:, 2] - s[:, 0])
        sn /= np.linalg.norm(sn, axis=1)[:, None]
        n /= np.linalg.norm(n, axis=1)[:, None]
        # Each output face stays within 60 degrees (LOCKED_MAX_TURN) of the
        # nearest same-material source face: none is flipped or edge-on.
        for face, normal, centre in zip(out_f, n, t.mean(axis=1)):
            same = f[:, 3] == face[3]
            nearest = np.argmin(((s[same].mean(axis=1) - centre) ** 2).sum(axis=1))
            self.assertGreater(float(normal @ sn[same][nearest]), .45)

    def test_default_reducer_still_moves_rims(self):
        """The earlier reducer stays selectable and unchanged (DON'T DELETE ANY
        METHOD); this pins why the locked mode exists: it pulls rims in."""
        from static_lod import reduce_mesh
        v, f = _two_plates()
        out_v, out_f, report = reduce_mesh(v, f, .3)
        self.assertNotIn('locked_vertices', report)
        kept = {tuple(p) for p in out_v[out_f[:, :3], :3].reshape(-1, 3)}
        self.assertFalse(self._rim(v, f, 0) <= kept)

    def test_quadric_simplify_never_moves_a_locked_vertex(self):
        import numpy as np
        from mold_shell import quadric_simplify
        v, f = _two_plates()
        mf = f[f[:, 3] == 0]
        points, inverse = np.unique(v[mf[:, :3], :3].reshape(-1, 3), axis=0, return_inverse=True)
        tri = inverse.reshape(-1, 3)
        locked = {i for i, p in enumerate(points) if p[0] in (0, 9) or p[1] in (0, 9)}
        out_p, out_t = quadric_simplify(points, tri, [40], locked=locked)[40]
        kept = {tuple(p) for p in out_p[np.unique(out_t)]}
        self.assertTrue({tuple(points[i]) for i in locked} <= kept)
        self.assertLess(len(out_t), len(tri))

    def test_strider_profile_locks_boundaries_in_every_town(self):
        """Balmora reads Seyda Neen's strider profile (one shared asset and
        profile); both towns and the CHIM converter get the same reduction."""
        from scenery_selection import load_groups
        from static_lod import profile_reduction
        from town_regions import visual_profile
        shared = load_groups()['silt_strider']['visual_profiles']['meshes/r/siltstrider.nif']
        self.assertTrue(shared['lock_boundaries'])
        # Boundary-locked 0.45 (MESH-LOD-OPEN-SEAMS-33, v0.0.34): every seam and rim stays closed and the
        # strider's CHIM block (464,336 B) is below the v0.0.32 profile's (477,568 B), so CHIM Balmora's
        # active ring keeps room (CHIM-STRIDER-RING-33). The full-detail variant E (shell, arms and legs
        # kept) stays selectable through preserve_shape_prefixes but does not fit the ring.
        self.assertLessEqual(shared['ratio'], 0.45)
        self.assertNotIn('preserve_shape_prefixes', shared)
        self.assertEqual(profile_reduction(shared), {'preserve_shared_seams': False, 'lock_boundaries': True,
                                                     'agg': 7.0, 'preserve_border': False})
        self.assertEqual(visual_profile('meshes/r/siltstrider.nif', 5600), shared)
        self.assertEqual(profile_reduction({}), {'preserve_shared_seams': False, 'lock_boundaries': False,
                                                 'agg': 7.0, 'preserve_border': False})

    def test_converter_and_estimates_share_one_profile_reduction(self):
        root = Path(__file__).resolve().parents[1] / 'tools'
        for name in ('prepare_mesh_bsp.py', 'asset_census.py', 'world_estimate_data.py'):
            text = (root / name).read_text(encoding='utf-8')
            self.assertIn('reduce_for_profile(', text, name)
            self.assertNotIn('reduce_mesh(', text, name)

    def test_profile_keeps_named_shapes_unreduced(self):
        from static_lod import reduce_for_profile
        v, f = _two_plates()
        materials = [{'source_shape': 'Tri shell 0'}, {'source_shape': 'Tri claw 0'}]
        profile = {'ratio': .3, 'lock_boundaries': True, 'preserve_shape_prefixes': ['Tri shell']}
        out_v, out_f, report = reduce_for_profile(v, f, profile, materials, 'fixture')
        self.assertEqual(int((out_f[:, 3] == 0).sum()), int((f[:, 3] == 0).sum()))
        self.assertLess(int((out_f[:, 3] == 1).sum()), int((f[:, 3] == 1).sum()))
        self.assertEqual(report['preserved_materials'], [0])
        with self.assertRaises(ValueError):
            reduce_for_profile(v, f, {**profile, 'preserve_shape_prefixes': ['Tri missing']}, materials, 'fixture')
        with self.assertRaises(ValueError):
            reduce_for_profile(v, f, profile, None, 'fixture')
        self.assertIs(reduce_for_profile(v, f, {}, materials)[0], v)


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
