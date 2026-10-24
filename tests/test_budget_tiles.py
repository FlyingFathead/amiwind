# SPDX-License-Identifier: GPL-3.0-only
"""chim.budget_tiles (CHIM-ROOM-CLIPNODE-BUDGET-48): a model whose standing hull is over one brush image's clipnode
budget is stored as tiles of its own frame. The whole model is refused by the image writer; its tiles each fit, hold
every piece exactly once, and their clipnodes add up to the whole chain. The variant run names the over-budget unit
and keeps every other unit's result; other errors stop it as before."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import budget_tiles as B  # noqa: E402
from chim import cut as C  # noqa: E402
from chim.models import BrushLumps, hull_pieces, model_image_lumps  # noqa: E402
from routed_hull import CLIPNODE_LIMIT  # noqa: E402


def plate_shell(n=64, size=1024.0):
    """A cave-like shell of authored plates: n x n thin sloped plates over a size x size floor (two per cell), like the
    hollow collision plates of a cave mesh, with one face per plate."""
    step = size / n
    parts, surfaces = [], []
    rng = np.random.default_rng(48)
    ax = np.array([[0.5, 0.0], [0.0, 0.5], [0.0, 0.0]])
    for i in range(n):
        for j in range(n):
            x, y = i * step, j * step
            z = rng.uniform(0, 24, size=4)
            corners = [(x, y, z[0]), (x + step, y, z[1]), (x + step, y + step, z[2]), (x, y + step, z[3])]
            for tri in ((0, 1, 2), (0, 2, 3)):
                q = np.array([corners[k] for k in tri], float)
                pts = np.vstack([q, q - [0, 0, 0.5]])
                parts.append((pts, None, [len(parts)], 0.0))
            q = np.array(corners, float)
            surfaces.append((q, np.array([0.0, 0.0, 1.0]), ax, np.array([0.0, 0.0]), 0))
    return surfaces, parts


def tiles_of(surfaces, parts):
    """chim.cut.tile_unit's image step on prepared faces and pieces (exact standing bevels, as the cave shells)."""
    def run(task):
        out = []
        for t, (surfs, prts, c) in sorted(C.model_tiles(surfaces, parts, task['grain']).items()):
            allp = np.vstack([np.asarray(s[0]) for s in surfs] + [p for p, *_ in prts])
            lumps, _ = model_image_lumps(surfs, prts, allp.min(axis=0) - 1, allp.max(axis=0) + 1, lambda m: 0, True,
                                         None, b'', hull='chain')
            out.append({'tile': list(t), 'centre': list(c), 'lumps': lumps, 'pieces': len(prts),
                        'lo': list(allp.min(axis=0) - 1), 'hi': list(allp.max(axis=0) + 1), 'materials': {('k',): 0}})
        return out
    return run


class BudgetTilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surfaces, cls.parts = plate_shell()
        probe = BrushLumps()
        try:
            probe.collider(hull_pieces(cls.parts), True, None, point_hull=False)
            cls.whole = None
        except ValueError as error:
            cls.whole = error

    def test_the_whole_model_is_over_the_budget(self):
        self.assertIsNotNone(self.whole)
        self.assertTrue(B.over_budget(self.whole), self.whole)
        with self.assertRaises(ValueError) as caught:
            model_image_lumps(self.surfaces, self.parts, np.zeros(3), np.full(3, 1024.0), lambda m: 0, True, None,
                              b'', hull='auto')
        self.assertTrue(B.over_budget(caught.exception))

    def test_tiles_fit_and_hold_every_piece_once(self):
        grain, tiles = B.fit_tiles({'grain': 256.0}, tiles_of(self.surfaces, self.parts))
        self.assertLessEqual(len(tiles), B.TILE_MAX)
        self.assertEqual(sum(t['pieces'] for t in tiles), len(self.parts))
        clip = sum(len(t['lumps'][9]) // 8 for t in tiles)
        self.assertGreater(clip, CLIPNODE_LIMIT)              # more than one image holds
        for t in tiles:
            self.assertLess(len(t['lumps'][9]) // 8, CLIPNODE_LIMIT)
        # the pieces moved back by their tile centre are the model's pieces (the solid does not change)
        moved = sorted(tuple(np.round((p + c).ravel(), 4)) for (_, prts, c) in
                       C.model_tiles(self.surfaces, self.parts, grain).values() for p, *_ in prts)
        self.assertEqual(moved, sorted(tuple(np.round(np.asarray(p).ravel(), 4)) for p, *_ in self.parts))
        lo, hi, mats = B.whole_of(tiles)
        self.assertEqual(mats, {('k',): 0})
        self.assertTrue(all(a <= 0.0 for a in lo[:2]) and all(b >= 1024.0 for b in hi[:2]))

    def test_the_grain_halves_until_every_tile_fits(self):
        calls = []

        def run(task):
            calls.append(task['grain'])
            if task['grain'] > 64:
                raise ValueError('Clipnode budget exceeded')
            return [{'tile': [0, 0]}]
        self.assertEqual(B.fit_tiles({'grain': 256.0}, run)[0], 64.0)
        self.assertEqual(calls, [256.0, 128.0, 64.0])
        with self.assertRaises(ValueError):
            B.fit_tiles({'grain': 256.0}, lambda task: (_ for _ in ()).throw(ValueError('Clipnode budget exceeded')))
        with self.assertRaises(ValueError):                   # too many tiles
            B.fit_tiles({'grain': 256.0}, lambda task: [{}] * (B.TILE_MAX + 1))

    def test_the_variant_run_names_the_unit_over_the_budget_in_one_run(self):
        # CHIM-BUDGET-RERUN-SERIAL-48: the over-budget unit is named in the first run; nothing runs again
        runs = []

        def run_units(kind, items, worker, jobs, cache, soft=None):
            runs.append((len(items), jobs, soft))
            from chim.units import SoftError
            return [SoftError('Clipnode budget exceeded: 162975') if task == 'big' else {'fp': fp}
                    for fp, task in items]
        lines = []
        out = B.run_fitting(run_units, 'variant', [('a', 'x'), ('b', 'big'), ('c', 'y')], None, 4, None,
                            log=lines.append)
        self.assertEqual(out, [{'fp': 'a'}, {'over_budget': 'Clipnode budget exceeded: 162975'}, {'fp': 'c'}])
        self.assertEqual(runs, [(3, 4, B.BUDGET_ERRORS)])
        self.assertIn('b', lines[0])

    def test_named_run_equals_the_serial_rerun_and_caches_the_verdict(self):
        # the real chim.units.run_units: the same results as the method before (AMIWIND_BUDGET_RERUN=serial); the
        # fitting units are cached as before, and the over-budget verdict is cached too, so the next run takes it from
        # the cache instead of making the model again (CHIM-ROOM-OVER-BUDGET-RETRY-48)
        import os
        import tempfile
        from unittest import mock
        from chim.units import UnitCache, run_units
        items = [('aa01', 'x'), ('bb02', 'big'), ('cc03', 'y'), ('dd04', 'big2')]
        results = {}
        for method in ('named', 'serial'):
            with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'AMIWIND_BUDGET_RERUN': method}):
                cache = UnitCache(tmp)
                out = B.run_fitting(run_units, 'variant-test', items, _budget_worker, 1, cache, log=lambda m: 0)
                stored = sorted(p.stem for p in Path(tmp).rglob('*.pickle'))
                results[method] = (out, stored)
                if method == 'named':
                    # again: nothing is made, the verdicts come from the cache
                    again = B.run_fitting(run_units, 'variant-test', items, _never_called, 1, cache, log=lambda m: 0)
                    self.assertEqual(again, out)
                    # the method before on the same cache: the cached verdicts count as misses, the same results
                    with mock.patch.dict(os.environ, {'AMIWIND_BUDGET_RERUN': 'serial'}):
                        self.assertEqual(B.run_fitting(run_units, 'variant-test', items, _budget_worker, 1, cache,
                                                       log=lambda m: 0), out)
        self.assertEqual(results['named'][0], results['serial'][0])
        self.assertEqual(results['serial'][1], ['aa01', 'cc03'])
        self.assertEqual(results['named'][1], ['aa01', 'bb02', 'cc03', 'dd04'])
        self.assertIn('Clipnode budget exceeded', results['named'][0][1]['over_budget'])
        self.assertIn('Vertex budget exceeded', results['named'][0][3]['over_budget'])

    def test_named_run_raises_other_errors(self):
        from chim.units import run_units
        with self.assertRaises(ValueError):
            B.run_fitting(run_units, 'variant-test', [('aa01', 'x'), ('ee05', 'bad')], _budget_worker, 1, None)

    def test_the_serial_rerun_method_names_the_unit_over_the_budget(self):
        import os
        from unittest import mock
        runs = []

        def run_units(kind, items, worker, jobs, cache):
            runs.append(len(items))
            out = []
            for fp, task in items:
                if task == 'big':
                    raise ValueError('Clipnode budget exceeded')
                out.append({'fp': fp})
            return out
        with mock.patch.dict(os.environ, {'AMIWIND_BUDGET_RERUN': 'serial'}):
            out = B.run_fitting(run_units, 'variant', [('a', 'x'), ('b', 'big'), ('c', 'y')], None, 4, None,
                                log=lambda m: 0)
            self.assertEqual(out[0], {'fp': 'a'})
            self.assertEqual(out[2], {'fp': 'c'})
            self.assertIn('Clipnode budget exceeded', out[1]['over_budget'])
            self.assertEqual(runs, [3, 1, 1, 1])
            # a run with no budget error runs once, unchanged
            runs.clear()
            self.assertEqual(B.run_fitting(run_units, 'variant', [('a', 'x')], None, 4, None), [{'fp': 'a'}])
            self.assertEqual(runs, [1])

    def test_other_errors_stop_the_run(self):
        def run_units(kind, items, worker, jobs, cache, soft=None):
            raise ValueError('Unknown model weld mode: x')
        with self.assertRaises(ValueError):
            B.run_fitting(run_units, 'variant', [('a', 'x')], None, 1, None)


def _never_called(task):
    raise AssertionError('made again: %r' % (task,))


def _budget_worker(task):
    """A unit worker for the run_fitting tests: 'big'/'big2' are over a budget, 'bad' is another error."""
    if task == 'big':
        raise ValueError('Clipnode budget exceeded: 162975 clipnodes, at most 65520')
    if task == 'big2':
        raise ValueError('Vertex budget exceeded: 70000 vertices')
    if task == 'bad':
        raise ValueError('Unknown model weld mode: x')
    return {'made': task}


if __name__ == '__main__':
    unittest.main()
