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


class DirectClipEstimateTests(unittest.TestCase):
    def test_large_clipnode_lump_has_no_duplicate_temporary_stage(self):
        data = lumps(fixture(inline=True))
        data[9] = bytearray(struct.pack('<iHH', 0, 65535, 65534)*20000)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'large-clip.bsp'
            path.write_bytes(pack_lumps(data))
            report = heap.estimate_bsp(path, SIZES)
        self.assertEqual(report['counts']['clipnodes'], 20000)
        self.assertEqual(report['direct_in_place_sections'], ['clipnodes'])
        clip = next(r for r in report['resident_allocations'] if r['allocation'] == 'clipnodes')
        self.assertEqual(clip['payload_bytes'], 160000)
        self.assertEqual(clip['hunk_bytes'], heap.hunk_alloc_bytes(160000, 16))
        self.assertLess(report['temporary_input_peak_bytes'], 1000)
        self.assertEqual(report['peak_loader_bytes'], report['resident_loader_bytes'])
        self.assertEqual(report['temporary_input_bytes_at_peak'], 0)


if __name__ == '__main__':
    unittest.main()
