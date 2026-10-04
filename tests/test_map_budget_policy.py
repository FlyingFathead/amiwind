import copy
import json
import tempfile
import unittest
from pathlib import Path
from build_aga import apply_map_budget_policy


class MapBudgetPolicyTests(unittest.TestCase):
    def report(self, peak):
        return {'heap_budget_bytes': 11 * 1024 * 1024,
                'baseline_reserve_bytes': 3 * 1024 * 1024,
                'safety_headroom_bytes': 2 * 1024 * 1024,
                'maps': [{'map': 'town.bsp', 'peak_loader_bytes': peak}],
                'failing_maps': ['town.bsp'] if peak > 6 * 1024 * 1024 else []}

    def test_strict_is_default_and_records_failed_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / 'policy.json'
            with self.assertRaisesRegex(ValueError, 'estimate_failed'):
                apply_map_budget_policy(self.report(6 * 1024 * 1024 + 100), receipt_path=receipt)
            self.assertFalse(json.loads(receipt.read_text())['private_assembly_allowed'])

    def test_explicit_warning_preserves_reserves_and_failure(self):
        report = self.report(6 * 1024 * 1024 + 100)
        before = copy.deepcopy(report)
        result = apply_map_budget_policy(report, 'warning')
        self.assertEqual(report, before)
        self.assertEqual(result['status'], 'estimate_warning_needs_adjustment')
        self.assertTrue(result['private_assembly_allowed'])
        self.assertFalse(result['production_memory_gate_passed'])
        self.assertEqual(result['allowance_failures'], ['town.bsp'])
        self.assertEqual(result['runtime_validation'], 'pending; runtime allocation errors remain fatal')

    def test_warning_does_not_waive_allocation_ceiling(self):
        with self.assertRaisesRegex(ValueError, 'allocation_ceiling_failed'):
            apply_map_budget_policy(self.report(11 * 1024 * 1024), 'warning')

    def test_pass_stays_pass_and_unknown_policy_rejects(self):
        self.assertEqual(apply_map_budget_policy(self.report(5 * 1024 * 1024))['status'], 'estimate_passed')
        with self.assertRaisesRegex(ValueError, 'strict or warning'):
            apply_map_budget_policy(self.report(5 * 1024 * 1024), 'ignore')

    def test_malformed_budget_remains_error(self):
        report = self.report(5 * 1024 * 1024)
        report['safety_headroom_bytes'] = 0
        with self.assertRaisesRegex(ValueError, 'Invalid heap'):
            apply_map_budget_policy(report, 'warning')
