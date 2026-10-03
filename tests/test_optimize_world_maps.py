"""Exercise all-map validation, rollback, idempotence and gate hash binding."""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from optimize_world_maps import optimize_maps, verify_optimized_maps, bind_heap_report
from check_geometry_render_inputs import BSP, compare_sample_sharing, f32
from deduplicate_bsp import deduplicate, light_ranges
from player_hull import lumps, pack_lumps
from test_share_bsp_geometry import repeated_geometry


class StagedMapOptimizerTests(unittest.TestCase):
    def test_parallel_matches_serial_order_hashes_and_oracle_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);serial=root/'serial';parallel=root/'parallel'
            serial.mkdir();parallel.mkdir()
            raw=repeated_geometry()
            for name in ('z.bsp','c.bsp','a.bsp','q.bsp','e.bsp'):
                for folder in (serial,parallel):(folder/name).write_bytes(raw)
            a=optimize_maps(serial,root/'serial.json')
            b=optimize_maps(parallel,root/'parallel.json',jobs=2)
            self.assertEqual(a['maps'],b['maps'])
            self.assertEqual(a['committed_maps'],b['committed_maps'])
            self.assertEqual([r['map'] for r in b['maps']],sorted(p.name for p in parallel.glob('*.bsp')))
            for p in serial.glob('*.bsp'):
                self.assertEqual(p.read_bytes(),(parallel/p.name).read_bytes())
            verify_optimized_maps(parallel,b)

    def test_parallel_worker_failure_preserves_originals_and_cleans_transaction(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);maps=root/'maps';maps.mkdir()
            raw=repeated_geometry()
            for name in ('a.bsp','c.bsp','d.bsp'):(maps/name).write_bytes(raw)
            (maps/'b.bsp').write_bytes(b'not a BSP')
            before={p.name:p.read_bytes() for p in maps.glob('*.bsp')}
            with self.assertRaises((ValueError,struct.error)):
                optimize_maps(maps,root/'failed.json',jobs=2)
            self.assertEqual(before,{p.name:p.read_bytes() for p in maps.glob('*.bsp')})
            report=json.loads((root/'failed.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertEqual(report['active_map'],'b.bsp')
            self.assertEqual(report['committed_maps'],[])
            self.assertEqual(list(root.glob('map-optimize-*')),[])

    def test_invalid_worker_count_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            for jobs in (0,-1,1.5,True):
                with self.assertRaisesRegex(ValueError,'positive integer'):
                    optimize_maps(root,root/'receipt.json',jobs=jobs)
            self.assertFalse((root/'receipt.json').exists())

    def test_invalid_second_map_leaves_every_original_untouched(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root);maps = root/'maps';maps.mkdir()
            first = repeated_geometry()
            (maps/'a.bsp').write_bytes(first)
            (maps/'b.bsp').write_bytes(b'not a BSP')
            with self.assertRaises((ValueError, struct.error)):
                optimize_maps(maps, root/'optimize-world-maps.json')
            self.assertEqual((maps/'a.bsp').read_bytes(), first)
            self.assertEqual((maps/'b.bsp').read_bytes(), b'not a BSP')
            report = json.loads((root/'optimize-world-maps.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['active_map'], 'b.bsp')
            self.assertEqual(report['committed_maps'], [])

    def test_commit_failure_rolls_back_preceding_replacement(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root);maps = root/'maps';maps.mkdir()
            raw = repeated_geometry()
            for name in ('a.bsp', 'b.bsp'):
                (maps/name).write_bytes(raw)
            replace = os.replace
            def fail_second(source, destination):
                if Path(source).parent.name == 'candidate' and Path(source).name == 'b.bsp':
                    raise OSError('simulated blocked replacement')
                return replace(source, destination)
            with patch('optimize_world_maps.os.replace', side_effect=fail_second):
                with self.assertRaisesRegex(OSError, 'simulated'):
                    optimize_maps(maps, root/'receipt.json')
            for name in ('a.bsp', 'b.bsp'):
                self.assertEqual((maps/name).read_bytes(), raw)
            report = json.loads((root/'receipt.json').read_text())
            self.assertEqual(report['rollback'], 'originals preserved/restored')

    def test_keyboard_interrupt_rolls_back_preceding_replacement(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root);maps = root/'maps';maps.mkdir()
            raw = repeated_geometry()
            for name in ('a.bsp', 'b.bsp'):
                (maps/name).write_bytes(raw)
            replace = os.replace
            def fail_second(source, destination):
                if Path(source).parent.name == 'candidate' and Path(source).name == 'b.bsp':
                    raise KeyboardInterrupt('simulated interruption')
                return replace(source, destination)
            with patch('optimize_world_maps.os.replace', side_effect=fail_second):
                with self.assertRaisesRegex(KeyboardInterrupt, 'simulated'):
                    optimize_maps(maps, root/'receipt.json')
            for name in ('a.bsp', 'b.bsp'):
                self.assertEqual((maps/name).read_bytes(), raw)
            report = json.loads((root/'receipt.json').read_text())
            self.assertEqual(report['rollback'], 'originals preserved/restored')

    def test_idempotence_final_gate_binding_and_late_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root);maps = root/'maps';maps.mkdir()
            (maps/'a.bsp').write_bytes(repeated_geometry())
            report = optimize_maps(maps, root/'receipt.json')
            final = (maps/'a.bsp').read_bytes()
            self.assertGreater(report['file_bytes_saved'], 0)
            verify_optimized_maps(maps, report)
            second = optimize_maps(maps, root/'second.json')
            self.assertEqual(second['changed_maps'], 0)
            self.assertEqual((maps/'a.bsp').read_bytes(), final)
            # Simulated downstream estimator receipt: hashes, not fake acceptance.
            heap = {'maps': [{'map': 'a.bsp', 'file_sha256': hashlib.sha256(final).hexdigest(),
                             'resident_loader_bytes': 1, 'peak_loader_bytes': 2,
                             'estimated_clearance_bytes': 3, 'gate': 'fixture-only'}],
                    'passing_maps': 0, 'failing_maps': [], 'acceptance': 'fixture only',
                    'baseline_reserve_bytes': 3*1024**2, 'safety_headroom_bytes': 2*1024**2}
            (root/'heap.json').write_text(json.dumps(heap))
            bind_heap_report(report, heap, root/'heap.json', root/'receipt.json')
            self.assertEqual(report['maps'][0]['final_estimate']['gate'], 'fixture-only')
            heap['maps'][0]['file_sha256'] = report['maps'][0]['input_sha256']
            with self.assertRaisesRegex(ValueError, 'does not describe'):
                bind_heap_report(report, heap, root/'heap.json', root/'receipt.json')
            (maps/'a.bsp').write_bytes(repeated_geometry())
            with self.assertRaisesRegex(ValueError, 'no longer match'):
                verify_optimized_maps(maps, report)

    def test_independent_sample_check_detects_light_and_pvs_corruption(self):
        raw = repeated_geometry()
        shared, _ = deduplicate(raw)
        compare_sample_sharing(raw, shared)
        for lump, offset in ((8, 0), (4, 0)):
            data = lumps(shared)
            data[lump][offset] ^= 1
            with self.assertRaises(ValueError):
                compare_sample_sharing(raw, pack_lumps(data))
        data = lumps(shared)
        struct.pack_into('<i', data[10], 28+4, 99999)
        with self.assertRaisesRegex(ValueError, 'PVS'):
            compare_sample_sharing(raw, pack_lumps(data))

    def test_rounding_boundary_keeps_longest_original_light_prefix(self):
        data = lumps(repeated_geometry())
        # Constructed, asset-free cancellation example: narrow UV=64.00003,
        # wide intermediates rounded on store=64.0. The larger extent matters.
        scale, offset = f32(2.73), f32(-469.4419860839844)
        low = f32((32-offset)/scale)
        for index in range(len(data[3])//12):
            struct.pack_into('<3f', data[3], index*12,
                             f32(195.4) if index%3 == 0 else low,
                             16.0 if index%3 == 2 else 0.0, 0.0)
        struct.pack_into('<8f', data[6], 0, scale,0,0,offset,0,1,0,0)
        data[8] = bytearray(range(128))
        raw = pack_lumps(data)
        parsed = BSP(raw)
        narrow = len(parsed.face_inputs(0, False)[-1])
        wide = len(parsed.face_inputs(0, True)[-1])
        self.assertGreater(narrow, wide)
        self.assertEqual(light_ranges(data)[0][2], max(narrow, wide))
        result, _ = deduplicate(raw)
        compare_sample_sharing(raw, result)
        self.assertEqual(deduplicate(result)[0], result)


if __name__ == '__main__':
    unittest.main()
