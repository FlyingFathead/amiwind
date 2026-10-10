# SPDX-License-Identifier: GPL-3.0-only
"""The world survey's outputs hold no wall time, so a rerun on the same inputs writes the same bytes and its
dependents can be reused (BUILD-SURVEY-NOT-REPRODUCIBLE-33)."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SurveyReproducible(unittest.TestCase):
    def test_report_has_no_clock(self):
        tree = ast.parse((ROOT / 'tools/survey_vvardenfell.py').read_text(encoding='utf-8'))
        reports = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'report' for t in node.targets)]
        self.assertTrue(reports, 'survey report assignment not found')
        for value in reports:
            for node in ast.walk(value):
                if isinstance(node, ast.keyword):
                    self.assertNotIn(node.arg, ('seconds', 'elapsed', 'wall', 'started', 'finished'))
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    self.assertNotEqual(node.value.id, 'time', 'clock read inside the survey report')
                    self.assertNotEqual(node.value.id, 'datetime', 'clock read inside the survey report')


if __name__ == '__main__':
    unittest.main()
