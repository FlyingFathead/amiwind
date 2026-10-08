"""Temporary pre-CHIM heap bypass (HEAP-SEYDA-OVERLAP-32, owner decision A).

v0.0.32 ships the recorded Seyda Neen maps sn019, sn026 and sn035, which exceed
the modelled reserve allowance only. The strict heap gate accepts exactly those
maps, by name and SHA-256, with the legacy builder, and records it; a temporary
bypass for the legacy builder, removed when Seyda Neen moves to CHIM (M2).
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_aga import BYPASS_STATUS, ROOT, apply_map_budget_policy, load_heap_bypass

MB = 1024 * 1024


def report(rows):
    """rows: (map, peak bytes, fails the allowance)."""
    return {'heap_budget_bytes': 11 * MB, 'baseline_reserve_bytes': 3 * MB, 'safety_headroom_bytes': 2 * MB,
            'maps': [{'map': m, 'peak_loader_bytes': peak, 'estimated_clearance_bytes': -1000 if fail else 1000}
                     for m, peak, fail in rows],
            'failing_maps': [m for m, _, fail in rows if fail]}


class HeapBypassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.maps = Path(self.temp.name)
        self.raw = b'recorded sn019'
        (self.maps / 'sn019.bsp').write_bytes(self.raw)
        (self.maps / 'sn020.bsp').write_bytes(b'other map')
        self.entries = {'sn019.bsp': dict(map='sn019.bsp', sha256=hashlib.sha256(self.raw).hexdigest(),
                                          builder='legacy', until='CHIM M2 (Seyda Neen on CHIM)',
                                          bug='HEAP-SEYDA-OVERLAP-32', decision='test')}

    def decide(self, rows, **kw):
        receipt = self.maps / 'policy.json'
        decision = apply_map_budget_policy(report(rows), 'strict', receipt, maps_dir=self.maps,
                                           bypass=self.entries, **kw)
        self.assertEqual(json.loads(receipt.read_text()), decision)
        return decision

    def test_listed_map_with_its_exact_bytes_passes_and_is_recorded(self):
        d = self.decide([('sn019.bsp', 7 * MB, True), ('town.bsp', 5 * MB, False)])
        self.assertEqual(d['status'], 'estimate_passed_with_temporary_pre_chim_bypass')
        self.assertTrue(d['production_memory_gate_passed'])
        self.assertEqual(d['production_memory_gate'], 'passed with %s: sn019.bsp' % BYPASS_STATUS)
        self.assertFalse(d['modeled_allowance_passed'])  # never silently a clean pass
        row, = d['temporary_pre_chim_bypass']
        self.assertEqual((row['map'], row['status'], row['until'], row['bug'], row['estimated_clearance_bytes']),
                         ('sn019.bsp', BYPASS_STATUS, 'CHIM M2 (Seyda Neen on CHIM)', 'HEAP-SEYDA-OVERLAP-32', -1000))
        self.assertEqual(d['allowance_failures'], [])

    def test_changed_bytes_fail(self):
        (self.maps / 'sn019.bsp').write_bytes(b'rebuilt sn019')
        with self.assertRaisesRegex(ValueError, 'estimate_failed; sn019.bsp'):
            self.decide([('sn019.bsp', 7 * MB, True)])
        refused, = json.loads((self.maps / 'policy.json').read_text())['bypass_refused']
        self.assertEqual(refused['reason'], 'map bytes differ from the listed recorded map')

    def test_unlisted_map_fails(self):
        with self.assertRaisesRegex(ValueError, 'estimate_failed; sn020.bsp'):
            self.decide([('sn019.bsp', 7 * MB, True), ('sn020.bsp', 7 * MB, True)])
        policy = json.loads((self.maps / 'policy.json').read_text())
        self.assertEqual(policy['allowance_failures'], ['sn020.bsp'])
        self.assertFalse(policy['production_memory_gate_passed'])

    def test_allocation_ceiling_fails_even_when_listed(self):
        with self.assertRaisesRegex(ValueError, 'allocation_ceiling_failed; sn019.bsp'):
            self.decide([('sn019.bsp', 11 * MB, True)])
        refused, = json.loads((self.maps / 'policy.json').read_text())['bypass_refused']
        self.assertIn('allocation ceiling', refused['reason'])

    def test_chim_builder_refuses_the_bypass(self):
        with self.assertRaisesRegex(ValueError, 'estimate_failed; sn019.bsp'):
            self.decide([('sn019.bsp', 7 * MB, True)], builder='chim')
        refused, = json.loads((self.maps / 'policy.json').read_text())['bypass_refused']
        self.assertIn('the bypass ends with CHIM M2', refused['reason'])

    def test_without_map_bytes_nothing_is_bypassed(self):
        with self.assertRaisesRegex(ValueError, 'estimate_failed'):
            apply_map_budget_policy(report([('sn019.bsp', 7 * MB, True)]), 'strict', bypass=self.entries)


class ShippedBypassTests(unittest.TestCase):
    def test_shipped_entries_are_the_recorded_seyda_maps_until_chim_m2(self):
        entries = load_heap_bypass()
        self.assertEqual(sorted(entries), ['sn019.bsp', 'sn026.bsp', 'sn035.bsp'])
        pin = json.loads((ROOT / 'config/seyda-recorded-v0.0.31.json').read_text(encoding='utf-8'))
        recorded = {row['file'][5:]: row['sha256'] for row in pin['files']}
        for name, entry in entries.items():
            self.assertEqual(entry['sha256'], recorded[name], name)
            self.assertEqual((entry['builder'], entry['until'], entry['bug']),
                             ('legacy', 'CHIM M2 (Seyda Neen on CHIM)', 'HEAP-SEYDA-OVERLAP-32'))
        text = (ROOT / 'config/heap-bypass.json').read_text(encoding='utf-8')
        self.assertIn('temporary bypass for the legacy builder, removed when Seyda Neen moves to CHIM', text)

    def test_image_step_passes_map_bytes_and_builder_and_records_the_bypass(self):
        source = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("maps_dir=boot/'id1/maps', builder=getattr(args, 'builder', 'legacy')", source)
        self.assertIn("'temporary_pre_chim_bypass':budget_decision['temporary_pre_chim_bypass']", source)
        self.assertIn("'production_memory_gate':budget_decision['production_memory_gate']", source)

    def test_bypass_is_not_a_private_test_waiver(self):
        import argparse
        from build_aga import image_waivers
        self.assertEqual(image_waivers(argparse.Namespace(map_budget_policy='strict')), [])


if __name__ == '__main__':
    unittest.main()
