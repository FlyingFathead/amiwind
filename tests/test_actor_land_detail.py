# SPDX-License-Identifier: GPL-3.0-only
"""Local dry LAND detail uses the existing sampler and stitches adjoining tiles."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
import prepare_quake as Q
from prepare_world_regions import terrain_triangles


def grids():
    heights=np.full((65,65),400.,dtype=float)
    # Nonlinear but wholly dry original samples, missed by the stride-four corners.
    for j in range(65):
        for i in range(65):heights[j,i]+=8*((i%4)*(j%4))
    return [{'cell':[0,-9],'heights':heights,'materials':np.ones((16,16),dtype=int)}]


def tiles(rows):
    out={}
    for tri,material in rows:
        x=min(p[0] for p in tri);y=min(p[1] for p in tri)
        key=(int(x//128)*128,int(y//128)*128)
        out.setdefault(key,[]).append((tri,material))
    return out


def edge(rows,axis,value,lo,hi):
    return {tuple(p) for tri,_ in rows for p in tri if p[axis]==value and lo<=p[1-axis]<=hi}


class ActorLandDetailTests(unittest.TestCase):
    def build(self,detailed):
        with patch.object(Q,'GROUND_BOUNDS',((4224,512),(4608,896))),patch.object(Q,'AREA',{'terrain_detail_tiles':detailed}):
            return tiles(list(Q.town_ground_triangles(grids())))

    def test_no_detail_keeps_the_existing_two_triangles(self):
        rows=self.build([])
        self.assertEqual(len(rows),9)
        self.assertTrue(all(len(v)==2 for v in rows.values()))

    def test_detail_keeps_all_original_samples_and_exact_triangles(self):
        rows=self.build([[4352,640]])[(4352,640)]
        self.assertEqual(len(rows),32)
        ox,oy=(v*Q.SCALE for v in Q.CENTRE)
        from chim.seyda import audit_terrain
        terrain=audit_terrain(grids())
        expected=[([[p[0]-ox,p[1]-oy,p[2]] for p in tri],1)
                  for tri in terrain_triangles(terrain,4352+ox,640+oy,full_detail=True)]
        self.assertEqual(rows,expected)
        self.assertEqual(len({tuple(p) for tri,_ in rows for p in tri}),25)

    def test_adjacent_edges_match_and_distant_tiles_stay_exact(self):
        before=self.build([]);after=self.build([[4352,640]])
        for key in [(4224,512),(4480,512),(4224,768),(4480,768)]:self.assertEqual(before[key],after[key])
        for key,axis,value,lo,hi in [((4224,640),0,4352,640,768),((4480,640),0,4480,640,768),
                                     ((4352,512),1,640,4352,4480),((4352,768),1,768,4352,4480)]:
            self.assertEqual(edge(after[(4352,640)],axis,value,lo,hi),edge(after[key],axis,value,lo,hi))
            self.assertEqual(len(edge(after[key],axis,value,lo,hi)),5)
        for rows in after.values():
            area=sum(abs((b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]))/2 for (a,b,c),_ in rows)
            self.assertAlmostEqual(area,128*128)

    def test_policy_rejects_malformed_duplicate_and_outside_tiles(self):
        for rows in [None,{},[[1,0]],[[True,0]],[[0.0,0]],[[0]],[[0,0],[0,0]],[[999999,0]]]:
            with self.subTest(rows=rows),self.assertRaises(ValueError):Q.terrain_detail_tiles({'terrain_detail_tiles':rows})
        self.assertEqual(Q.terrain_detail_tiles({}),frozenset())

    def test_declared_tiles_are_only_the_two_measured_support_sites(self):
        self.assertEqual(Q.terrain_detail_tiles(),frozenset({(4352,640),(3072,1280)}))




class OriginalLandDiamondTests(unittest.TestCase):
    class Sampler:
        def sample(self,x,y):
            return 100.+8.*((int(round(x/32))%2)*(int(round(y/32))%2)),1
        def shoreline_detail(self,x,y):return False

    def assert_diamond(self,x,y,origin=(0.,0.)):
        rows=list(terrain_triangles(self.Sampler(),x,y,full_detail=True,grid_origin=origin))
        self.assertEqual(len(rows),32)
        for j in range(4):
            for i in range(4):
                pair=rows[(j*4+i)*2:(j*4+i+1)*2]
                shared={tuple(p) for p in pair[0]} & {tuple(p) for p in pair[1]}
                a=(x+i*32,y+j*32);c=(a[0]+32,a[1]+32)
                expected={a,c} if (round((a[0]+origin[0])/32)+round((a[1]+origin[1])/32))%2==0 else {(c[0],a[1]),(a[0],c[1])}
                self.assertEqual({p[:2] for p in shared},expected)
        return rows

    def test_alternating_nonplanar_original_spacing(self):
        self.assert_diamond(0,0)
        # Odd square has BD and retains the nonplanar original vertex values.
        pair=list(terrain_triangles(self.Sampler(),0,0,full_detail=True))[2:4]
        self.assertEqual({tuple(p) for p in pair[0]} & {tuple(p) for p in pair[1]},
                         {(64,0,100.),(32,32,108.)})

    def test_negative_cells_and_explicit_frame_translation(self):
        for x,y in [(-2048,-2048),(-128,0),(0,-128),(2048,4096)]:self.assert_diamond(x,y)
        self.assert_diamond(0,0,(-2048.,-18432.))
        self.assert_diamond(0,0,(32.,0.))

    def test_full_detail_cell_edges_have_same_source_vertices(self):
        left=self.assert_diamond(-128,-2048);right=self.assert_diamond(0,-2048)
        self.assertEqual({tuple(p) for t in left for p in t if p[0]==0},
                         {tuple(p) for t in right for p in t if p[0]==0})

    def test_coarse_path_unchanged_and_bad_original_alignment_rejected(self):
        expected=[[[0,0,100.],[128,0,100.],[128,128,100.]],
                  [[0,0,100.],[128,128,100.],[0,128,100.]]]
        self.assertEqual(list(terrain_triangles(self.Sampler(),0,0)),expected)
        for origin in [(1.,0.),(float('inf'),0.),(0.,)]:
            with self.subTest(origin=origin),self.assertRaises(ValueError):
                list(terrain_triangles(self.Sampler(),0,0,full_detail=True,grid_origin=origin))

    def test_local_lava_sampler_uses_the_explicit_global_grid_origin(self):
        from chim.build import shoreline_ground
        sample=self.Sampler().sample
        pool={'hull':[[1.,1.],[100.,1.],[100.,100.],[1.,100.]],'top':120.}
        ground=shoreline_ground(sample,np.ones((1,1),int),(0,0),(128,128),128,
                               liquids=[pool],grid_origin=(32.,0.))
        self.assertEqual([[tuple(p) for p in t] for t,_ in ground.tile_list(0,0)],
                         [[tuple(p) for p in t] for t in self.assert_diamond(0,0,(32.,0.))])


if __name__=='__main__':unittest.main()
