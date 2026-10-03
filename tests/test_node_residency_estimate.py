import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import check_world_map_heap as heap
from player_hull import lumps, pack_lumps
from test_check_world_map_heap import SIZES
from test_replace_bsp_world import fixture


def candidate(count=100, fallback=False):
    data = lumps(fixture(inline=True))
    world = bytes(data[5][:24])
    nodes = bytearray(world)
    for index in range(1, count):
        row = bytearray(data[5][24:48])
        struct.pack_into('<h', row, 4, index+1 if index+1 < count else -2)
        struct.pack_into('<H', row, 22, 0)
        nodes.extend(row)
    data[5] = nodes
    if fallback:
        struct.pack_into('<i', data[14], 64+36, 0)
    return pack_lumps(data)


class NodeResidencyEstimateTests(unittest.TestCase):
    def estimate(self, raw):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'candidate.bsp'
            path.write_bytes(raw)
            return heap.estimate_bsp(path, SIZES)

    def test_direct_hull0_and_renderer_coexist_with_raw_node_section(self):
        report = self.estimate(candidate())
        policy = report['node_residency']
        self.assertTrue(policy['direct_hull0'])
        self.assertEqual(policy['render_nodes'], 1)
        self.assertEqual(policy['disk_nodes'], 100)
        self.assertEqual(report['external_classifier_scratch_bytes'], 13)
        allocations = report['resident_allocations']
        labels = [r['allocation'] for r in allocations]
        self.assertLess(labels.index('models'), labels.index('hull0 clipnodes (direct disk)'))
        self.assertEqual(sum(label.startswith('hull0 clipnodes') for label in labels), 1)
        node = next(r for r in allocations if r['allocation'] == 'nodes (world render prefix)')
        self.assertEqual(report['peak_section'], 'nodes')
        self.assertEqual(report['peak_loader_bytes'], node['resident_after_bytes']+heap.hunk_temp_bytes(2401, 16))
        self.assertEqual(report['resident_bytes_at_peak']+report['temporary_input_bytes_at_peak'], report['peak_loader_bytes'])

    def test_optional_classifier_failure_bound_matches_generic_layout(self):
        direct = self.estimate(candidate())
        generic = self.estimate(candidate(fallback=True))
        self.assertFalse(generic['node_residency']['direct_hull0'])
        self.assertEqual(direct['classifier_allocation_failure_fallback_peak_bytes'], generic['peak_loader_bytes'])
        self.assertGreater(generic['peak_loader_bytes'], direct['peak_loader_bytes'])
        self.assertIn('hull0 clipnodes', [r['allocation'] for r in generic['resident_allocations']])

    def test_noncontiguous_and_face_bearing_tail_receive_no_savings(self):
        for kind in ('gap', 'face', 'backward', 'negative'):
            data = lumps(candidate(3))
            if kind == 'gap':
                struct.pack_into('<h', data[5], 4, 2)
            elif kind == 'face':
                struct.pack_into('<H', data[5], 24+22, 1)
            elif kind == 'backward':
                struct.pack_into('<h', data[5], 48+4, 1)
            else:
                struct.pack_into('<i', data[14], 64+36, -999)
            report = self.estimate(pack_lumps(data))
            self.assertFalse(report['node_residency']['direct_hull0'])
            self.assertEqual(report['node_residency']['render_nodes'], 3)


if __name__ == '__main__':
    unittest.main()
