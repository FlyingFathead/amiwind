# SPDX-License-Identifier: GPL-3.0-only
"""Stage outputs carry no wall time, worker counts or run paths (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33,
BUILD-SURVEY-NOT-REPRODUCIBLE-33): a stage that runs again on the same inputs writes the same bytes, so the
stages after it are reused. Timings go to the stage log (a diagnostic, tools/build_cache.py)."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

# (module, the name of the dict/receipt variable it writes as a stage output)
WRITERS = (('tools/survey_vvardenfell.py', 'report'),
           ('tools/prepare_tree_sprites.py', 'receipt'),
           ('tools/prepare_world_scenery.py', 'receipt'),
           ('tools/prepare_world_scenery.py', 'report'),
           ('tools/prepare_world_regions.py', 'metrics'),
           ('tools/chim/build.py', 'receipt'))
VOLATILE = {'seconds', 'wall_seconds', 'cpu_seconds', 'workers', 'jobs', 'started_at', 'finished_at', 'timing'}


def written_keys(tree, variable):
    """Keys put into VARIABLE: dict(...) keywords and literal keys assigned to it, .update(...) keywords and
    literal keys, and VARIABLE[...] = assignments."""
    keys = set()
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
            value = node.value
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'update' \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == variable:
            keys.update(k.arg for k in node.keywords if k.arg)
            for arg in node.args:
                if isinstance(arg, ast.Dict):
                    keys.update(k.value for k in arg.keys if isinstance(k, ast.Constant))
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                                                  and t.value.id == variable and isinstance(t.slice, ast.Constant)
                                                  for t in node.targets):
            keys.update(t.slice.value for t in node.targets if isinstance(t, ast.Subscript)
                        and isinstance(t.slice, ast.Constant))
        if isinstance(value, ast.Call) and getattr(value.func, 'id', None) == 'dict':
            keys.update(k.arg for k in value.keywords if k.arg)
        elif isinstance(value, ast.Dict):
            keys.update(k.value for k in value.keys if isinstance(k, ast.Constant))
    return keys


class StageOutputDeterminismTests(unittest.TestCase):
    def test_no_wall_time_or_worker_count_in_stage_receipts(self):
        for module, variable in WRITERS:
            tree = ast.parse((ROOT / module).read_text(encoding='utf-8'))
            keys = written_keys(tree, variable)
            self.assertTrue(keys, (module, variable))
            self.assertEqual(sorted(keys & VOLATILE), [], (module, variable))

    def test_flora_packing_report_names_no_run_path(self):
        text = (ROOT / 'tools/prepare_world_flora.py').read_text(encoding='utf-8')
        self.assertNotIn("'candidate_directory':str(local)", text)
        self.assertIn("'candidate_directory':local.name", text)

    def test_chim_build_figures_are_a_diagnostic(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        import build_cache
        from chim.build import TIMING_FILE
        self.assertTrue(build_cache.diagnostic('chim-world/' + TIMING_FILE))
        self.assertTrue(build_cache.diagnostic('intro-scene/area-work/x/light.log'))
        self.assertFalse(build_cache.diagnostic('chim-world/chim-receipt.json'))


if __name__ == '__main__':
    unittest.main()
