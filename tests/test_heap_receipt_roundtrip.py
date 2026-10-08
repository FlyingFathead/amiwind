# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-HEAP-RECEIPT-TUPLES-32: the final heap audit handed to bind_heap_report equals its saved receipt,
even when the audit holds tuples (the harvest profile's fingerprint entries did)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_aga  # noqa: E402
from optimize_world_maps import bind_heap_report  # noqa: E402


class HeapReceiptRoundTripTests(unittest.TestCase):
    def test_returned_audit_equals_saved_receipt_with_tuples(self):
        audit = {'maps': [{'map': 'a.bsp', 'file_sha256': 'x' * 64, 'resident_loader_bytes': 1,
                           'peak_loader_bytes': 2, 'estimated_clearance_bytes': 3, 'gate': 'pass'}],
                 'harvest_external_profile': {'fingerprint_entries': [('harvest-a.txt', 'y' * 64)]},
                 'passing_maps': 1, 'failing_maps': 0, 'acceptance': 'ok',
                 'baseline_reserve_bytes': 0, 'safety_headroom_bytes': 0}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(build_aga, 'verify_heap_loader_source_receipt', return_value={'model.c': 'z'}), \
                mock.patch('check_world_map_heap.audit_world_maps', return_value=audit):
            heap_path = Path(tmp) / 'world-map-heap.json'
            heap = build_aga.audit_world_map_heap_with_receipt({}, Path(tmp), 'sdk', heap_path)
            self.assertEqual(json.loads(heap_path.read_text(encoding='utf-8')), heap)
            optimization = {'maps': [{'map': 'a.bsp', 'output_sha256': 'x' * 64}]}
            bind_heap_report(optimization, heap, heap_path, Path(tmp) / 'opt.json')
            self.assertEqual(optimization['final_heap_gate']['passing_maps'], 1)

    def test_compact_harvest_fingerprint_entries_are_lists(self):
        text = (ROOT / 'tools/compact_harvest_heap.py').read_text(encoding='utf-8')
        self.assertIn('fingerprint_entries=[list(e) for e in entries]', text)


if __name__ == '__main__':
    unittest.main()
