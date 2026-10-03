import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from adaptive_town_regions import plan,MIB
from balmora_regions import owner

class AdaptiveTownTests(unittest.TestCase):
    def entries(self):
        return [dict(name='sn000',core=[[0,0],[1024,1024]]),
                dict(name='sn001',core=[[1024,0],[2048,1024]])]
    def run_plan(self,evaluate,**kwargs):
        return plan(self.entries(),evaluate,terrain_bounds=[[-4096,-4096],[4096,4096]],
                    prefix='sn',**kwargs)
    def test_only_dense_core_splits_and_union_and_overlap_survive(self):
        def measure(entry):
            a,b=entry['core'];area=(b[0]-a[0])*(b[1]-a[1])
            return dict(peak_loader_bytes=int(3*MIB+area*4) if entry['source_region']=='sn000' else 4*MIB)
        report=self.run_plan(measure)
        self.assertEqual(report['region_count'],3)
        self.assertFalse(report['over_budget_regions'])
        self.assertFalse(report['planning_target_unmet_regions'])
        regions=report['regions']
        self.assertEqual(sum((b[0]-a[0])*(b[1]-a[1]) for a,b in (e['core'] for e in regions)),2048*1024)
        self.assertEqual(sum(e['source_region']=='sn001' for e in regions),1)
        for x,y in [(0,0),(511,500),(512,500),(1023,500),(1024,500),(2048,1024)]:
            self.assertIsNotNone(owner((x,y),regions))
        for entry in regions:
            for axis in range(2):
                self.assertEqual(entry['core'][0][axis]-entry['coverage'][0][axis],896)
                self.assertEqual(entry['coverage'][1][axis]-entry['core'][1][axis],896)
        self.assertFalse(report['installed'])
        self.assertEqual(report['runtime_validation'],'pending')
    def test_shared_payload_floor_does_not_multiply_useless_cells(self):
        report=self.run_plan(lambda entry:dict(peak_loader_bytes=7*MIB))
        self.assertEqual(report['region_count'],2)
        self.assertEqual(report['status'],'estimate_failed')
        self.assertEqual(report['stop_reason'],'no_measured_reduction')
        self.assertTrue(all(not attempt['accepted'] for attempt in report['split_attempts']))
    def test_capacity_never_silently_accepts_over_budget_cells(self):
        report=self.run_plan(lambda entry:dict(peak_loader_bytes=7*MIB),max_regions=2)
        self.assertEqual(report['stop_reason'],'native_region_capacity')
        self.assertEqual(len(report['over_budget_regions']),2)
    def test_minimum_core_and_planning_target_are_not_new_hard_gate(self):
        report=self.run_plan(lambda entry:dict(peak_loader_bytes=6*MIB),min_core=600)
        self.assertEqual(report['status'],'estimate_passed')
        self.assertEqual(report['stop_reason'],'minimum_core_reached')
        self.assertEqual(len(report['planning_target_unmet_regions']),2)
        self.assertTrue(all(e['growth_margin_bytes']==0 for e in report['regions']))
    def test_invalid_geometry_estimates_and_policy_rejected(self):
        for kwargs in (dict(overlap=768),dict(safety_headroom=MIB),dict(max_regions=65)):
            with self.assertRaises(ValueError):self.run_plan(lambda e:dict(peak_loader_bytes=0),**kwargs)
        with self.assertRaises(ValueError):self.run_plan(lambda e:dict(peak_loader_bytes=float('nan')))
        entries=self.entries();entries[1]['core'][0][0]=500
        with self.assertRaises(ValueError):
            plan(entries,lambda e:dict(peak_loader_bytes=0),terrain_bounds=[[-4096,-4096],[4096,4096]],prefix='sn')

if __name__=='__main__':unittest.main()
