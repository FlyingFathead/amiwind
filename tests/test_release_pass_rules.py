# SPDX-License-Identifier: GPL-3.0-only
"""Release rules of the image step's per-map passes (owner decisions, 9 October 2026):

1. the per-map pass cache is used by release candidates and finals only with --allow-release-reuse
   (the from-scratch reference build is compared file by file before the release), and every pass
   receipt counts its hits and misses;
2. the stair walk covers only the steps of flights (the rows that can fail the gate) in release
   candidates and finals, and every step and ramp in development builds and nightly full reports
   (--stair-walk all); a flight row is the same in both walks.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests'), str(ROOT / 'src')]
import pass_cache  # noqa: E402


class PassCacheReleaseRule(unittest.TestCase):
    def test_release_builds_use_the_cache_only_with_release_reuse(self):
        for version in ('0.0.34', '0.0.34-rc1'):
            self.assertEqual(pass_cache.setting(version, '/w'), 'off', version)
            self.assertEqual(pass_cache.setting(version, '/w', allow_release_reuse=False), 'off', version)
            self.assertEqual(Path(pass_cache.setting(version, '/w', allow_release_reuse=True)).parts[-2:],
                             ('cache', 'image-passes'), version)
        self.assertEqual(Path(pass_cache.setting('0.0.34-dev3', '/w')).parts[-2:], ('cache', 'image-passes'))

    def test_optimizer_receipt_counts_hits_and_misses(self):
        from optimize_world_maps import optimize_maps
        from test_pass_cache import PassCacheTests
        maker = PassCacheTests()
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            with patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache')}):
                cold = optimize_maps(maker.maps(root / 'cold', maker.optimizer_inputs), root / 'cold.json', jobs=2)
                warm = optimize_maps(maker.maps(root / 'warm', maker.optimizer_inputs), root / 'warm.json', jobs=2)
            # Three maps, two distinct inputs: a.bsp and c.bsp share one entry.
            self.assertEqual(cold['pass_cache']['hits'] + cold['pass_cache']['misses'], 3)
            self.assertEqual((warm['pass_cache']['hits'], warm['pass_cache']['misses']), (3, 0))
            saved = json.loads((root / 'warm.json').read_text())
            self.assertEqual(saved['pass_cache']['hits'], 3)


class StairWalkScope(unittest.TestCase):
    def payload(self, root, fill):
        from test_stair_walk import build
        maps = Path(root) / 'maps'
        maps.mkdir(parents=True)
        (maps / 'hall.bsp').write_bytes(build(fill=fill))
        (maps / 'tall.bsp').write_bytes(build(rise=7.))
        return Path(root)

    def test_flights_scope_walks_exactly_the_flight_rows_of_a_full_walk(self):
        import stair_walk
        for fill in (False, True):
            with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {pass_cache.ENV: 'off'}):
                id1 = self.payload(temp, fill)
                full = stair_walk.check(id1, jobs=1, scope='all')
                flights = stair_walk.check(id1, jobs=1, scope='flights')
            self.assertTrue(flights['rows'])
            self.assertEqual(json.dumps(flights['rows']), json.dumps([r for r in full['rows'] if r.get('flight')]))
            self.assertEqual(json.dumps(flights['failures']), json.dumps(full['failures']))
            self.assertEqual(flights['status'], full['status'])
            self.assertIn('scope', flights)
            self.assertNotIn('scope', full)        # a full walk's receipt is unchanged

    def test_only_flight_candidates_are_walked(self):
        import stair_walk
        items = [dict(kind='step', flight=True), dict(kind='step', flight=False), dict(kind='ramp'),
                 dict(kind='ramp', flight=True)]
        self.assertEqual(stair_walk.flight_items(items), [items[0], items[3]])

    def test_scope_from_the_builder_variable(self):
        import stair_walk
        with patch.dict(os.environ, {stair_walk.SCOPE_ENV: ''}):
            self.assertEqual(stair_walk.scope_setting(), 'all')
        with patch.dict(os.environ, {stair_walk.SCOPE_ENV: 'flights'}):
            self.assertEqual(stair_walk.scope_setting(), 'flights')
        with patch.dict(os.environ, {stair_walk.SCOPE_ENV: 'some'}):
            with self.assertRaises(ValueError):
                stair_walk.scope_setting()

    def test_flights_and_all_keep_separate_cache_entries(self):
        import stair_walk
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            id1 = self.payload(Path(temp) / 'p', False)
            with patch.dict(os.environ, {pass_cache.ENV: str(Path(temp) / 'cache')}):
                stair_walk.check(id1, jobs=1, scope='all')
                flights = stair_walk.check(id1, jobs=1, scope='flights')
            self.assertEqual(flights['pass_cache']['hits'], 0)   # never the rows of the other scope

    def test_builder_scope_by_version(self):
        import build
        self.assertEqual(build.stair_walk_scope('0.0.34-dev3'), 'all')
        self.assertEqual(build.stair_walk_scope('0.0.34-rc1'), 'flights')
        self.assertEqual(build.stair_walk_scope('0.0.34'), 'flights')
        self.assertEqual(build.stair_walk_scope('0.0.34', 'all'), 'all')          # nightly full report
        self.assertEqual(build.stair_walk_scope('0.0.34-dev3', 'flights'), 'flights')
        with self.assertRaises(ValueError):
            build.stair_walk_scope('0.0.34', 'some')
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("STAIR_WALK_ENV = 'AMIWIND_STAIR_WALK'", text)
        import stair_walk
        self.assertEqual(stair_walk.SCOPE_ENV, 'AMIWIND_STAIR_WALK')


if __name__ == '__main__':
    unittest.main()
