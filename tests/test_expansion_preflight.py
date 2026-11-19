# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' first-minute check of the presented exteriors (tools/expansion_preflight.py). Small synthetic
masters: no game data."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import build_preflight  # noqa: E402
import expansion_preflight as ep  # noqa: E402
from test_presented_exterior import CONFIG, exterior, header, interior, master, ref  # noqa: E402


class PresentedExteriors(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.recipes = Path(self.tmp.name) / 'visual-recipes.json'

    def tearDown(self):
        self.tmp.cleanup()

    def write_recipes(self, cells, bare=None):
        """CELLS carry the districts' recipe; BARE (default: the same cells) carry the no-LAND mark."""
        bare = set(cells if bare is None else bare)
        rows = {}
        for c in sorted(set(cells) | bare):
            row = {}
            if c in set(cells):
                row['visual_recipe'] = ep.DISTRICT_RECIPE
            if c in bare:
                row[ep.NO_LAND] = True
            rows['%d,%d' % c] = row
        doc = {'recipes': {ep.DISTRICT_RECIPE: {'models': {}}}, 'cell_settings': rows}
        self.recipes.write_text(json.dumps(doc), encoding='utf-8')

    def test_the_no_land_mark_is_on_exactly_the_presented_cells(self):
        blocks = [(-12, -30), (-11, -30), (-8, -30)]
        self.write_recipes(blocks, bare=blocks[:2] + [(2, 2)])
        problems = ep.presented_problems(master(), True, self.recipes, CONFIG)
        self.assertEqual(len(problems), 2)
        self.assertIn('-8,-30', problems[0])
        self.assertIn('would refuse', problems[0])
        self.assertIn('2,2', problems[1])
        self.assertIn('without their terrain', problems[1])
        self.assertEqual(ep.no_land_cells(), ep.recipe_cells())          # the shipped file: the same eleven cells

    def test_the_blocks_cells_with_the_recipe_pass(self):
        self.write_recipes([(-12, -30), (-11, -30), (-8, -30)])      # the plaza's two cells and the yard's one
        self.assertEqual(ep.presented_problems(master(), True, self.recipes, CONFIG), [])

    def test_a_district_cell_without_the_recipe_and_a_recipe_cell_that_is_no_district_are_named(self):
        self.write_recipes([(-12, -30), (-8, -30), (3, 3)], bare=[(-12, -30), (-11, -30), (-8, -30)])
        problems = ep.presented_problems(master(), True, self.recipes, CONFIG)
        self.assertEqual(len(problems), 2)
        self.assertIn('-11,-30', problems[0])
        self.assertIn('3,3', problems[1])
        # without Tribunal selected the recipe is not held against the blocks
        self.assertEqual(ep.presented_problems(master(), False, self.recipes, CONFIG), [])

    def test_a_block_on_a_game_cell_is_a_problem_not_an_exception(self):
        self.write_recipes([])
        problems = ep.presented_problems(master() + exterior(-12, -31), True, self.recipes, CONFIG)
        self.assertEqual(len(problems), 1)
        self.assertIn('touches the game', problems[0])
        big = header(1) + interior('Big', 0x81, ref(1, 'wall', (0, 0, 0)), ref(2, 'wall', (30000, 0, 0)))
        self.assertIn('largest block', ep.presented_problems(big, False, self.recipes, CONFIG)[0])

    def test_the_base_game_alone_has_nothing_to_check(self):
        context = SimpleNamespace(masters=['Morrowind.esm'], data_files='/nowhere')
        self.assertEqual(ep.presented_exteriors(context), [])

    def test_a_pass_is_recorded_by_the_inputs_and_a_problem_never(self):
        from unittest.mock import patch
        data = Path(self.tmp.name) / 'data'
        data.mkdir()
        (data / 'Morrowind.esm').write_bytes(b'base')
        (data / 'Tribunal.esm').write_bytes(b'layer')
        work = Path(self.tmp.name) / 'work'
        lines = []
        context = SimpleNamespace(masters=['Morrowind.esm', 'Tribunal.esm'], data_files=str(data), workspace=work,
                                  log=lines.append)
        calls = []

        def answer(problems):
            def fake(merged, tribunal):
                calls.append(tribunal)
                return list(problems)
            return fake

        with patch('mwad.masters.master_bytes', lambda data_files, masters=None: b'merged'):
            with patch.object(ep, 'presented_problems', answer(['a block touches the game'])):
                self.assertEqual(ep.presented_exteriors(context), ['a block touches the game'])
                self.assertEqual(ep.presented_exteriors(context), ['a block touches the game'])
            self.assertEqual(calls, [True, True])                    # a problem is found again, never recorded
            with patch.object(ep, 'presented_problems', answer([])):
                self.assertEqual(ep.presented_exteriors(context), [])
                self.assertEqual(ep.presented_exteriors(context), [])
                self.assertEqual(len(calls), 3)                      # the second pass came from the record
                self.assertIn('passed before', lines[-1])
                (data / 'Tribunal.esm').write_bytes(b'another layer')  # other game files: checked again
                self.assertEqual(ep.presented_exteriors(context), [])
                self.assertEqual(len(calls), 4)
        self.assertEqual(len(list((work / ep.CACHE_FOLDER).glob('*.json'))), 2)

    def test_the_check_is_registered_for_the_first_minute(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'presented-exteriors']
        self.assertEqual(entry, [('presented-exteriors', 'inputs', 'expansion_preflight:presented_exteriors')])
        self.assertTrue(callable(ep.presented_exteriors))

    def test_the_shipped_recipe_cells_are_the_shipped_config_blocks_shape(self):
        """Without game data: the shipped recipe cells are eleven and lie in the row the shipped config lays out."""
        cells = ep.recipe_cells()
        self.assertEqual(len(cells), 11)
        import presented_exterior
        config = presented_exterior.load_config()
        self.assertTrue(all(config['first_block'][1] <= y < config['first_block'][1] + config['max_block']
                            for _, y in cells))


if __name__ == '__main__':
    unittest.main()
