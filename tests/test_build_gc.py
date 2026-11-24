"""The one garbage collector: retention keys, pins, owners, dry run, hard-link-aware sizes, deletion."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_gc  # noqa: E402
import storage_pool  # noqa: E402

LINKS = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0
SIZE = 100_000


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.volume = Path(self.temp.name) / 'volume'
        self.workspace = self.volume / 'ws'
        (self.workspace / 'cache' / 'world-terrain-v1').mkdir(parents=True)
        self.registry = []

    def tearDown(self):
        for here, directories, names in os.walk(self.temp.name):
            for name in directories + names:
                os.chmod(Path(here) / name, 0o755)
        self.temp.cleanup()

    def run_folder(self, name, status='passed', version='0.0.33-dev1', started='2026-10-09T10:00:00Z',
                   recipe='full', payload=b'x', scratch=False):
        run = self.workspace / 'build' / name
        (run / 'image').mkdir(parents=True)
        state = {'status': status, 'runtime_version': version, 'builder': 'chim', 'recipe': recipe,
                 'build_started_at': started}
        (run / 'build-state.json').write_text(json.dumps(state))
        (run / 'image' / 'game.hdf').write_bytes(payload * SIZE)
        if scratch:
            (run / 'scratch').mkdir()
            (run / 'scratch' / 'tmp.bin').write_bytes(b's' * SIZE)
        return run

    def own(self, path, owner, state):
        self.registry.append({'path': str(path), 'owner': owner, 'purpose': 'test', 'state': state})

    def plan(self, **kwargs):
        kwargs.setdefault('jobs', 1)
        with contextlib.redirect_stdout(io.StringIO()):
            return build_gc.plan([self.volume], registry_items=self.registry, **kwargs)

    def decisions(self, result):
        return {Path(row['path']).name: (row['decision'], row['reason']) for row in result['items']}


class CollectorTest(Base):
    def test_retention_keys(self):
        old = self.run_folder('old', started='2026-10-09T08:00:00Z', scratch=True)
        self.run_folder('new', started='2026-10-09T09:00:00Z')
        self.run_folder('mw', started='2026-10-09T07:00:00Z', recipe='miniwind')
        failed = self.run_folder('failed', status='failed', started='2026-10-09T11:00:00Z')
        self.run_folder('stray', status='failed', started='2026-10-09T06:00:00Z')
        self.run_folder('live', status='running')
        (self.volume / 'smoke-copy').mkdir()
        (self.volume / 'smoke-copy' / 'played.hdf').write_bytes(b'p' * SIZE)
        (self.volume / 'nobody').mkdir()
        self.own(old, 'job-a', 'done')
        self.own(failed, 'job-b', 'active')
        self.own(self.volume / 'smoke-copy', 'job-a', 'done')
        got = self.decisions(self.plan())
        self.assertEqual(got['new'][0], 'keep')                     # newest passed of its line: reuse source
        self.assertIn('latest passed run', got['new'][1])
        self.assertEqual(got['mw'][0], 'keep')                      # another line (MiniWind recipe) keeps its own
        self.assertEqual(got['old'][0], 'expire')                   # superseded, owner done
        self.assertEqual(got['scratch'][0], 'expire')               # scratch left in a finished run
        self.assertEqual(got['failed'][0], 'keep')                  # maintainer still active
        self.assertEqual(got['stray'][0], 'unregistered')           # nobody owns it: reported, never deleted
        self.assertEqual(got['live'], ('keep', 'still building'))
        self.assertEqual(got['smoke-copy'][0], 'expire')
        self.assertEqual(got['nobody'][0], 'unregistered')
        self.assertEqual(got['world-terrain-v1'][0], 'keep')

    def test_runs_of_older_release_series_expire(self):
        # BUILD-CACHE-NO-RETENTION-55: the newest passed run of an old line was kept forever as a "reuse source".
        for name, version, started in (('v51', '0.0.51', '2026-10-01T08:00:00Z'),
                                       ('v52', '0.0.52-rc1', '2026-10-02T08:00:00Z'),
                                       ('v53', '0.0.53', '2026-10-03T08:00:00Z'),
                                       ('v54', '0.0.54-dev2', '2026-10-04T08:00:00Z'),
                                       ('v55', '0.0.55-dev1', '2026-10-05T08:00:00Z'),
                                       ('v52live', '0.0.52-dev1', '2026-10-02T09:00:00Z')):
            self.run_folder(name, version=version, started=started, status='running' if name == 'v52live' else 'passed')
        build_gc.edit_pin(self.workspace, 'build/v51', 'release', 'v0.0.51 release reference')
        got = self.decisions(self.plan())
        self.assertEqual(got['v52'][0], 'expire')
        self.assertIn('release series v0.0.52 is older than the kept series (v0.0.53, v0.0.54, v0.0.55)', got['v52'][1])
        for kept in ('v53', 'v54', 'v55'):
            self.assertEqual(got[kept][0], 'keep')                  # the newest three series: the usual rules
        self.assertIn('pinned (release)', got['v51'][1])            # a pin wins over age
        self.assertEqual(got['v52live'], ('keep', 'still building'))
        self.assertEqual(self.decisions(self.plan(keep_series=0))['v52'][0], 'keep')  # 0 = the rule off
        self.assertEqual(build_gc.series('v0.0.55-rc2'), (0, 0, 55))
        self.assertIsNone(build_gc.series('unknown'))

    def test_pins_win_over_everything(self):
        old = self.run_folder('rc1', version='0.0.33-rc1', started='2026-10-09T08:00:00Z')
        self.run_folder('rc1b', version='0.0.33-rc1', started='2026-10-09T09:00:00Z')
        self.own(old, 'job-a', 'done')
        self.assertEqual(self.decisions(self.plan())['rc1'][0], 'expire')
        build_gc.edit_pin(self.workspace, 'build/rc1', 'rc', 'release candidate reference')
        decision, reason = self.decisions(self.plan())['rc1']
        self.assertEqual(decision, 'keep')
        self.assertIn('pinned (rc)', reason)
        build_gc.edit_pin(self.workspace, old, remove=True)
        self.assertEqual(self.decisions(self.plan())['rc1'][0], 'expire')
        with self.assertRaises(ValueError):
            build_gc.edit_pin(self.workspace, 'build/rc1', 'favourite')

    def test_dry_run_deletes_nothing_and_delete_only_expired_listed_items(self):
        old = self.run_folder('old', started='2026-10-09T08:00:00Z')
        other = self.run_folder('other', started='2026-10-09T08:30:00Z')
        self.run_folder('new', started='2026-10-09T09:00:00Z')
        stray = self.run_folder('stray', started='2026-10-09T07:00:00Z')
        self.own(old, 'job-a', 'done')
        self.own(other, 'job-a', 'done')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(build_gc.main(['plan', str(self.volume), '--json', str(self.volume.parent / 'p.json')]), 0)
        self.assertTrue(old.exists() and stray.exists())
        self.assertIn('dry run', output.getvalue())
        result = self.plan()
        with contextlib.redirect_stdout(io.StringIO()):
            deleted = build_gc.delete(result, only=[old, stray])
        self.assertEqual(deleted, [str(old)])                       # stray is unregistered: never deleted
        self.assertFalse(old.exists())
        self.assertTrue(other.exists() and stray.exists())
        with contextlib.redirect_stdout(io.StringIO()):
            build_gc.delete(self.plan())
        self.assertFalse(other.exists())
        self.assertTrue((self.workspace / 'build' / 'new').exists())

    def test_items_file_deletes_exactly_its_listed_expired_items(self):
        # a long approved list (2026-10-29: 262 301 pool objects archived first) in a file, one path per line
        old = self.run_folder('old', started='2026-10-09T08:00:00Z')
        other = self.run_folder('other', started='2026-10-09T08:30:00Z')
        self.run_folder('new', started='2026-10-09T09:00:00Z')
        self.own(old, 'job-a', 'done')
        self.own(other, 'job-a', 'done')
        listing = self.volume.parent / 'items.txt'
        listing.write_text('%s\r\n\n' % old, encoding='utf-8')
        registry = self.volume.parent / 'registry.json'
        registry.write_text(json.dumps({'items': self.registry}), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_gc.main(['plan', str(self.volume), '--registry', str(registry), '--delete',
                                            '--items-file', str(listing)]), 0)
        self.assertFalse(old.exists())
        self.assertTrue(other.exists())
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            build_gc.main(['plan', str(self.volume), '--items-file', str(listing)])     # never without --delete

    def test_running_state_is_rechecked_before_deleting(self):
        old = self.run_folder('old', started='2026-10-09T08:00:00Z')
        self.run_folder('new', started='2026-10-09T09:00:00Z')
        self.own(old, 'job-a', 'done')
        result = self.plan()
        (old / 'build-state.json').write_text(json.dumps({'status': 'running'}))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_gc.delete(result), [])
        self.assertTrue(old.exists())

    def test_stale_running_run_is_not_kept_forever(self):
        stale = self.run_folder('stale', status='running')
        self.own(stale, 'job-a', 'done')
        later = time.time() + build_gc.STALE_RUNNING_SECONDS + 60
        self.assertEqual(self.decisions(self.plan(now_seconds=later))['stale'][0], 'expire')

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_sizes_count_hard_linked_bytes_only_when_every_link_goes(self):
        old = self.run_folder('old', started='2026-10-09T08:00:00Z')
        new = self.run_folder('new', started='2026-10-09T09:00:00Z')
        pool = self.workspace / build_gc.POOL
        for run in (old, new):
            storage_pool.put(pool, run / 'image' / 'game.hdf')
        self.own(old, 'job-a', 'done')
        result = self.plan()
        rows = {Path(row['path']).name: row for row in result['items']}
        state = len((old / 'build-state.json').read_bytes())
        self.assertEqual(rows['old']['bytes'], SIZE + state)
        self.assertEqual(rows['old']['freed_alone'], state)         # the pool and the newer run still link the image
        self.assertEqual(result['totals']['expire']['freed'], state)
        self.assertNotIn('pool-object', {row['kind'] for row in result['items']})
        # Once no run links an object and no reuse key names it, the object itself expires.
        os.chmod(new / 'image', 0o755)
        for run in (old, new):
            (run / 'image' / 'game.hdf').unlink()
        result = self.plan()
        orphans = [row for row in result['items'] if row['kind'] == 'pool-object']
        self.assertEqual(len(orphans), 1)
        self.assertEqual(result['totals']['expire']['freed'], SIZE + state)
        # ... unless a reuse key of the asset pool still names it (a converter cache entry).
        digest = Path(orphans[0]['path']).name
        key = pool / 'keys' / 'media' / 'ab' / 'ab.json'
        key.parent.mkdir(parents=True)
        key.write_text(json.dumps({'sha256': digest}))
        self.assertFalse([row for row in self.plan()['items'] if row['kind'] == 'pool-object'])


NOW = time.time()
DAY = 86400
OLD = NOW - 30 * DAY


def stamp(seconds):
    return build_gc.datetime.fromtimestamp(seconds, build_gc.timezone.utc).isoformat(timespec='seconds')


def key(n):
    return hashlib.sha256(str(n).encode()).hexdigest()


class UnitAgeingTest(Base):
    """BUILD-CACHE-NO-RETENTION-55: the unit caches age by their use logs; the plan reports the pool's needs, the retire
    order and the use-log trim. Every case here failed before: the collector kept every cache whole."""

    def setUp(self):
        super().setUp()
        self.kept = self.run_folder('2026_11_20_v0.0.33-dev1_full_aaaaaaa', started=stamp(NOW - 2 * DAY))
        self.origin = time.strftime('%Y_%m_%d', time.gmtime(OLD)) + '_v0.0.33-dev1_full_bbbbbbb'   # retired
        ran = self.kept / 'profile' / 'manifests-ran'
        ran.mkdir(parents=True)
        (ran / 'chim.json').write_text(json.dumps({'provenance': {'run': self.origin, 'created_at': stamp(OLD + 3600)}}))
        self.cache = self.workspace / 'cache'
        self.lines = []

    def use(self, cache, entry, at, run):
        self.lines.append((cache, json.dumps({'at': stamp(at), 'cache': 'x', 'job': None, 'key': entry, 'run': run},
                                             sort_keys=True, separators=(',', ':'))))

    def write_logs(self):
        for cache in {c for c, _ in self.lines} | {'chim-units'}:
            log = self.cache / cache / '.provenance' / 'reuse.jsonl'
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(''.join(line + '\n' for c, line in self.lines if c == cache), encoding='utf-8')

    def unit(self, kind, entry, written, writer='someone', data=b'u'):
        folder = self.cache / 'chim-units' / kind / entry[:2]
        folder.mkdir(parents=True, exist_ok=True)
        pickle, meta = folder / (entry + '.pickle'), folder / (entry + '.meta.json')
        pickle.write_bytes(data * 1000)
        meta.write_text(json.dumps({'schema': 'aw-cache-provenance-1', 'run': writer, 'key': entry}))
        for path in (pickle, meta):
            os.utime(path, (written, written))
        return pickle, meta

    def rows(self, result, kind):
        return {Path(row['path']).name: row for row in result['items'] if row['kind'] == kind}

    def test_old_unused_entries_expire_and_named_or_recent_ones_stay(self):
        gone = self.unit('mesh', key(1), OLD - 10 * DAY)                       # old, nobody used it: expires
        self.unit('mesh', key(2), OLD - 10 * DAY)
        self.use('chim-units', key(2), OLD - 5 * DAY, self.kept.name)            # a kept run used it: stays
        self.unit('mesh', key(3), OLD - 10 * DAY)
        self.use('chim-units', key(3), NOW - DAY, 'some-test-run')               # used within the grace: stays
        self.unit('mesh', key(4), NOW - DAY)                                     # written within the grace: stays
        self.unit('mesh', key(5), OLD + 1800, writer=self.origin)                # the kept run's stage came from it
        other = self.unit('mesh', key(6), OLD + 1800, writer='a-run-nobody-keeps')
        self.use('chim-units', key(6), OLD + 1800, 'a-run-nobody-keeps')         # old line of no named run: trimmed
        heap = self.cache / 'chim-units' / 'heap' / 'ab'
        heap.mkdir(parents=True)
        (heap / 'frame.json').write_bytes(b'h' * 500)                            # not recorded: kept whole
        os.utime(heap / 'frame.json', (OLD, OLD))
        for n in range(100, 112):
            self.unit('mesh', key(n), NOW - DAY)                                 # more shards: a worker pool's share
        self.write_logs()
        result = self.plan(now_seconds=NOW)
        row = self.rows(result, 'unit-entries')['mesh']
        self.assertEqual(row['decision'], 'expire')
        self.assertEqual(row['expired_entries'], 2)
        self.assertEqual(sorted(Path(p).name for p in row['members']),
                         sorted(p.name for p in gone + other))
        self.assertEqual(row['freed_alone'], sum(p.stat().st_size for p in gone + other))
        self.assertEqual(self.rows(result, 'cache')['chim-units']['decision'], 'keep')
        self.assertFalse([p for r in result['items'] for p in r.get('members') or () if os.sep + 'heap' + os.sep in p])
        self.assertIn(self.origin, result['named_runs'])
        trim = [log for log in result['log_trim'] if 'chim-units' in log['path']][0]
        self.assertEqual((trim['lines'], trim['expiring_lines']), (3, 1))
        # the same plan on worker processes
        parallel = self.rows(self.plan(now_seconds=NOW, jobs=4), 'unit-entries')['mesh']
        self.assertEqual(sorted(parallel['members']), sorted(row['members']))
        # grace 0: no ageing, the cache kept whole as before
        self.assertFalse(self.rows(self.plan(now_seconds=NOW, grace_days=0), 'unit-entries'))
        # --delete with one listed entry file removes exactly that file
        with contextlib.redirect_stdout(io.StringIO()):
            deleted = build_gc.delete(result, only=[gone[0]])
        self.assertEqual(deleted, [str(gone[0])])
        self.assertFalse(gone[0].exists())
        self.assertTrue(gone[1].exists() and other[0].exists())

    def test_caches_whose_use_is_not_recorded_stay(self):
        self.unit('mesh', key(1), OLD)                                         # chim-units without a use log
        gallery = self.cache / 'npc-gallery-v1' / 'ab' / key(7)
        gallery.mkdir(parents=True)
        (gallery / 'model.mdl').write_bytes(b'g' * 100)
        os.utime(gallery / 'model.mdl', (OLD, OLD))
        result = self.plan(now_seconds=NOW)
        self.assertFalse(self.rows(result, 'unit-entries'))
        caches = self.rows(result, 'cache')
        self.assertIn('no use log', caches['chim-units']['reason'])
        self.assertEqual(caches['npc-gallery-v1']['decision'], 'keep')

    def test_shared_files_go_only_with_every_entry_that_names_them(self):
        self.write_logs()
        passes = self.cache / 'image-passes'
        blobs = {name: '%064x' % (100 + n) for n, name in enumerate('abc')}

        def entry(sub, k, written, files=None):
            path = passes / sub / k[:2] / (k + '.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            row = {'row': {}, 'files': files} if files is not None else {}
            path.write_text(json.dumps({'format': 'x', 'row': row}))
            os.utime(path, (written, written))
            return path

        entry('player-parts', key(11), NOW - DAY, {'a': blobs['a'], 'b': blobs['b']})
        # (ten days before the retired origin ran: an entry written while it ran, with no writer recorded, is kept)
        old = entry('player-parts', key(12), OLD - 10 * DAY, {'b': blobs['b'], 'c': blobs['c']})
        entry('player-parts', key(15), OLD + 1800, {})                         # while the origin ran: kept
        for sha in blobs.values():
            blob = passes / 'player-parts' / 'files' / sha[:2] / (sha + '.bin')
            blob.parent.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(b'b' * 10)
            os.utime(blob, (OLD, OLD))
        entry('stair-walk', key(13), OLD)                                       # the walk records: never aged
        entry('odd-sub', key(14), OLD)
        (passes / 'odd-sub' / 'ab').mkdir(parents=True)
        (passes / 'odd-sub' / 'ab' / 'notes.txt').write_text('?')               # outside the form: kept whole
        (passes / '.provenance').mkdir()
        (passes / '.provenance' / 'reuse.jsonl').write_text('')
        row = self.rows(self.plan(now_seconds=NOW), 'unit-entries')['player-parts']
        self.assertEqual(sorted(Path(p).name for p in row['members']), sorted([old.name, blobs['c'] + '.bin']))
        self.assertEqual((row['expired_entries'], row['expired_blobs']), (1, 1))
        self.assertNotIn('stair-walk', self.rows(self.plan(now_seconds=NOW), 'unit-entries'))
        self.assertNotIn('odd-sub', self.rows(self.plan(now_seconds=NOW), 'unit-entries'))

    def test_expired_reuse_keys_take_their_objects_and_unrecorded_namespaces_stay(self):
        pool = self.workspace / build_gc.POOL
        names = {}
        for namespace, n in (('sound', 21), ('chim-unit', 22)):
            sha = '%064x' % (200 + n)
            obj = pool / 'objects' / sha[:2] / sha
            obj.parent.mkdir(parents=True, exist_ok=True)
            obj.write_bytes(b'o' * 50)
            k = pool / 'keys' / namespace / key(n)[:2] / (key(n) + '.json')
            k.parent.mkdir(parents=True, exist_ok=True)
            k.write_text(json.dumps({'sha256': sha, 'key': key(n)}))
            os.utime(k, (OLD - 10 * DAY, OLD - 10 * DAY))
            names[namespace] = sha
        objects = self.rows(self.plan(now_seconds=NOW), 'pool-object')
        self.assertFalse(objects)                                               # no use log: no key ages
        (pool / '.provenance').mkdir()
        (pool / '.provenance' / 'reuse.jsonl').write_text('')
        result = self.plan(now_seconds=NOW)
        keys = self.rows(result, 'reuse-keys')
        self.assertEqual(list(keys), ['sound'])
        self.assertEqual(keys['sound']['expired_entries'], 1)
        objects = self.rows(result, 'pool-object')
        self.assertEqual(list(objects), [names['sound']])
        self.assertIn('only expired reuse keys', objects[names['sound']]['reason'])

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_pool_needs_retire_order_and_hard_linked_unit_entries(self):
        self.write_logs()
        old = self.run_folder('2026_10_01_v0.0.30-dev1_full_ccccccc', version='0.0.30-dev1', payload=b'o')
        stray = self.run_folder('2026_10_02_v0.0.33-dev1_full_ddddddd', status='failed', payload=b's')
        pool = self.workspace / build_gc.POOL
        for run in (old, stray, self.kept):
            storage_pool.put(pool, run / 'image' / 'game.hdf')
        pickle, meta = self.unit('mesh', key(31), OLD)
        os.link(pickle, self.kept / 'unit.pickle')                              # a kept run still links it
        result = self.plan(now_seconds=NOW, keep_series=1)                     # v0.0.30 is an older series
        row = self.rows(result, 'unit-entries')['mesh']
        self.assertEqual(row['freed_alone'], meta.stat().st_size)               # the pickle is not freed
        objects = self.rows(result, 'pool-object')
        self.assertEqual(len(objects), 1)                                       # the old run's image, same plan
        self.assertIn('only expiring items link', list(objects.values())[0]['reason'])
        state = len((old / 'build-state.json').read_bytes())
        self.assertEqual(self.rows(result, 'run')[old.name]['freed_alone'], state)
        accounting = result['pools'][0]
        self.assertEqual(accounting['bytes'], 3 * SIZE)
        self.assertEqual(accounting['kept_needs_bytes'], SIZE)
        self.assertEqual(accounting['expiring_bytes'], SIZE)
        self.assertEqual(accounting['held_by_others_bytes'], SIZE)
        order = result['retire_order']
        self.assertEqual([Path(r['path']).name for r in order], [old.name, stray.name])
        stray_state = len((stray / 'build-state.json').read_bytes())
        self.assertEqual(order[-1]['cumulative_freed'], 2 * SIZE + state + stray_state)

    def test_run_folders_walked_on_worker_processes_give_the_same_plan(self):
        # GC-RUN-WALK-ONE-CORE-68: the run folders were walked one after another on one core
        for n in range(9):
            self.run_folder('2026_11_0%d_v0.0.33-dev1_full_%07d' % (n % 9 + 1, n), started=stamp(NOW - (20 - n) * DAY))
        self.write_logs()
        rows = lambda result: sorted((r['path'], r['decision'], r['bytes'], r['freed_alone']) for r in result['items'])
        self.assertEqual(rows(self.plan(now_seconds=NOW, jobs=1)), rows(self.plan(now_seconds=NOW, jobs=4)))

    def test_json_names_every_expired_path_beside_the_plan(self):
        gone = self.unit('mesh', key(41), OLD - 10 * DAY)
        self.write_logs()
        plan_file = self.volume.parent / '2026_11_23_v0.0.68_gc_plan.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_gc.main(['plan', str(self.volume), '--json', str(plan_file), '--jobs', '1']), 0)
        data = json.loads(plan_file.read_text(encoding='utf-8'))
        listing = Path(data['expired_paths_file'])
        self.assertEqual(listing.name, '2026_11_23_v0.0.68_gc_plan.expired-paths.txt')
        self.assertTrue({str(p) for p in gone} <= set(listing.read_text(encoding='utf-8').splitlines()))
        self.assertFalse(any('members' in row for row in data['items']))
        self.assertTrue(all(p.exists() for p in gone))                          # a dry run
        self.assertIn('retire_order', data)
        self.assertIn('log_trim', data)


if __name__ == '__main__':
    unittest.main()
