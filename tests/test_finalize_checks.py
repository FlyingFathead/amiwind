# SPDX-License-Identifier: GPL-3.0-only
"""Every check of the image step's last part is tried early, or tools/finalize_checks.py says why not.

A build with Mournhold's districts stopped in that last part, in the door check, 1 h 34 min after it started
(DOOR-CHECK-MODULE-FRAME-MAPS-67). This test reads tools/build_aga.py finalize_image and fails when a call there is
not in the table: a new check cannot be added to the image's last part without deciding how a build learns of its
failure early."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import build_preflight  # noqa: E402
import finalize_checks as F  # noqa: E402


class EveryCallIsInTheTable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls = F.finalize_calls((ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8'))

    def test_every_call_of_the_images_last_part_is_listed_once(self):
        listed = set(F.CHECKS) | set(F.WORK)
        self.assertEqual(sorted(self.calls - listed), [],
                         'new calls in build_aga.finalize_image: list each in tools/finalize_checks.py, as a check '
                         '(with the early check that tries it, or why none can yet) or as work')
        self.assertEqual(sorted(listed - self.calls), [], 'listed in tools/finalize_checks.py but no longer called')
        self.assertEqual(sorted(set(F.CHECKS) & set(F.WORK)), [])

    def test_a_name_that_reads_as_a_check_is_never_listed_as_work(self):
        self.assertEqual(sorted(name for name in F.WORK if F.reads_as_check(name)), [])
        self.assertTrue(F.reads_as_check('require_frame_map_heap'))
        self.assertTrue(F.reads_as_check('entity_gate'))
        self.assertFalse(F.reads_as_check('install_layer_stores'))

    def test_a_check_names_a_registered_early_check_or_says_why_it_has_none(self):
        registered = {name for name, _phase, _target in build_preflight.EARLY_CHECKS}
        for name, row in F.CHECKS.items():
            self.assertTrue(row.get('why'), name)
            if row['early'] is not None:
                self.assertIn(row['early'], registered, name)
        # the door check is tried in the first minute on a module's frame map names
        self.assertEqual(F.CHECKS['write_door_check']['early'], 'module-frame-maps')
        phases = {name: phase for name, phase, _target in build_preflight.EARLY_CHECKS}
        self.assertEqual(phases['module-frame-maps'], 'inputs')

    def test_the_open_list_is_the_checks_without_an_early_one(self):
        still = dict(F.not_tried_early())
        self.assertNotIn('write_door_check', still)
        self.assertNotIn('check_engine_map_limits', still)       # tried after a module's world stage, on its maps
        self.assertIn('require_frame_map_heap', still)
        self.assertEqual(len(still), sum(1 for row in F.CHECKS.values() if not row['early']))

    def test_the_call_reader_finds_imports_inside_the_function_and_the_modules_own_functions(self):
        source = ('def own():\n    pass\n\ndef other():\n    pass\n\n'
                  'def finalize_image(args):\n    from m import require_x as rx, helper\n    own()\n    rx(1)\n'
                  '    print(helper)\n    len([])\n')
        self.assertEqual(F.finalize_calls(source), {'own', 'rx'})


if __name__ == '__main__':
    unittest.main()
