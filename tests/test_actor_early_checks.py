# SPDX-License-Identifier: GPL-3.0-only
"""The outdoor creatures' models early check (OUTDOOR-CREATURES-REGRESSION-66, tools/actor_early_checks.py): every
creature the base game places outdoors and every outdoor levelled list must give a creature with a model in the actor
library, checked on the library stage's own output (phase stored and after:actor-library of tools/build_preflight.py
EARLY_CHECKS) in seconds, before the world stages. The synthetic master of tests/test_chim_levelled.py: outdoors the
lists all_lev, top_lev, outer (a list inside a list), late (only the cliff racer and an unknown id), the crab placed,
and a villager (an NPC: not a creature)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.append(str(p))

import actor_early_checks as aec  # noqa: E402
import build_preflight as bp  # noqa: E402


class MissingModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import test_chim_levelled as L
        cls.master = L.MASTER

    def test_a_list_of_unmodelled_creatures_is_named(self):
        placed, lev, n = aec.missing_models(self.master, {'crab': 'x', 'rat': 'x'})
        self.assertEqual((placed, lev), ([], ['late']))
        self.assertEqual(n, {'creatures': 1, 'levelled': 4})

    def test_the_library_without_creatures_fails_on_all_of_them(self):
        # the "lost all hostile creatures" case: no creature model in the library, so the engine spawns none
        placed, lev, _n = aec.missing_models(self.master, {})
        self.assertEqual(placed, ['crab'])
        self.assertEqual(lev, ['all_lev', 'late', 'outer', 'top_lev'])

    def test_every_creature_with_a_model_passes(self):
        self.assertEqual(aec.missing_models(self.master, {'crab': 'x', 'rat': 'x', 'racer': 'x'})[:2], ([], []))

    def test_a_nested_list_counts_through_its_inner_list(self):
        # outer gives the inner list "maybe" (rat, crab) or the fish: the rat alone is enough
        placed, lev, _n = aec.missing_models(self.master, {'rat': 'x', 'racer': 'x'})
        self.assertEqual((placed, lev), (['crab'], []))


class Wiring(unittest.TestCase):
    def test_registered_in_both_phases(self):
        rows = [(n, p, t) for n, p, t in bp.EARLY_CHECKS if n == 'outdoor-creature-models']
        self.assertEqual(rows, [('outdoor-creature-models', 'stored', 'actor_early_checks:exterior_creature_models'),
                                ('outdoor-creature-models', 'after:actor-library',
                                 'actor_early_checks:exterior_creature_models_after')])

    def test_stored_phase_skips_a_library_this_build_makes(self):
        lines = []
        ctx = bp.EarlyContext('stored', steps=['actor-library'], log=lines.append)
        self.assertEqual(aec.exterior_creature_models(ctx), [])
        self.assertIn('checked the moment it has passed', lines[0])
        self.assertEqual(aec.exterior_creature_models(bp.EarlyContext('stored', steps=['image'])), [])

    def test_the_game_data_from_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = bp.EarlyContext('after:actor-library', run=tmp)
            self.assertIsNone(aec._data_files(ctx, tmp))
            (Path(tmp) / 'build-state.json').write_text(json.dumps({'data_files': '/owned'}), encoding='utf-8')
            self.assertEqual(aec._data_files(ctx, tmp), Path('/owned'))

    def test_a_missing_manifest_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = aec.check_library(tmp, tmp, log=lambda line: None)
        self.assertEqual(len(got), 1)
        self.assertIn('has no creature-library.json', got[0])


if __name__ == '__main__':
    unittest.main()
