"""Synthetic coarse/fine LAND edge regression; no game data."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
import numpy as np
from prepare_world_regions import Terrain,terrain_triangles
from prepare_quake import town_ground_triangles,CENTRE,SCALE

def flat():
 terrain=Terrain.__new__(Terrain);terrain.cells={(0,0):0}
 terrain.heights=np.full((1,65,65),40.,dtype=float)
 terrain.materials=np.ones((1,16,16),dtype=int)
 return terrain
def edge_points(tris,axis,coordinate,lo,hi):
 return {tuple(p) for tri in tris for p in tri if p[axis]==coordinate and lo<=p[1-axis]<=hi}

class TerrainBoundaryStitchTests(unittest.TestCase):
 def test_no_required_edges_retains_default_dry_path(self):
  terrain=flat();self.assertEqual(len(list(terrain_triangles(terrain,0,0))),2)
 def test_forced_dry_edge_keeps_all_original_samples(self):
  for edge,axis,coordinate in [(0,1,0),(1,0,128),(2,1,128),(3,0,0)]:
   terrain=flat();tris=list(terrain_triangles(terrain,0,0,required_edge_samples={edge}))
   actual=edge_points(tris,axis,coordinate,0,128)
   expected={(float(x),float(y),10.) for x,y in ([(i,coordinate) for i in range(0,129,32)] if axis==1 else [(coordinate,i) for i in range(0,129,32)])}
   self.assertEqual(actual,expected)
 def test_forced_nonlinear_edge_is_not_flattened(self):
  terrain=flat();terrain.heights[0,2,4]=120.
  tris=list(terrain_triangles(terrain,0,0,required_edge_samples={1}))
  self.assertIn((128.,64.,30.),edge_points(tris,0,128,0,128))
  self.assertGreater(len(tris),2)
 def test_a_steep_bank_keeps_its_top_without_dents(self):
  # BALMORA-GROUND-DENTS-51: Balmora's canal bank (cell -3,-2): the tile's west column lies in the water, the bank
  # rises inside it and the east columns are the street. Only the land/water flips were added, so the bank top sagged
  # to the coarse plane between them; every interior sample now lies within SHORE_TOLERANCE of the ground.
  from prepare_world_regions import SHORE_TOLERANCE
  terrain=flat()
  for iy in range(65):
   for ix,h in enumerate((-200.,-120.,40. if iy%2 else 100.,168.,168.)):terrain.heights[0,iy,ix]=h
  tris=list(terrain_triangles(terrain,0,0))
  def ground(x,y):
   for a,b,c in tris:
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
    if min(u,v,1-u-v)>=-1e-8:return u*a[2]+v*b[2]+(1-u-v)*c[2]
  for dy in (32,64,96):
   for dx in (32,64,96):
    self.assertLessEqual(abs(ground(dx,dy)-terrain.heights[0,dy//32,dx//32]*.25),SHORE_TOLERANCE+1e-9,(dx,dy))
 def test_invalid_edge_is_rejected(self):
  for edges in [{-1},{4},{True},{1.5}]:
   with self.assertRaises(ValueError):list(terrain_triangles(flat(),0,0,required_edge_samples=edges))
 def test_town_dry_port_boundary_matches_in_xyz(self):
  ox,oy=(v*SCALE for v in CENTRE)
  grids=[]
  for cy in range(-10,-7):
   for cx in range(-3,0):
    h=np.full((65,65),40.,dtype=float)
    for iy in range(65):
     for ix in range(65):
      localx=cx*2048+ix*32-ox;localy=cy*2048+iy*32-oy
      if localx==0 and 896<=localy<=1024 and localy not in (896,1024):h[iy,ix]=120.
    grids.append({'cell':[cx,cy],'heights':h,'materials':np.ones((16,16),dtype=int)})
  tris=[tri for tri,_ in town_ground_triangles(grids)]
  west=[tri for tri in tris if all(-128<=p[0]<=0 and 896<=p[1]<=1024 for p in tri)]
  east=[tri for tri in tris if all(0<=p[0]<=128 and 896<=p[1]<=1024 for p in tri)]
  self.assertEqual(edge_points(west,0,0,896,1024),edge_points(east,0,0,896,1024))
  self.assertEqual(len(edge_points(west,0,0,896,1024)),5)

if __name__=='__main__':unittest.main()
