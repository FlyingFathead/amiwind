# SPDX-License-Identifier: GPL-3.0-only
"""Original town-cell ownership, source coverage and stable Seyda aliases."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT/'tools', ROOT/'src'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import town_grid


def cfg(name):
    return json.loads((ROOT/'config'/name).read_text())


def owner(rows, point):
    return [r['name'] for r in rows if all(r['core'][0][k] <= point[k] < r['core'][1][k] for k in range(2))]


class TownGrid(unittest.TestCase):
    def test_exact_52_original_cells_at_stable_origins(self):
        s,v=cfg('seyda_area.json'),cfg('vivec_city.json')
        self.assertEqual(s['owned_cells'],[[-3,-11],[1,-7]])
        self.assertEqual(v['owned_cells'],[[1,-14],[7,-8]])
        self.assertEqual(s['centre'],[-11264,-71680]);self.assertEqual(v['centre'],[32768,-92160])
        self.assertEqual(town_grid.owned_bounds(s),[[-3328,-4608],[4864,3584]])
        self.assertEqual(town_grid.owned_bounds(v),[[-6144,-5632],[6144,6656]])
        self.assertEqual(sum((x['owned_cells'][1][0]-x['owned_cells'][0][0])*(x['owned_cells'][1][1]-x['owned_cells'][0][1]) for x in (s,v)),52)

    def test_selection_audit_and_apron_cover_the_owned_core(self):
        for name in ('seyda_area.json','vivec_city.json'):
            s=cfg(name);self.assertEqual(town_grid.audit_radius(s), 4 if name == 'vivec_city.json' else 3)
            self.assertGreaterEqual(s['terrain_margin'],s['draw_distance']+32)
        s=cfg('seyda_area.json');self.assertGreater(town_grid.scenery_radius(s,[-11200,-71504,400],11500),11500)

    def test_mismatched_core_and_incomplete_source_fail(self):
        s=cfg('seyda_area.json');bad=copy.deepcopy(s);bad['handoff_core'][1][0]-=1
        with self.assertRaises(ValueError):town_grid.owned_bounds(bad)
        bad=copy.deepcopy(s);bad['source_radius']=1
        with self.assertRaises(ValueError):town_grid.audit_radius(bad)
        bad=copy.deepcopy(s);bad['owned_cells'][0][0]=-3.5
        with self.assertRaises(ValueError):town_grid.owned_bounds(bad)

    def expanded(self):
        s=cfg('seyda_area.json');ground=[[v-768 for v in s['bounds'][0]],[v+768 for v in s['bounds'][1]]]
        old=cfg('seyda-bounded-regions.json')
        return old,town_grid.extend_edge_layout(old,s['bounds'],ground)

    def test_all64_old_region_names_order_and_points_preserved(self):
        old,new=self.expanded();self.assertEqual(len(new['regions']),64)
        self.assertEqual([r['name'] for r in old['regions']],[r['name'] for r in new['regions']])
        for row in old['regions']:
            p=[(row['core'][0][k]+row['core'][1][k])/2 for k in range(2)]
            self.assertEqual(owner(old['regions'],p),owner(new['regions'],p))
            self.assertEqual(owner(old['regions'],row['core'][0]),owner(new['regions'],row['core'][0]))

    def test_expanded_partition_has_no_hole_or_duplicate_owner(self):
        _,new=self.expanded();rows=new['regions']
        cuts=[sorted({r['core'][e][k] for r in rows for e in (0,1)}) for k in (0,1)]
        for x0,x1 in zip(cuts[0],cuts[0][1:]):
            for y0,y1 in zip(cuts[1],cuts[1][1:]):
                self.assertEqual(len(owner(rows,[(x0+x1)/2,(y0+y1)/2])),1)
        self.assertEqual(owner(rows,new['bounds'][1]),[])

    def test_bad_frozen_coverage_is_rejected_not_repaired(self):
        old,new=self.expanded();old['regions'][0]['coverage'][0][0]-=1
        s=cfg('seyda_area.json');ground=[[v-768 for v in s['bounds'][0]],[v+768 for v in s['bounds'][1]]]
        with self.assertRaises(ValueError):town_grid.extend_edge_layout(old,s['bounds'],ground)

    def test_vivec_subregions_keep_native64_cap(self):
        from town_regions import regions
        rows=regions(cfg('vivec_city.json'));self.assertEqual(len(rows),64)
        self.assertEqual([r['name'] for r in rows],[f'vc{i:03d}' for i in range(64)])

    def test_vivec_scenery_apron_keeps_neighbor_objects_without_taking_ownership(self):
        import math
        from import_town import in_frame, footprint_in_frame
        from town_regions import town_references
        from chim.regions import LEAVE_MARGIN
        s = cfg('vivec_city.json')
        self.assertEqual(s['missing_land'], 'flat')
        self.assertGreaterEqual(s['reference_margin'], s['draw_distance'] + LEAVE_MARGIN)
        self.assertLessEqual(s['reference_margin'], s['terrain_margin'])
        # Four objects outside each logical edge but visible during handoff.
        points = [[7936, -97008, 0], [57600, -112368, 0],
                  [18704, -114944, 0], [32768, -65280, 0]]
        refs = [dict(number=n + 1, cell=[math.floor(p[k]/8192) for k in range(2)],
                     position=p, bounds=[p, p]) for n, p in enumerate(points)]
        for ref in refs:
            self.assertTrue(in_frame(ref, s))
            self.assertTrue(footprint_in_frame(ref, s))
        self.assertEqual(town_references({'references': refs}, s), [1, 2, 3, 4])
        own = town_grid.reference_ownership(refs, s)
        self.assertEqual(own['owned_references'], [])
        self.assertEqual(len(own['dependency_references']), 4)
        # Audit covers the apron in all directions, including its corners.
        low, high = s['bounds']; margin = s['reference_margin']
        for edge in range(2):
            for k in range(2):
                local = (low[k] - margin) if edge == 0 else (high[k] + margin - 1)
                cell = math.floor((s['centre'][k] + local/s['scale']) / 8192)
                self.assertLessEqual(abs(cell-s['source_cell'][k]), s['source_radius'])
        outside = [s['centre'][k] + (high[k]+margin)/s['scale'] for k in range(2)]
        self.assertFalse(in_frame({'position': outside + [0]}, s))

    def test_reference_origin_ownership_keeps_dependency_copies_and_rejects_duplicates(self):
        s=cfg('seyda_area.json')
        inside={'number':11,'cell':[-2,-9],'position':[-11264,-71680,0]}
        outside={'number':12,'cell':[1,-9],'position':[8192,-71680,0]}
        result=town_grid.reference_ownership([inside,outside],s)
        self.assertEqual([r['reference'] for r in result['owned_references']],[11])
        self.assertEqual([r['reference'] for r in result['dependency_references']],[12])
        self.assertEqual(result['dependency_references'][0]['role'],'footprint_or_assembly_dependency')
        with self.assertRaises(ValueError):town_grid.reference_ownership([inside,inside],s)

    def test_terrain_apron_is_not_a_second_frame_owner(self):
        from chim.world import frame_box
        s=cfg('seyda_area.json')
        frame={'centre':s['centre'],'owned':s['bounds'],'low':[-4608,-5376],'span':[10752,9984]}
        self.assertEqual(frame_box(frame),(-24576,-90112,8192,-57344))

    def test_town_cores_leave_no_classic_slivers(self):
        """CHIM-BALMORA-INSET-SLIVERS-43: a town core off the cell grid leaves strips of its border cells to the
        classic open world (Balmora's 96-unit inset kept 15 legacy maps for 8 cells); every town of the default
        build owns whole cells, so the exterior checklist has no town-owned classic cell."""
        import exterior_plan
        towns=exterior_plan.town_cores(['seyda','balmora','vivec_city'])
        for town in towns:
            self.assertTrue(all(v % 2048 == 0 for v in town['core']), town)
        cells=[(x,y) for x in range(-5,8) for y in range(-15,1)]
        plan=exterior_plan.make(cells,[],towns)
        self.assertEqual([r['cell'] for r in plan['cells'] if r['format']=='bsp' and r['town_owners']],[])
        self.assertEqual(cfg('balmora.json')['handoff_core'],cfg('balmora.json')['bounds'])

if __name__=='__main__':unittest.main()
