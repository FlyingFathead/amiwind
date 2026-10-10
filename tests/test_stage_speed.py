# SPDX-License-Identifier: GPL-3.0-only
"""Critical-path stage speed-ups keep their outputs: loop path choices in stage keys, split lit
placements, the stored-grid bake, background calls (docs/BUILD_PROFILE.md)."""
import ast
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import build_cache  # noqa: E402
from build_parallel import Background  # noqa: E402


def _choices(source):
    return build_cache.loop_choices(list(ast.walk(ast.parse(source))))


def _square(value):
    return value * value


class LoopChoicesTest(unittest.TestCase):
    def test_literal_loop_names_its_files(self):
        found = _choices("for name, file, reader in [('A', 'a.json', f), ('B', 'b.json', g)]:\n"
                         "    read(ROOT / 'config' / file)\n")
        self.assertEqual(found, {'name': ('A', 'B'), 'file': ('a.json', 'b.json')})

    def test_rebound_or_computed_names_have_no_choices(self):
        for source in ("for file in ['a.json']:\n    pass\nfile = other()\n",
                       "for file in ['a.json', name]:\n    pass\n",
                       "def f(file):\n    for file in ['a.json']:\n        pass\n",
                       "for file in ['a.json']:\n    pass\ntry:\n    x()\nexcept E as file:\n    pass\n",
                       "for file in ['a.json']:\n    pass\nfor file in ['b.json']:\n    pass\n",
                       "for file in names:\n    pass\n"):
            self.assertNotIn('file', _choices(source), source)

    def test_path_with_loop_name_is_its_files_not_the_folder(self):
        tree = ast.parse("for file in ['a.json', 'b.json']:\n    read(ROOT / 'config' / file)\n")
        walked = list(ast.walk(tree))
        division = next(n for n in walked if isinstance(n, ast.BinOp) and isinstance(n.right, ast.Name))
        runs = build_cache._literal_runs(build_cache._flatten_path(division), {}, True, build_cache.loop_choices(walked))
        self.assertEqual(sorted(runs), [('config/a.json', False), ('config/b.json', False)])
        # Without choices the computed part leaves the folder open (the earlier reading).
        self.assertEqual(build_cache._literal_runs(build_cache._flatten_path(division), {}, True), [('config', True)])

    def test_world_survey_key_names_only_its_area_files(self):
        # BUILD-SURVEY-KEY-CONFIG-35: every config file used to be in the world survey's key.
        python, data, uncertain = build_cache.SourceIndex(ROOT).closure(ROOT / 'tools/survey_vvardenfell.py')
        self.assertFalse(uncertain)
        self.assertIn('config/balmora.json', data)
        self.assertIn('config/seyda_area.json', data)
        self.assertNotIn('config/harvest-pick-known.json', data)
        self.assertNotIn('config/seam-audit-known.json', data)


class SplitPlacementTest(unittest.TestCase):
    def test_split_tasks_join_to_the_single_task_result(self):
        import prepare_mesh_bsp as mesh
        rng = np.random.default_rng(3)
        polys = []
        for _ in range(mesh.BAKE_CHUNK * 2 + 5):
            polygon = rng.normal(size=(3, 3)) * 50
            axes = np.eye(3)[:, :2] / 32
            polys.append((polygon, 0, axes, np.zeros(2), np.cross(polygon[1] - polygon[0], polygon[2] - polygon[0])))
        v = np.concatenate([rng.normal(size=(8, 3)) * 40, np.zeros((8, 5))], axis=1)
        ref = {'number': 1, 'model_index': 0, 'position': [10., 20., 30.], 'rotation_radians': [0., 0., .3], 'scale': 1.}
        task = (ref, (v, None, polys, [], {}), 64, (0, 0), None, False, True)
        whole = mesh._prepare_placement(task)
        parts = mesh.split_placement(task)
        self.assertEqual(len(parts), 1 + 3)
        joined = mesh.join_placement([mesh._prepare_placement(part) for part in parts])
        self.assertEqual(len(whole[0]), len(joined[0]))
        for a, b in zip(whole[0], joined[0]):
            for x, y in zip(a[:4], b[:4]):
                self.assertTrue(np.array_equal(x, y))
        self.assertTrue(np.array_equal(whole[2], joined[2]) and np.array_equal(whole[3], joined[3]))
        self.assertEqual(mesh.split_placement((ref, (v, None, polys[:3], [], {}), 64)), [(ref, (v, None, polys[:3], [], {}), 64)])

    def test_stored_grid_is_the_engine_grid_of_stored_values(self):
        import prepare_mesh_bsp as mesh
        from surface_grid import engine_grid, sample_dimensions
        polygon = np.array([[0., 0., 0.], [32.0000001, 0., 0.], [0., 47.9999999, 0.]])
        axes = np.array([[1., 0.], [0., 1.], [0., 0.]])
        offset = np.zeros(2)
        low, size = mesh.placement_grid(polygon, axes, offset)
        mins, extents = engine_grid(polygon, [[*axes[:, 0], 0.], [*axes[:, 1], 0.]])
        self.assertEqual(tuple(low), mins)
        self.assertEqual(tuple(size), sample_dimensions(extents))


class BackgroundTest(unittest.TestCase):
    def test_background_matches_the_direct_call(self):
        self.assertEqual(Background(_square, 7, jobs=1).result(), 49)
        self.assertEqual(Background(_square, 7, jobs=2).result(), 49)


if __name__ == '__main__':
    unittest.main()
