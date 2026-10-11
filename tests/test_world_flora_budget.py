# SPDX-License-Identifier: GPL-3.0-only
"""World flora fails fast on its reserves (BUILD-FLORA-STAIR-PLATES-BUDGET-36): the maps whose scenery already fills
most of a reserve are converted first, in parallel; if one of them cannot be packed the stage stops at once with the
map and its numbers, before every other map. Synthetic maps only (header + lump sizes)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import prepare_world_flora as F  # noqa: E402
from player_hull import pack_lumps  # noqa: E402


def scene(models, clipnodes):
    lumps = [b''] * 15
    lumps[9] = bytes(8 * clipnodes)
    lumps[14] = bytes(64 * models)
    return pack_lumps(lumps)


def worker(task):
    """A stand-in for convert_region_cached: maps named bad* fail as the reserve check reports them."""
    name = task[5]['name']
    if name.startswith('bad'):
        return {'name': name, 'conversion_status': 'failed', 'error_type': 'FloraReserveError',
                'error': str({'attempts': [{'violations': [{'metric': 'clipnodes', 'actual': 33172, 'limit': 32767}]}]})}
    return {'name': name, 'source_references': []}


def tasks(names):
    return [(None, None, None, None, None, {'name': n}, False, 'adaptive', None, {}) for n in names]


class Budget(unittest.TestCase):
    def test_share_and_order_largest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            sizes = {'vf0001': (10, 1000), 'vf0002': (184, 26958), 'vf0003': (40, 30137), 'vf0004': (200, 100)}
            for name, (m, c) in sizes.items():
                (base / name).mkdir()
                (base / name / 'scene.bsp').write_bytes(scene(m, c))
            share, figures = F.budget_share(base / 'vf0003' / 'scene.bsp')
            self.assertAlmostEqual(share, 30137 / 32767)
            self.assertEqual(figures, {'base_models': 40, 'base_clipnodes': 30137})
            risky, rest, shares = F.budget_order(base, [{'name': n} for n in sizes], jobs=2)
            self.assertEqual([e['name'] for e in risky], ['vf0003', 'vf0004', 'vf0002'])   # 92 %, 83 %, 82 %
            self.assertEqual([e['name'] for e in rest], ['vf0001'])

    def test_a_failure_among_the_first_stops_before_the_rest(self):
        seen = []

        def counted(task):
            seen.append(task[5]['name'])
            return worker(task)
        with self.assertRaises(F.FloraBudgetError) as caught:
            F.convert_budget_first(tasks(['ok1', 'bad779', 'ok2', 'ok3', 'ok4']), 2, 1, worker=counted)
        error = caught.exception
        self.assertEqual(seen, ['ok1', 'bad779'])                    # nothing of the rest started
        self.assertEqual(error.not_started, 3)
        self.assertEqual([f['name'] for f in error.failures], ['bad779'])
        self.assertIn('bad779 (clipnodes 33172 > 32767)', str(error))

    def test_failures_after_the_first_are_returned_as_before(self):
        converted, failures = F.convert_budget_first(tasks(['ok1', 'ok2', 'bad3']), 2, 1, worker=worker)
        self.assertEqual([r['name'] for r in converted], ['ok1', 'ok2'])
        self.assertEqual([f['name'] for f in failures], ['bad3'])

    def test_the_stage_uses_it(self):
        import inspect
        source = inspect.getsource(F.prepare)
        self.assertIn('budget_order(base,pending', source)
        self.assertIn('convert_budget_first(tasks,len(risky)', source)


if __name__ == '__main__':
    unittest.main()
