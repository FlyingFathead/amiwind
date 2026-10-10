"""Work pool: leases with owner, purpose, quota and expiry; admission by capacity; quota from unique bytes;
over-quota leases paused one by one; returned and expired leases collected by the garbage collector."""
import contextlib
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_gc  # noqa: E402
import storage_pool  # noqa: E402
import work_pool  # noqa: E402
from work_pool import GB, WorkPool  # noqa: E402

LINKS = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0
KB = 1000


class WorkPoolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'workpool'
        self.pool = WorkPool(self.root)
        self.pool.init(100 * KB, 10 * KB)
        self.later = work_pool.now() + timedelta(hours=2)

    def tearDown(self):
        for here, directories, names in os.walk(self.temp.name):
            for name in directories + names:
                os.chmod(Path(here) / name, 0o755)
        self.temp.cleanup()

    def test_lease_records_owner_purpose_quota_expiry(self):
        lease = self.pool.lease('job-a', 'MiniWind sandbox', 40 * KB, self.later, container='box-a')
        self.assertTrue(Path(lease['path']).is_dir())
        stored = json.loads((self.root / 'leases' / f"{lease['id']}.json").read_text())
        self.assertEqual((stored['owner'], stored['purpose'], stored['quota_bytes'], stored['state']),
                         ('job-a', 'MiniWind sandbox', 40 * KB, 'active'))
        with self.assertRaises(ValueError):
            self.pool.lease('', 'x', KB, self.later)
        with self.assertRaises(ValueError):
            self.pool.lease('job', 'x', 0, self.later)

    def test_admission_keeps_quotas_within_capacity_minus_reserve(self):
        first = self.pool.lease('job-a', 'build', 50 * KB, self.later)
        with self.assertRaises(ValueError) as refused:
            self.pool.lease('job-b', 'build', 41 * KB, self.later)  # 50 + 41 > 100 - 10
        self.assertIn('wait for a lease', str(refused.exception))
        self.pool.lease('job-b', 'build', 40 * KB, self.later)
        self.pool.give_back(first['id'])
        self.pool.lease('job-c', 'build', 50 * KB, self.later)  # a returned lease frees its quota

    def test_expired_leases_free_their_quota(self):
        self.pool.lease('job-a', 'build', 90 * KB, work_pool.now() - timedelta(seconds=1))
        self.assertEqual([lease['state'] for lease in self.pool.leases()], ['expired'])
        self.pool.lease('job-b', 'build', 90 * KB, self.later)

    def test_over_quota_pauses_only_that_job(self):
        small = self.pool.lease('job-a', 'build', 10 * KB, self.later, container='box-a')
        big = self.pool.lease('job-b', 'build', 50 * KB, self.later, container='box-b')
        (Path(small['path']) / 'out.bin').write_bytes(b'x' * 20 * KB)
        (Path(big['path']) / 'out.bin').write_bytes(b'x' * 20 * KB)
        calls = []
        over = self.pool.enforce('pause {container} {owner}', run=lambda command, **_: calls.append(command))
        self.assertEqual([row['id'] for row in over], [small['id']])
        self.assertEqual(calls, ['pause box-a job-a'])
        self.assertEqual(self.pool.get(small['id'])['state'], 'over-quota')
        self.assertEqual(self.pool.get(big['id'])['state'], 'active')
        self.pool.enforce('pause {container}', run=lambda command, **_: calls.append(command))
        self.assertEqual(len(calls), 1)  # paused once, not on every check
        (Path(small['path']) / 'out.bin').unlink()
        self.pool.enforce()
        self.assertEqual(self.pool.get(small['id'])['state'], 'active')

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_bytes_linked_from_the_content_pool_are_free(self):
        content = Path(self.temp.name) / 'cache' / 'asset-pool-v1'
        source = Path(self.temp.name) / 'input.bin'
        source.write_bytes(b'i' * 50 * KB)
        _, digest, _ = storage_pool.put(content, source)
        lease = self.pool.lease('job-a', 'build', 10 * KB, self.later)
        target = self.pool.link(lease['id'], content, digest, 'inputs/input.bin')
        self.assertEqual(os.stat(target).st_ino, os.stat(source).st_ino)
        self.assertEqual(self.pool.used(lease), 0)
        self.assertEqual(self.pool.enforce(), [])
        with self.assertRaises(ValueError):
            self.pool.link(lease['id'], content, digest, '../escape.bin')

    def test_returned_and_expired_leases_are_collected(self):
        done = self.pool.lease('job-a', 'build', 10 * KB, self.later)
        live = self.pool.lease('job-b', 'build', 10 * KB, self.later)
        (Path(done['path']) / 'out.bin').write_bytes(b'x' * KB)
        self.pool.give_back(done['id'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            build_gc.main(['plan', '--work-pool', str(self.root), '--json', str(self.root.parent / 'plan.json')])
        plan = json.loads((self.root.parent / 'plan.json').read_text())
        decisions = {Path(row['path']).name: row['decision'] for row in plan['items']}
        self.assertEqual(decisions[done['id']], 'expire')
        self.assertEqual(decisions[live['id']], 'keep')
        self.assertTrue(Path(done['path']).exists())  # dry run
        items = self.pool.registry_items()
        result = build_gc.plan([self.root / 'work'], registry_items=items)
        with contextlib.redirect_stdout(io.StringIO()):
            build_gc.delete(result)
        self.assertFalse(Path(done['path']).exists())
        self.assertTrue(Path(live['path']).exists())

    def test_cli(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(work_pool.main(['lease', str(self.root), '--owner', 'job-a', '--purpose', 'p',
                                             '--quota', str(20 * KB / GB), '--hours', '1']), 0)
            self.assertEqual(work_pool.main(['usage', str(self.root)]), 0)
        self.assertIn('job-a', output.getvalue())


if __name__ == '__main__':
    unittest.main()
