"""The one garbage collector: retention keys, pins, owners, dry run, hard-link-aware sizes, deletion."""
import contextlib
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


class CollectorTest(unittest.TestCase):
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
        return build_gc.plan([self.volume], registry_items=self.registry, **kwargs)

    def decisions(self, result):
        return {Path(row['path']).name: (row['decision'], row['reason']) for row in result['items']}

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
        self.assertEqual(got['failed'][0], 'keep')                  # owner still active
        self.assertEqual(got['stray'][0], 'unregistered')           # nobody owns it: reported, never deleted
        self.assertEqual(got['live'], ('keep', 'still building'))
        self.assertEqual(got['smoke-copy'][0], 'expire')
        self.assertEqual(got['nobody'][0], 'unregistered')
        self.assertEqual(got['world-terrain-v1'][0], 'keep')

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


if __name__ == '__main__':
    unittest.main()
