# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-STATS-SERIAL-36: the CHIM stats on the worker pool (build_parallel.in_order_map, the models' facts once for
the stats and the cameras, the source manifest's frame cells handed over instead of parsed again, timed phases) write
the same chim-stats.json, byte for byte, as the method before (AMIWIND_STATS_POOL=off, AMIWIND_JSON_POOL=ordered)."""
import json
import os
import random
import statistics
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_parallel  # noqa: E402
import parallel_json  # noqa: E402
from chim import stats as S  # noqa: E402
from chim.validate import measure, validate  # noqa: E402
from test_chim_format import CENTRE, fixture  # noqa: E402

BEFORE = {'AMIWIND_STATS_POOL': 'off', 'AMIWIND_JSON_POOL': 'ordered'}
NOW = {'AMIWIND_STATS_POOL': 'on', 'AMIWIND_JSON_POOL': 'in-order'}


def _square(x):
    return x * x


class InOrderMapTests(unittest.TestCase):
    def test_results_in_input_order_with_and_without_cost(self):
        # (a builtin as the worker: spawned workers import it without this test module)
        items = [-x for x in range(60)]
        for cost in (None, lambda x: (x * 37) % 11):
            with self.subTest(cost=cost is not None):
                self.assertEqual(list(build_parallel.in_order_map(abs, items, 3, cost=cost)), [abs(x) for x in items])
        self.assertEqual(list(build_parallel.in_order_map(_square, items, 1)), [x * x for x in items])
        self.assertEqual(list(build_parallel.in_order_map(abs, [], 3)), [])

    def test_in_order_map_is_a_scheduling_unit(self):
        import build_cache
        for name in ('in_order_map', '_indexed_call'):
            self.assertIn(('tools/build_parallel.py', name), build_cache.SCHEDULING_UNITS)
        for name in ('AMIWIND_STATS_POOL', 'AMIWIND_JSON_POOL', 'AMIWIND_BUDGET_RERUN'):
            self.assertIn(name, build_cache.IGNORED_ENV)

    def test_parallel_json_text_is_the_same_either_way(self):
        doc = {'a': {'rows': [[i, i * 3, 'x%d' % i] for i in range(3000)]}, 'b': [{'k': i} for i in range(700)]}
        want = json.dumps(doc, indent=1, sort_keys=True)
        for env in (BEFORE, NOW):
            with mock.patch.dict(os.environ, env):
                self.assertEqual(parallel_json.dumps(doc, [('a', 'rows'), ('b',)], jobs=3), want)


class DistributionTests(unittest.TestCase):
    def test_whole_numbers_as_statistics_mean_gives_them(self):
        rnd = random.Random(36)
        cases = [[2, 4], [7], [1, 2], [0, 0, 0], [-3, 5, 1], [10 ** 18, 3, 7]]
        cases += [[rnd.randrange(-50, 10 ** rnd.randrange(1, 9)) for _ in range(rnd.randrange(1, 300))]
                  for _ in range(300)]
        cases += [[1.5, 2.25, 3], [True, 2], [3, 3.0]]          # not all ints: the method before
        for values in cases:
            with mock.patch.dict(os.environ, BEFORE):
                before = S.distribution(values)
            with mock.patch.dict(os.environ, NOW):
                now = S.distribution(values)
            self.assertEqual(json.dumps(now), json.dumps(before), values[:10])
            self.assertEqual(type(now['mean']), type(round(statistics.mean(values), 2)))


class StatsPoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'w'
        cls.receipt, cls.source = fixture(cls.out)
        src = cls.out / 'chim-source.json'
        if not src.is_file():
            src.write_text(json.dumps(cls.source), encoding='utf-8')
        fails, cls.world = validate(cls.out, cls.source)
        assert not fails, fails
        cls.cameras = ['--camera', 'west', str(CENTRE[0] - 460 * 4), str(CENTRE[1] + 40 * 4),
                       '--camera', 'centre', str(CENTRE[0]), str(CENTRE[1])]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def written(self, env, name, jobs, source=None):
        measured = measure(self.world, self.source)
        target = self.out / name
        with mock.patch.dict(os.environ, env), mock.patch.object(S, 'MODEL_GROUP', 1):
            self.assertEqual(S.main([str(self.out), '--json', str(target)] + self.cameras, self.world, measured,
                                    jobs=jobs, source=source), 0)
        return target.read_bytes()

    def test_pooled_stats_equal_the_method_before_byte_for_byte(self):
        before = self.written(BEFORE, 'before.json', 1)
        self.assertEqual(self.written(BEFORE, 'before-2.json', 2), before)
        self.assertEqual(self.written(NOW, 'now.json', 2, S.source_cells(self.source)), before)
        self.assertEqual(self.written(NOW, 'now-1.json', 1, S.source_cells(self.source)), before)
        # without the handed-over cells the manifest is read, as before
        self.assertEqual(self.written(NOW, 'now-read.json', 2), before)

    def test_source_cells_keep_what_the_stats_read(self):
        cells = S.source_cells({'frames': [{'town': 'a', 'cell': [1, 2], 'placements': [1] * 9}, {'cell': [0, 0]}],
                                'placements': [0] * 5})
        self.assertEqual(cells, {'frames': [{'town': 'a', 'cell': [1, 2]}, {'cell': [0, 0]}]})
        self.assertEqual(S.source_cells(None), {'frames': []})

    def test_every_section_is_a_timed_phase(self):
        import contextlib
        import io
        text = io.StringIO()
        with mock.patch.dict(os.environ, NOW), contextlib.redirect_stdout(text):
            self.written(NOW, 'phases.json', 2, S.source_cells(self.source))
        for name in ('model faces and textures', 'cameras', 'placements and chunks', 'views and disk',
                     'resident rings', 'memory, streaming and pain points', 'writing'):
            self.assertIn('CHIM stats: %s: started' % name, text.getvalue())


if __name__ == '__main__':
    unittest.main()
