"""Survey partitions and source-aligned terrain boundaries, without game data."""
import json
import copy
from pathlib import Path
import tempfile
import unittest
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_world_regions import plan, Terrain, map_text, town_handoffs, terrain_triangles
from world_volumes import balanced


class WorldRegionsTests(unittest.TestCase):
    def test_measured_splits_stable_names_and_matching_shared_vertices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def cell(x,split):
                return dict(cell=[x,0],screen=dict(candidate=split),unresolved_placements=0,
                            name='',region='Test')
            report=dict(format='AmiWind world survey 1',terrain=dict(height_seams=[]),
                        settings=dict(overlap_runtime=896),cells=[cell(0,2),cell(-1,1)])
            (root/'world-survey.json').write_text(json.dumps(report))
            _,entries=plan(root)
            self.assertEqual(len(entries),5)
            self.assertEqual([e['name'] for e in entries],[f'vf{i:04d}' for i in range(5)])
            self.assertEqual(entries[0]['cell'],[-1,0])
            terrain=Terrain.__new__(Terrain)
            terrain.cells={(-1,0):0,(0,0):1}
            terrain.heights=np.zeros((2,65,65),np.float32)
            terrain.materials=np.ones((2,16,16),np.uint16)
            for index in range(2):
                for x in range(65):terrain.heights[index,:,x]=(index*64+x)*4
            self.assertEqual(terrain.sample(-32,64)[0],63)
            self.assertEqual(terrain.sample(0,64)[0],64)
            self.assertEqual(terrain.sample(2048,64)[0],128)
            self.assertEqual(terrain.sample(-4096,64),(-512.,0))
            for entry in entries:
                text=map_text(entry,terrain)
                self.assertIn('"info_player_start"',text)
                ox,oy,oz=entry['origin']
                for x in range(entry['coverage'][0][0],entry['coverage'][1][0]+1,128):
                    self.assertEqual((x+ox)%128,0)

    def test_shoreline_retains_small_dry_rise_and_matches_neighbour_edge(self):
        terrain=Terrain.__new__(Terrain)
        terrain.cells={(0,0):0};terrain.heights=np.full((1,65,65),-32,np.float32)
        terrain.materials=np.ones((1,16,16),np.uint16)
        terrain.heights[0,2,2]=32  # Original dry island lost by stride-four corners.
        terrain.heights[0,1,4]=32  # Detail on the shared edge must match both sides.
        self.assertTrue(terrain.shoreline_detail(0,0))
        self.assertTrue(terrain.shoreline_detail(128,0))
        fine=list(terrain_triangles(terrain,0,0));joined=list(terrain_triangles(terrain,128,0))
        self.assertLess(len(fine),32)
        self.assertIn([64,64,8], [point for tri in fine for point in tri])
        def edge(triangles):
            return {tuple(p) for tri in triangles for p in tri if p[0]==128 and 0<=p[1]<=128}
        self.assertEqual(edge(fine),edge(joined))
        self.assertEqual(len(edge(fine)),5)
        # Sampling is global, so overlapping regions produce identical edges.
        self.assertEqual(joined,list(terrain_triangles(terrain,128,0)))

    def test_town_exits_stay_on_ground_inside_larger_sea_enclosure(self):
        root=Path(__file__).resolve().parents[1]
        areas=[]
        for name,file in [('Seyda Neen','seyda_area.json'),('Balmora','balmora.json')]:
            config=json.loads((root/'config'/file).read_text())
            extent=2079 if name=='Seyda Neen' else 3072
            origin=config['centre']
            core=[[origin[k]+sign*extent*4 for k in range(2)] for sign in (-1,1)]
            areas.append(dict(name=name,centre=origin,scale=.25,regions=[dict(core=core)]))
        report=dict(areas=areas)
        towns=town_handoffs(report)
        self.assertEqual(towns[0]['core'],[[-1184,-1696],[1568,1440]])
        self.assertEqual(towns[1]['core'],[[-2976,-2976],[2976,2976]])
        for town in towns:
            for k in range(2):
                self.assertGreaterEqual(town['core'][0][k]-32,town['ground_bounds'][0][k]+64)
                self.assertLessEqual(town['core'][1][k]+32,town['ground_bounds'][1][k]-64)
        bad=copy.deepcopy(report);bad['areas'][0]['centre'][0]+=1
        with self.assertRaisesRegex(ValueError,'transform'):town_handoffs(bad)

    def test_two_partition_balance_includes_boot_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[]
            for index in range(5):
                p=root/f'vf{index:04d}.bsp';p.write_bytes(bytes(4));paths.append(p)
            self.assertEqual(balanced(reversed(paths),4,12),(paths[:2],paths[2:]))
            self.assertEqual(balanced(paths,20,20),([],paths))
            with self.assertRaisesRegex(ValueError,'two-partition budget'):balanced(paths,4,11)



class ContentPreservingRefinementTests(unittest.TestCase):
    def test_parent_slots_and_append_only_siblings_tile_cores(self):
        from prepare_world_regions import refine_entries
        original=[dict(name=f'vf{i:04d}',cell=[i,0],divisions=1,subcell=[0,0],origin=[i*2048+1024,1024,384],core=[[-1024,-1024],[1024,1024]],coverage=[[-1920,-1920],[1920,1920]],converted={'sha256':'old'}) for i in range(3)]
        result=refine_entries(original,[{'parent':'vf0001','cell':[1,0],'divisions':2,'reason':'reserve'}])
        self.assertEqual([e['name'] for e in result],[f'vf{i:04d}' for i in range(6)])
        self.assertEqual(result[0],original[0]);self.assertEqual(result[2],original[2])
        children=[e for e in result if e.get('refinement')]
        self.assertEqual([e['origin'][:2] for e in children],[[2560.,512.],[3584.,512.],[2560.,1536.],[3584.,1536.]])
        self.assertEqual(sum((e['core'][1][0]-e['core'][0][0])*(e['core'][1][1]-e['core'][0][1]) for e in children),2048**2)
        for e in children:
            self.assertEqual(e['coverage'],[[-1408,-1408],[1408,1408]])
            self.assertNotIn('converted',e)
        self.assertIn('converted',original[1])
        with self.assertRaisesRegex(ValueError,'parent differs'):
            refine_entries(original,[{'parent':'vf0099','cell':[1,0],'divisions':2,'reason':'bad'}])

if __name__=='__main__':unittest.main()


class SeydaHandoffGroundTests(unittest.TestCase):
    def test_apron_covers_draw_distance_without_moving_handoff(self):
        from prepare_quake import BOUNDS, GROUND_BOUNDS
        from prepare_seyda_regions import DRAW_DISTANCE, regions
        for axis in range(2):
            self.assertGreaterEqual(BOUNDS[0][axis]+64-GROUND_BOUNDS[0][axis], DRAW_DISTANCE)
            self.assertGreaterEqual(GROUND_BOUNDS[1][axis]-(BOUNDS[1][axis]-64), DRAW_DISTANCE)
        east = next(r for r in regions() if r['core'][0][0] <= 1024 < r['core'][1][0] and r['core'][0][1] <= -768 < r['core'][1][1])
        self.assertGreaterEqual(east['coverage'][1][0],1600+DRAW_DISTANCE)
        self.assertEqual(len(regions()),64)
        for region in regions():
            for axis in range(2):
                self.assertLessEqual(region['coverage'][0][axis],region['core'][0][axis])
                self.assertGreaterEqual(region['coverage'][1][axis],region['core'][1][axis])

    def test_handoff_triangles_match_world_heights_and_materials(self):
        from prepare_quake import town_ground_triangles, CENTRE, SCALE
        from prepare_world_regions import Terrain, terrain_triangles
        import numpy as np
        grids=[dict(cell=[x,y],heights=[[8*(ix+iy) for ix in range(65)] for iy in range(65)],
                    materials=[[1+(ix//2) for ix in range(16)] for iy in range(16)])
               for y in range(-10,-7) for x in range(-3,0)]
        # Check a tile crossing the reported eastern handoff, including UV material identity.
        ox,oy=(v*SCALE for v in CENTRE)
        actual=[(tri,material) for tri,material in town_ground_triangles(grids)
                if all(1536<=p[0]<=1664 and 0<=p[1]<=128 for p in tri)]
        terrain=Terrain.__new__(Terrain)
        terrain.cells={tuple(g['cell']):i for i,g in enumerate(grids)}
        terrain.heights=np.asarray([g['heights'] for g in grids],float)
        terrain.materials=np.asarray([g['materials'] for g in grids],int)
        expected=[]
        for tri in terrain_triangles(terrain,1536+ox,oy):
            material=terrain.sample(*(sum(p[k] for p in tri)/3 for k in (0,1)))[1]
            expected.append(([[p[0]-ox,p[1]-oy,p[2]] for p in tri],material))
        self.assertEqual(actual,expected)
