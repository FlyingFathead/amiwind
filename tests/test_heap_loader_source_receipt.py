import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_aga


class HeapLoaderSourceReceiptTests(unittest.TestCase):
    def make_sources(self, root):
        hashes = {}
        for relative in build_aga.HEAP_LOADER_SOURCE_PATHS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('baseline ' + relative, encoding='utf-8')
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes

    def test_current_heap_loader_sources_match_engine_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            hashes = self.make_sources(source)
            receipt = {'source_sha256': hashes}
            self.assertEqual(build_aga.verify_heap_loader_source_receipt(receipt, source), hashes)

    def test_changed_loader_source_rejects_stale_engine_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            hashes = self.make_sources(source)
            (source / 'src/model.c').write_text('changed after engine build', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, r'stale.*src/model\.c'):
                build_aga.verify_heap_loader_source_receipt({'source_sha256': hashes}, source)

    def test_missing_required_source_hash_rejects_incomplete_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            hashes = self.make_sources(source)
            del hashes['src/zone.h']
            with self.assertRaisesRegex(ValueError, r'stale.*src/zone\.h'):
                build_aga.verify_heap_loader_source_receipt({'source_sha256': hashes}, source)

    def test_map_audit_receipt_records_sources_and_runs_estimator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'runtime'
            hashes = self.make_sources(source)
            output = root / 'world-map-heap.json'
            expected = {'map_count': 2, 'acceptance': 'estimate-only'}
            with patch('check_world_map_heap.audit_world_maps', return_value=expected) as audit:
                report = build_aga.audit_world_map_heap_with_receipt(
                    {'source_sha256': hashes}, root / 'maps', root / 'sdk', output, source)
            audit.assert_called_once_with(root / 'maps', root / 'sdk', output)
            self.assertEqual(report['loader_source_sha256'], hashes)
            self.assertEqual(json.loads(output.read_text())['loader_source_sha256'], hashes)

    def test_map_audit_refuses_stale_receipt_before_estimation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'runtime'
            hashes = self.make_sources(source)
            (source / 'src/common.c').write_text('changed before map audit', encoding='utf-8')
            with patch('check_world_map_heap.audit_world_maps') as audit:
                with self.assertRaisesRegex(ValueError, r'stale.*src/common\.c'):
                    build_aga.audit_world_map_heap_with_receipt(
                        {'source_sha256': hashes}, root / 'maps', root / 'sdk',
                        root / 'world-map-heap.json', source)
                audit.assert_not_called()


class HeapWatcherReceiptTests(unittest.TestCase):
    def summary(self, peak):
        budget = 11 * 1024 * 1024
        baseline, safety = 3 * 1024 * 1024, 2 * 1024 * 1024
        report = dict(heap_budget_bytes=budget, baseline_reserve_bytes=baseline,
                      safety_headroom_bytes=safety, worst_map='town.bsp',
                      maps=[dict(map='town.bsp', peak_loader_bytes=peak)],
                      map_count=1, failing_maps=['town.bsp'] if peak > budget-baseline-safety else [],
                      acceptance='estimate-only; not target or gameplay validation')
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'world-map-heap.json'
            path.write_text(json.dumps(report), encoding='utf-8')
            summary=build_aga.heap_watcher_summary(report,path)
            self.assertEqual(summary['report_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        return summary

    def test_used_free_and_growth_margin_are_distinct(self):
        mib=1024*1024
        row=self.summary(5*mib)
        self.assertEqual(row['estimated_map_peak_used_bytes'],5*mib)
        self.assertEqual(row['estimated_free_before_reserves_bytes'],6*mib)
        self.assertEqual(row['estimated_growth_margin_after_reserves_bytes'],mib)
        self.assertEqual(row['status'],'estimate_passed')
        self.assertEqual(row['runtime_validation'],'pending')
        self.assertIsNone(row['runtime_measured_used_bytes'])
        self.assertIsNone(row['runtime_measured_free_bytes'])

    def test_negative_margin_flags_map_instead_of_clamping(self):
        row=self.summary(7*1024*1024)
        self.assertEqual(row['estimated_growth_margin_after_reserves_bytes'],-1024*1024)
        self.assertEqual(row['status'],'estimate_failed')
        self.assertEqual(row['over_budget_maps'],['town.bsp'])

    def test_zero_growth_margin_keeps_safety_reserved(self):
        row=self.summary(6*1024*1024)
        self.assertEqual(row['estimated_growth_margin_after_reserves_bytes'],0)
        self.assertEqual(row['required_safety_headroom_bytes'],2*1024*1024)
        self.assertEqual(row['status'],'estimate_passed')


class DynamicTownFingerprintTests(unittest.TestCase):
    def directory(self,count):
        return ('AWBR1 '+str(count)+' 96 540 0 0 64 90 0 0 64 90\n'+
                ''.join(f'sn{i:03d} {i} 0 {i+1} 1 {i-896} -896 {i+897} 897\n' for i in range(count)))
    def test_actual_additional_subcells_included(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'seyda-regions.txt';path.write_text(self.directory(30))
            names=build_aga.town_region_map_names(path,'sn')
            self.assertEqual(len(names),30)
            self.assertEqual(names[-1],'maps/sn029.bsp')
    def test_native_capacity_row_and_bounds_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'seyda-regions.txt'
            for text in (self.directory(65),self.directory(2).replace('sn001','sn099'),
                         self.directory(1).replace('0 0 1 1','0 0 0 1'),self.directory(1)+'extra\n'):
                path.write_text(text)
                with self.assertRaises(ValueError):build_aga.town_region_map_names(path,'sn')


if __name__ == '__main__':
    unittest.main()
