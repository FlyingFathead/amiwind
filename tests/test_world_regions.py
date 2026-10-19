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
from prepare_world_regions import layout_refinements
from prepare_world_regions import region_lava, region_terrain_triangles
CEILING=layout_refinements()['survey_source_triangle_limit']


class WorldRegionsTests(unittest.TestCase):
    def test_elevated_lava_keeps_land_depression_and_shared_edge(self):
        terrain=Terrain.__new__(Terrain)
        terrain.cells={(0,0):0};terrain.heights=np.full((1,65,65),600,np.float32)
        terrain.materials=np.ones((1,16,16),np.uint16)
        terrain.heights[0,2,2]=136
        terrain.heights[0,1,4]=136
        entry=dict(origin=[0,0,0],coverage=[[0,0],[512,128]],
                   lava_pools=[dict(hull=[[32,32],[500,32],[500,400],[32,400]],top=480)])
        tris=list(region_terrain_triangles(entry,terrain))
        vertices={tuple(p) for tri in tris for p in tri}
        self.assertIn((64,64,34),vertices)
        self.assertIn((128,32,34),vertices)
        left=[tri for tri in tris if max(p[0] for p in tri)<=128]
        right=[tri for tri in tris if min(p[0] for p in tri)>=128 and max(p[0] for p in tri)<=256]
        edge=lambda ts:{tuple(p) for tri in ts for p in tri if p[0]==128}
        self.assertEqual(edge(left),edge(right))
        remote=[tri for tri in tris if min(p[0] for p in tri)>=384]
        self.assertEqual(remote,list(terrain_triangles(terrain,384,0)))
        self.assertEqual(len(remote),2)
        # The same world-space samples must survive a shifted overlapping map.
        shifted=copy.deepcopy(entry);shifted['origin'][0]=128
        shifted['coverage']=[[-128,0],[384,128]]
        self.assertEqual(tris,list(region_terrain_triangles(shifted,terrain)))

    def test_lava_crosses_cell_boundary_and_is_clipped_to_each_map(self):
        pool = dict(reference=7, hull=[[400,0],[800,0],[800,400],[400,400]], top=256,
                    id='molten', model='pool.nif', dps=20, sound='')
        left = dict(origin=[0,0,0], coverage=[[0,0],[128,128]])
        right = dict(origin=[128,0,0], coverage=[[0,0],[128,128]])
        a, b = region_lava(left,[pool]), region_lava(right,[pool])
        self.assertEqual([p['reference'] for p in a], [7])
        self.assertEqual([p['reference'] for p in b], [7])
        self.assertEqual(max(p[0] for p in a[0]['hull']),512)
        self.assertEqual(min(p[0] for p in b[0]['hull']),512)
        self.assertEqual(pool['hull'][1][0],800)  # original remains immutable
        self.assertEqual(region_lava(dict(origin=[512,0,0],coverage=[[0,0],[128,128]]),[pool]),[])

    def test_legacy_map_has_lava_liquid_bed_and_effect_at_source_height(self):
        terrain=Terrain.__new__(Terrain)
        terrain.cells={(0,0):0};terrain.heights=np.zeros((1,65,65),np.float32)
        terrain.materials=np.ones((1,16,16),np.uint16)
        entry=dict(name='test',origin=[0,0,0],coverage=[[0,0],[128,128]])
        entry['lava_pools']=region_lava(entry,[dict(reference=7,hull=[[100,100],[300,100],[300,300],[100,300]],
                    top=256,id='molten',model='pool.nif',dps=20,sound='')])
        text=map_text(entry,terrain)
        self.assertIn('*lava',text);self.assertIn('lavabed',text)
        self.assertIn('"classname" "aw_lava"',text)
        self.assertIn('"origin" "50.00 50.00 64.00"',text)

    def test_measured_splits_stable_names_and_matching_shared_vertices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def cell(x,split):
                return dict(cell=[x,0],screen=dict(candidate=split),unresolved_placements=0,
                            name='',region='Test')
            report=dict(format='AmiWind world survey 1',terrain=dict(height_seams=[]),
                        settings=dict(overlap_runtime=896,source_triangle_limit=CEILING),cells=[cell(0,2),cell(-1,1)])
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
            origin=config['centre']
            core=[[origin[k]+p[k]/config['scale'] for k in range(2)] for p in config['bounds']]
            areas.append(dict(name=name,centre=origin,scale=.25,regions=[dict(core=core)]))
        report=dict(areas=areas)
        towns=town_handoffs(report)
        self.assertEqual(towns[0]['core'],[[-3328,-4608],[4864,3584]])
        self.assertEqual(towns[0]['owned_bounds'],towns[0]['core'])
        self.assertEqual(towns[0]['ground_bounds'],[[-4096,-5376],[5632,4352]])
        # Balmora owns its 3x3 cells since v0.0.43 (CHIM-BALMORA-INSET-SLIVERS-43): core on the cell grid
        self.assertEqual(towns[1]['core'],[[-3072,-3072],[3072,3072]])
        self.assertEqual(towns[1]['owned_bounds'],towns[1]['core'])
        self.assertEqual(towns[1]['ground_bounds'],[[-3840,-3840],[3840,3840]])
        for town in towns:
            for k in range(2):
                self.assertGreaterEqual(town['core'][0][k]-32,town['ground_bounds'][0][k]+64)
                self.assertLessEqual(town['core'][1][k]+32,town['ground_bounds'][1][k]-64)
        bad=copy.deepcopy(report);bad['areas'][0]['centre'][0]+=1
        with self.assertRaisesRegex(ValueError,'transform'):town_handoffs(bad)
        short=copy.deepcopy(report)
        short['areas'][0]['regions'][0]['core'][1][0]-=4
        with self.assertRaisesRegex(ValueError,'outside converted ground'):town_handoffs(short)

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
        split=refine_entries(original,[{'parent':'vf0001','cell':[1,0],'divisions':2,'reason':'reserve'}])
        with self.assertRaisesRegex(ValueError,r'unsplit cell: cell \[1, 0\] is split into 4'):
            refine_entries(split,[{'parent':'vf0001','cell':[1,0],'divisions':2,'reason':'again'}])

    def test_explicit_subcell_refinement_preserves_other_cores_and_global_grid(self):
        from prepare_world_regions import refine_entries
        original=[dict(name='vf0000',cell=[-2,3],divisions=1,subcell=[0,0],origin=[-3072,7168,128],core=[[-1024,-1024],[1024,1024]],coverage=[[-1920,-1920],[1920,1920]])]
        split=refine_entries(original,[dict(parent='vf0000',cell=[-2,3],divisions=2,reason='initial')])
        result=refine_entries(split,[dict(parent='vf0001',cell=[-2,3],parent_divisions=2,divisions=4,reason='dense lava')])
        self.assertEqual(len(result),7)
        for i in (0,2,3):self.assertEqual(result[i],split[i])
        children=[result[i] for i in (1,4,5,6)]
        self.assertEqual([e['subcell'] for e in children],[[2,0],[3,0],[2,1],[3,1]])
        covered=set()
        for e in result:
            self.assertEqual(e['coverage'][0],[v-896 for v in e['core'][0]])
            lo=[int(e['origin'][k]+e['core'][0][k]) for k in (0,1)]
            hi=[int(e['origin'][k]+e['core'][1][k]) for k in (0,1)]
            tiles={(x,y) for x in range(lo[0],hi[0],128) for y in range(lo[1],hi[1],128)}
            self.assertFalse(covered & tiles)
            covered.update(tiles)
        self.assertEqual(covered,{(x,y) for x in range(-4096,-2048,128) for y in range(6144,8192,128)})
        with self.assertRaisesRegex(ValueError,'parent divisions differ'):
            refine_entries(split,[dict(parent='vf0001',cell=[-2,3],parent_divisions=4,divisions=8,reason='stale')])

    def test_survey_with_another_ceiling_is_refused(self):
        # BUILD-WORLD-LAYOUT-DRIFT-32: a different ceiling lays out a different world.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for ceiling in (CEILING-1,None):
                settings=dict(overlap_runtime=896)
                if ceiling is not None:settings['source_triangle_limit']=ceiling
                report=dict(format='AmiWind world survey 1',terrain=dict(height_seams=[]),settings=settings,
                            cells=[dict(cell=[0,0],screen=dict(candidate=1),unresolved_placements=0,name='',region='Test')])
                (root/'world-survey.json').write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'differs from the recorded world layout ceiling'):
                    plan(root)

    def test_recorded_ceiling_is_the_shipped_layout(self):
        layout=layout_refinements()
        self.assertEqual(layout['survey_source_triangle_limit'],140801)
        self.assertEqual([r['parent'] for r in layout['regions']],
                         ['vf0698','vf0791','vf1174','vf1176','vf1255','vf1454','vf1692','vf1693','vf1816','vf1694','vf2541'])
        self.assertEqual([(r.get('parent_divisions',1),r['divisions']) for r in layout['regions'][2:]],
                         [(1,2),(2,4),(1,2),(1,2),(2,4),(2,4),(2,4),(2,4),(4,8)])

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
