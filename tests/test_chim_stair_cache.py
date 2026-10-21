# SPDX-License-Identifier: GPL-3.0-only
"""The stair walk is reused by content and the slow gates run last (BUILD-CHIM-STAIR-WALK-UNCACHED-36,
BUILD-CHIM-HEAP-GATE-LATE-36): an unchanged frame is not walked again, a changed one is, a sampled reused frame is
walked again and must match, and chim_build runs the heap gate and the zone walk before the stair walk."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]


class StairCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        os.environ['AMIWIND_PASS_CACHE'] = str(Path(self.tmp.name) / 'cache')
        os.environ['AMIWIND_STAIR_WALK_CACHE'] = 'cached'
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '0'
        # the frame key and the all scope (the methods before v0.0.46, kept selectable; the reach key and the
        # flights scope: tests/test_chim_stair_reach_key.py)
        os.environ.update(AMIWIND_STAIR_WALK_KEY='frame', AMIWIND_STAIR_WALK='all', AMIWIND_STAIR_WATCH='off')

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def world(self, name, heights_of=None):
        from test_chim_format import fixture
        out = Path(self.tmp.name) / name
        fixture(out, **({'heights_of': heights_of} if heights_of else {}))
        return out

    def gate(self, out):
        from chim.collision import stair_gate
        from chim.validate import Failures, load_world
        world = load_world(out, Failures())
        return stair_gate(out, world[5], 1, models=world[4])

    def promote(self, report, run='2026_10_10_v0.0.36-dev3_full_abc1234'):
        """The run that wrote these records passed as a master build: mark them (tools/stair_records.py)."""
        import stair_records
        folder = Path(self.tmp.name) / 'runs' / run
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'chim-stairs.json').write_text(json.dumps(report), encoding='utf-8')
        return stair_records.promote(folder, 'req-1')

    def test_only_records_of_a_passed_master_build_are_reused(self):
        # the check-mark rule (release candidates and finals; AMIWIND_STAIR_WALK_REUSE=checked for any build).
        # Development builds reuse a passed walk without the mark: tests/test_chim_stair_pass.py
        os.environ.update(AMIWIND_RUN_NAME='2026_10_10_v0.0.36-dev3_full_abc1234', AMIWIND_RUN_COMMIT='abc1234',
                          AMIWIND_RUN_VERSION='0.0.36-dev3', AMIWIND_STAIR_WALK_REUSE='checked')
        first = self.gate(self.world('a'))
        self.assertEqual((first['pass_cache']['reused'], first['pass_cache']['walked']), (0, 1))
        self.assertEqual(len(first['pass_cache']['stored']), 1)
        # a candidate (its run has not passed as a master build) is walked again, never reused
        again = self.gate(self.world('b'))
        self.assertEqual((again['pass_cache']['reused'], again['pass_cache']['unchecked_candidates']), (0, 1))
        self.assertEqual(self.promote(again)['marked'], 1)
        reused = self.gate(self.world('c'))
        self.assertEqual((reused['pass_cache']['reused'], reused['pass_cache']['walked']), (1, 0))
        self.assertEqual(reused['tested'], first['tested'])
        how = list(reused['pass_cache']['frames'].values())[0]
        self.assertTrue(how.startswith('reused from 2026_10_10_v0.0.36-dev3_full_abc1234 (0.0.36-dev3, abc1234, '), how)
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '1'
        sampled = self.gate(self.world('c2'))
        self.assertTrue(list(sampled['pass_cache']['frames'].values())[0].startswith('walked again: reused from '))
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '0'
        # promoting the same run again marks nothing new
        self.assertEqual(self.promote(again)['already'], 1)
        changed = self.gate(self.world('d', heights_of=lambda x, y: 3.0 + 0.01 * x))
        self.assertEqual((changed['pass_cache']['reused'], changed['pass_cache']['walked']), (0, 1))

    def test_a_damaged_record_is_not_reused(self):
        self.promote(self.gate(self.world('a')))
        for path in (Path(self.tmp.name) / 'cache' / 'stair-walk').rglob('*.json'):
            meta = json.loads(path.read_text(encoding='utf-8'))
            meta['row']['rows'].append({'kind': 'step', 'result': 'passed', 'map': 'tampered', 'ref': 0})
            path.write_text(json.dumps(meta), encoding='utf-8', newline='\n')
        report = self.gate(self.world('b'))
        self.assertEqual((report['pass_cache']['reused'], report['pass_cache']['walked']), (0, 1))

    def test_a_sampled_frame_that_differs_from_its_checked_record_stops_the_gate(self):
        import stair_records
        self.promote(self.gate(self.world('a')))
        cache = Path(self.tmp.name) / 'cache'
        for path in (cache / 'stair-walk').rglob('*.json'):
            # a record and its mark both intact but holding other rows: what a key missing an input looks like
            meta = json.loads(path.read_text(encoding='utf-8'))
            record = meta['row']['record']
            meta['row']['rows'] = meta['row']['rows'] + [{'kind': 'step', 'result': 'passed', 'map': 'other', 'ref': 0}]
            record['rows_sha256'] = stair_records.sha256_of(meta['row']['rows'])
            record.pop('record_sha256')
            record['record_sha256'] = stair_records.sha256_of(record)
            if 'provenance' in meta:
                # consistent all through: its provenance names the new rows too (CACHE-NO-PROVENANCE-36)
                import cache_provenance
                meta['provenance']['output_sha256'] = cache_provenance.sha256_of(meta['row'])
            path.write_text(json.dumps(meta), encoding='utf-8', newline='\n')
            mark_path = stair_records.mark_path(cache, record['key'])
            mark = json.loads(mark_path.read_text(encoding='utf-8'))
            mark['record_sha256'] = record['record_sha256']
            mark.pop('mark_sha256')
            mark['mark_sha256'] = stair_records.sha256_of(mark)
            mark_path.write_text(json.dumps(mark), encoding='utf-8', newline='\n')
        os.environ['AMIWIND_STAIR_WALK_SAMPLE'] = '2'
        with self.assertRaises(ValueError) as caught:
            self.gate(self.world('b'))
        self.assertIn('walked again differs', str(caught.exception))

    def test_full_walks_every_frame(self):
        self.promote(self.gate(self.world('a')))
        os.environ['AMIWIND_STAIR_WALK_CACHE'] = 'full'
        report = self.gate(self.world('b'))
        self.assertEqual((report['pass_cache']['mode'], report['pass_cache']['reused']), ('full', 0))

    def test_both_gate_orders_are_offered(self):
        # v0.0.42 (B15): the stair gate first by default; the earlier order (heap gate and zone walk before the stair
        # walk, BUILD-CHIM-HEAP-GATE-LATE-36) stays selectable. The run order itself: tests/test_chim_stair_area.py
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        self.assertIn("choices=('stairs-first', 'stairs-last'), default='stairs-first'", text)

    def test_the_builder_sets_the_variables_the_walk_reads(self):
        import stair_walk
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("WALK_CACHE_ENV, WALK_SAMPLE_ENV, WALK_SAMPLE_DEFAULT = %r, %r, %d"
                      % (stair_walk.WALK_CACHE_ENV, stair_walk.WALK_SAMPLE_ENV, stair_walk.WALK_SAMPLE_DEFAULT), text)

    def test_the_walk_settings_never_key_a_stage(self):
        from build_cache import IGNORED_ENV
        self.assertTrue({'AMIWIND_STAIR_WALK_CACHE', 'AMIWIND_STAIR_WALK_SAMPLE'} <= IGNORED_ENV)


class RegionFramesSideBySideTests(unittest.TestCase):
    """BUILD-CHIM-STAGE-IDLE-START-36: generated areas (CHIM region frames) are prepared side by side."""

    def run_world(self, failing=None):
        from unittest import mock
        import chim.build as B
        seen = []

        def fake_task(task):
            town = task[0]
            seen.append(town)
            spec = {'frame': {'cell': (0, 0)}, 'terrain': {}}
            early = ['frame of %s: bad' % town] if town == failing else []
            return (spec, {'town': town}, {}, 1), early, [{'section': 'x', 'seconds': 1.0, 'cpu_seconds': 1.0}],                 {'terrain': {'built': 2, 'reused': 1}}, None

        def serial(function, items, jobs=None, **kw):
            return map(function, items)
        cache = B.UnitCache(None)
        timer = B.Timer()
        generated = {t: {'town': {'id': t}} for t in ('rcp1_p1', 'rcp2_p1', 'rcp3_p1')}
        with mock.patch.object(B, '_prepare_area_task', fake_task), mock.patch('build_parallel.ordered_map', serial):
            result = B.prepare_areas_parallel(list(generated), generated, None, Path(self.tmp.name), b'', None, 4,
                                              cache, timer, None, (), True, set(), None)
        return result, seen, cache, timer

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_frame_prepared_in_area_order_with_counts_merged(self):
        result, seen, cache, timer = self.run_world()
        self.assertEqual(list(result), ['rcp1_p1', 'rcp2_p1', 'rcp3_p1'])
        self.assertEqual(cache.stats['terrain'], {'built': 6, 'reused': 3})
        self.assertTrue(any(s['section'] == 'x (rcp2_p1)' for s in timer.sections))

    def test_a_failing_frame_stops_the_stage_named(self):
        with self.assertRaises(ValueError) as caught:
            self.run_world(failing='rcp2_p1')
        self.assertIn('rcp2_p1', str(caught.exception))

    def test_build_world_sends_region_frames_side_by_side(self):
        text = (ROOT / 'tools/chim/build.py').read_text(encoding='utf-8')
        self.assertIn('prepare_areas_parallel(towns + regional', text)


class AdoptEarlierFormTests(unittest.TestCase):
    """stair_records.adopt: a passed master build's walks in the cache's earlier form (rows only) become checked
    records without walking them again, when today's code computes the same input key and a sample walked again
    gives the same rows."""
    RUN = '2026_10_10_v0.0.36-dev3_full-coast_3b5e7a9'
    OLD_WALKER = 'f' * 64

    world, gate = StairCacheTests.world, StairCacheTests.gate

    def setUp(self):
        StairCacheTests.setUp(self)
        import stair_records
        real = stair_records.walker_sources
        self.old_root = Path(self.tmp.name) / 'old-source'
        self.patch = patch.object(stair_records, 'walker_sources', side_effect=lambda root, script: (
            (self.OLD_WALKER, {'tools/chim/collision.py': 'old'}) if Path(root) == self.old_root else real(root, script)))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        StairCacheTests.tearDown(self)

    def run_folder(self, status='passed', request='req-dev3', heights_of=None):
        """A run that walked its one frame with the earlier cache form: rows only, under the old walker's key."""
        from chim import collision
        from chim.validate import Failures, load_world
        from mesh_geometry_env import stair_mode
        from pass_cache import PassCache
        import stair_records
        run = Path(self.tmp.name) / 'ws' / 'build' / self.RUN
        out = run / 'chim-world'
        from test_chim_format import fixture
        fixture(out, **({'heights_of': heights_of} if heights_of else {}))
        report = self.gate(out)
        (out / 'chim-stairs.json').write_text(json.dumps(report), encoding='utf-8')
        # the earlier form: the same rows, no record, under the old walker's sources
        cache = Path(os.environ['AMIWIND_PASS_CACHE'])
        world = load_world(out, Failures())
        key = collision.frame_stair_key(world[5][0], world[4])
        options = {'stair_mode': stair_mode(), 'world': 'chim-frame', 'tile': collision.STAIR_TILE}
        # today's walk, stored under today's key form (the frame worker, chim.collision.stair_key_sources)
        rows = stair_records.lookup(PassCache('stair-walk', options, collision.stair_key_sources(), cache),
                                    key)[0]['rows']
        import shutil
        shutil.rmtree(cache)
        PassCache('stair-walk', options, self.OLD_WALKER, cache).store(key, {'rows': rows})
        (run / 'build-state.json').write_text(json.dumps({'status': 'passed'}), encoding='utf-8')
        result = run.parent / 'aw-result.json'
        result.write_text(json.dumps({'run_name': self.RUN, 'request_id': request, 'kind': 'build',
                                      'status': status, 'commit': '3b5e7a9', 'version': 'v0.0.36-dev3'}),
                          encoding='utf-8')
        return run, result, key, options

    def adopt(self, run, result, request='req-dev3'):
        import stair_records
        return stair_records.adopt(run, request, result, self.old_root, os.environ['AMIWIND_PASS_CACHE'], sample=1)

    def test_a_passed_runs_walks_are_adopted_and_reused_without_walking(self):
        run, result, _, _ = self.run_folder()
        before = self.gate(run / 'chim-world')                 # the earlier form is not reused as it is
        self.assertEqual(before['pass_cache']['reused'], 0)
        import shutil
        shutil.rmtree(Path(os.environ['AMIWIND_PASS_CACHE']))
        run, result, _, _ = self.run_folder()
        done = self.adopt(run, result)
        self.assertEqual((done['refused'], done['adopted']), (None, 1), done)
        self.assertEqual(done['parts']['chim frames']['walked_again'], list(before['pass_cache']['frames']))
        from chim import collision
        with patch.object(collision, 'stair_task', side_effect=AssertionError('walked again')):
            reused = self.gate(run / 'chim-world')
        self.assertEqual((reused['pass_cache']['reused'], reused['pass_cache']['walked']), (1, 0))
        how = list(reused['pass_cache']['frames'].values())[0]
        self.assertTrue(how.startswith('reused from %s (0.0.36-dev3, 3b5e7a9, ' % self.RUN), how)
        self.assertEqual(self.adopt(run, result)['already'], 1)

    def test_nothing_is_adopted_from_a_run_that_did_not_pass_as_a_master_build(self):
        for status, request, asked in (('failed', 'req-dev3', 'req-dev3'), ('passed', 'req-other', 'req-dev3')):
            run, result, key, options = self.run_folder(status=status, request=request)
            done = self.adopt(run, result, asked)
            self.assertIsNotNone(done['refused'])
            self.assertEqual(done['adopted'], 0)
            self.assertFalse((Path(os.environ['AMIWIND_PASS_CACHE']) / 'stair-walk-checked').exists())

    def test_rows_todays_walker_does_not_give_adopt_nothing(self):
        from pass_cache import PassCache
        run, result, key, options = self.run_folder()
        old = PassCache('stair-walk', options, self.OLD_WALKER, os.environ['AMIWIND_PASS_CACHE'])
        rows = old.load(key)[0]['rows']
        name = 'frames/x+00/y+00/frame.ccf'
        old.store(key, {'rows': rows + [{'map': name, 'kind': 'step', 'ref': 0, 'result': 'passed'}]})
        done = self.adopt(run, result)
        self.assertIn('differ', done['refused'] or '')
        self.assertEqual(done['adopted'], 0)

    def test_a_frame_whose_inputs_differ_is_not_adopted(self):
        run, result, key, options = self.run_folder()
        import shutil
        out = run / 'chim-world'
        shutil.rmtree(out)
        from test_chim_format import fixture
        fixture(out, heights_of=lambda x, y: 3.0 + 0.01 * x)  # the run's world now differs from what was walked
        (out / 'chim-stairs.json').write_text('{}', encoding='utf-8')
        done = self.adopt(run, result)
        self.assertEqual((done['refused'], done['adopted'], done['parts']['chim frames']['missing']), (None, 0, 1))

    def test_walker_sources_is_the_pass_cache_digest(self):
        import stair_records
        from chim import collision
        from pass_cache import source_digest
        self.patch.stop()
        try:
            root = Path(collision.__file__).resolve().parents[2]
            self.assertEqual(stair_records.walker_sources(root, 'tools/chim/collision.py')[0],
                             source_digest(collision.__file__))
        finally:
            self.patch.start()


if __name__ == '__main__':
    unittest.main()
