import unittest
from terrain_visual_cull import TerrainVolume
class TerrainCullTests(unittest.TestCase):
 def terrain(self):return TerrainVolume([[[0,0,0],[10,0,10],[10,10,10]],[[0,0,0],[10,10,10],[0,10,0]]],-20,.5)
 def test_sloped_buried_and_above(self):
  p=[[4,2,-1],[5,2,-1],[5,3,-1],[4,3,-1]]
  self.assertEqual(self.terrain().clip(p)[1],'fully_buried')
  self.assertEqual(self.terrain().clip([[x,y,12] for x,y,z in p])[1],'unchanged')
 def test_stilt_crosses_ground(self):
  p=[[4,2,-5],[5,2,-5],[5,2,12],[4,2,12]]
  parts,status=self.terrain().clip(p);self.assertEqual(status,'crossing_clipped')
  self.assertTrue(parts);self.assertTrue(all(p[2]>=p[0]-.500001 for poly in parts for p in poly))
 def test_holes_and_below_solid_depth_retained(self):
  t=TerrainVolume([[[0,0,0],[10,0,0],[0,10,0]]],-20)
  p=[[8,8,-2],[9,8,-2],[9,9,-2],[8,9,-2]]
  self.assertEqual(t.clip(p)[1],'unchanged')
  self.assertEqual(t.clip([[1,1,-30],[2,1,-30],[2,2,-30]])[1],'unchanged')
 def test_shore_piling_water_not_input(self):
  t=TerrainVolume([[[0,0,-10],[10,0,-10],[0,10,-10]]],-20)
  self.assertEqual(t.clip([[1,1,-5],[2,1,-5],[2,2,-5]])[1],'unchanged')
 def test_shared_placement_requires_each_proof(self):
  p=[[1,1,-2],[2,1,-2],[2,2,-2]];t=self.terrain()
  self.assertEqual(t.clip(p)[1],'fully_buried')
  self.assertEqual(t.clip([[x+20,y,z] for x,y,z in p])[1],'unchanged')
import unittest
from terrain_visual_cull import TerrainVolume,cull_surfaces,resolve_policy
import numpy as np
class PolicyAndAssemblyTests(unittest.TestCase):
 def test_precedence_and_false(self):
  c={'default':True,'cells':{'-1,2':False},'subcells':{'sn045':True},'bsps':{'SN045.BSP':False}}
  self.assertFalse(resolve_policy(c,map_identity='sn045',cell_identity='-1,2',subcell_identity='sn045')['enabled'])
  self.assertTrue(resolve_policy(c,map_identity='sn045.bsp',force=True)['enabled'])
  with self.assertRaises(ValueError):resolve_policy({'default':'false'})
  with self.assertRaises(ValueError):resolve_policy({'bsps':{'a':True,'A.BSP':False}})
 def test_uv_collision_and_shared_no_variant(self):
  t=TerrainVolume([[[0,0,0],[10,0,0],[0,10,0]]],-20)
  q=np.array([[1,1,-5],[2,1,-5],[2,1,5],[1,1,5.]])
  n=np.array([0,-1,0]);ax=np.array([[1,0],[0,0],[0,1.]]);off=np.array([2.,3.]);s=(q,n,ax,off,0,None)
  clipped,report=cull_surfaces([s],t,[(np.zeros(3),0)])
  self.assertEqual(report['crossing_clipped'],1)
  self.assertAlmostEqual(clipped[0][0][:,2].min(),-.5)
  self.assertIs(clipped[0][2],ax);self.assertIs(clipped[0][3],off)
  shared,report=cull_surfaces([s],t,[(np.zeros(3),0),(np.array([20,0,0]),0)])
  self.assertIs(shared[0],s);self.assertEqual(report['shared_or_lightmapped_retained'],1)
  lit=(q,n,ax,off,0,b'original lightmap');retained,report=cull_surfaces([lit],t,[(np.zeros(3),0)])
  self.assertIs(retained[0],lit)

class OverlapTests(unittest.TestCase):
 def test_nonnegative_and_independent_override_precedence(self):
  c={'default':True,'overlap':.5,'cells':{'Seyda Neen':{'overlap':2}},'subcells':{'sn045':{'enabled':False}},'bsps':{'SN045.BSP':{'overlap':0}}}
  p=resolve_policy(c,map_identity='sn045',cell_identity='Seyda Neen',subcell_identity='sn045')
  self.assertFalse(p['enabled']);self.assertEqual(p['overlap'],0);self.assertEqual(p['overlap_provenance'],'bsps')
  self.assertEqual(resolve_policy(c,map_identity='sn045',overlap_force=1.25)['overlap'],1.25)
  for bad in (-1,float('nan'),float('inf'),True,'0'):
   with self.assertRaises(ValueError):resolve_policy({'overlap':bad})
 def test_overlap_zero_and_seabed_not_water(self):
  ground=[[[0,0,-10],[10,0,-10],[0,10,-10]]]
  p=[[1,1,-15],[2,1,-15],[2,1,-5],[1,1,-5]]
  for overlap in (0.,.5,2.):
   t=TerrainVolume(ground,-20,overlap);pieces,status=t.clip(p)
   self.assertEqual(status,'crossing_clipped')
   self.assertAlmostEqual(min(v[2] for part in pieces for v in part),-10-overlap)
   # Everything between seabed and water level zero remains visible.
   self.assertEqual(t.clip([[1,1,-5],[2,1,-5],[2,2,-5]])[1],'unchanged')

class BspStageTests(unittest.TestCase):
 def test_disabled_and_no_land_preserve_exact_original_bytes(self):
  from cull_bsp_terrain import cull_bsp
  from test_share_bsp_geometry import repeated_geometry
  raw=repeated_geometry()
  for enabled in (False,True):
   result,receipt=cull_bsp(raw,resolve_policy(force=enabled),require_canonical=False) # isolated legacy algorithm fixture, never production acceptance
   self.assertEqual(result,raw);self.assertTrue(receipt['unchanged'])

if __name__=='__main__':unittest.main()


class CoplanarBoundaryRegression(unittest.TestCase):
    def test_coplanar_prism_side_is_not_duplicated(self):
        from terrain_visual_cull import TerrainVolume
        terrain=TerrainVolume([[[0,0,0],[10,0,0],[0,10,0]]],-10,0.5)
        pieces,status=terrain.clip([[1,0,-2],[3,0,-2],[3,0,-1],[1,0,-1]])
        self.assertEqual(status,'fully_buried')
        self.assertEqual(pieces,[])

    def test_above_ground_tiny_sliver_is_retained(self):
        from terrain_visual_cull import TerrainVolume,_area
        terrain=TerrainVolume([[[0,0,0],[10,0,0],[0,10,0]]],-10,0.5)
        source=[[1,0,1],[1.000001,0,1],[1.000001,0,1.000001],[1,0,1.000001]]
        pieces,status=terrain.clip(source)
        self.assertEqual(status,'unchanged')
        self.assertGreater(_area(pieces[0]),0)


class GlobalLocalEnvelopeRegression(unittest.TestCase):
    def test_higher_global_ground_does_not_cut_above_local_ground(self):
        from terrain_visual_cull import TerrainVolume,IntersectedTerrainVolume
        local=TerrainVolume([[[0,0,0],[10,0,0],[0,10,0]]],-10,0.5)
        global_land=TerrainVolume([[[0,0,10],[10,0,10],[0,10,10]]],-10,0.5)
        terrain=IntersectedTerrainVolume(local,global_land)
        q=[[1,1,2],[2,1,2],[2,2,2],[1,2,2]]
        self.assertEqual(terrain.clip(q)[1],'unchanged')
        buried=[[1,1,-2],[2,1,-2],[2,2,-2],[1,2,-2]]
        self.assertEqual(terrain.clip(buried)[1],'fully_buried')
