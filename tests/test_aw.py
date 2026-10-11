# SPDX-License-Identifier: GPL-3.0-only
"""The master builder's command line (tools/aw.py): schemas, lease register, gate judging, run names."""
import contextlib
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import aw  # noqa: E402

TS = '2026-10-10 14:30:00 +0300'

GREEN = {
    'repo': ['gate 7 repo /src/wt head abc1234 dirty 0', 'previous-release: ok (0.0.36-dev1)',
             'gate-queue: enabled=1 max=3 slot=1 waited_s=2 holders=1 cpus=8',
             'gate-times: queued_at=100 started_at=102'],
    'preflight': ['preflight-exit=0', 'Combined source preflight passed 2432'],
    'suite': ['suite-exit=0 image=gate node=v24', 'SKIP test_x.T.test_y | reason',
              '{"started": "a", "finished": "b", "seconds": 66.2, "tests_run": 3165, "failures": 0, "errors": 0, '
              '"skipped": 3, "unexpected_skips": 0, "successful": true}'],
    'hostparity': ['host-parity-linux-exit=0', 'host-parity-windows-exit=0'],
    'engine': ['engine-exit=0', '0', 'Target link/source binding passed'],
    'smoke': ['smoke-exit=0', 'PASS boot, seyda and balmora loaded, music reads 15 -> 26, off, on again (26 -> 44), 68 s'],
}


def write_gate(folder, number, files):
    for name, lines in files.items():
        Path(folder, f'par-{number}-{name}.out').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def config_in(base, **extra):
    base = Path(base)
    (base / 'gate').mkdir(exist_ok=True)
    config = {'schema': 'aw-config-1', 'state_dir': str(base / 'state'),
              'gate': {'out_dir': str(base / 'gate'), 'ranges': {'test': [10, 12]}, 'default_range': 'test'},
              'lock_stale_s': 300}
    config.update(extra)
    path = base / 'aw-config.json'
    path.write_text(json.dumps(config), encoding='utf-8')
    return path, aw.load_config(path)


class FakeGit:
    """Stands in for git (the gate images may have none): HEAD is abc1234, DIRTY lists uncommitted paths."""

    def __init__(self, head='abc1234'):
        self.head, self.dirty = head, ''

    def short(self, repo, rev='HEAD'):
        return self.head if rev in ('HEAD', self.head) else None

    def run(self, repo, *args):
        return self.dirty if args[:1] == ('status',) else None

    def patch(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(aw, 'git_short', self.short))
        stack.enter_context(mock.patch.object(aw, 'git', self.run))
        return stack


class SchemaTests(unittest.TestCase):
    def request(self, **change):
        doc = {'schema': 'aw-request-1', 'id': '2026_10_10_v0.0.36-dev1_gate-1530_abc1234', 'kind': 'gate',
               'repo': '/src/wt', 'commit': 'abc1234', 'purpose': 'gate-1530', 'version': 'v0.0.36-dev1',
               'reason': 'first use', 'requester': 'worker-a', 'time': TS, 'options': {}}
        doc.update(change)
        return doc

    def result(self, **change):
        doc = {'schema': 'aw-result-1', 'request_id': 'r1', 'kind': 'gate', 'status': 'passed',
               'version': 'v0.0.36-dev1', 'commit': 'abc1234',
               'run_name': '2026_10_10_v0.0.36-dev1_gate-1530-first-use_abc1234', 'time': TS, 'started': TS,
               'finished': TS, 'seconds': 70.5,
               'numbers': {'tests_run': 3165, 'failures': 0, 'errors': 0, 'skipped': 3, 'unexpected_skips': 0,
                           'engine_warnings': 0},
               'steps': {'suite': {'exit': 0, 'ok': True, 'detail': ''}}, 'failed_steps': [], 'failures': [],
               'artifacts': [], 'logs': [], 'timings': {}, 'reuse': {'applicable': False}, 'leases': ['gate-1']}
        doc.update(change)
        return doc

    def test_schema_files_are_json_with_their_ids(self):
        for name in ('aw-request-1', 'aw-result-1'):
            data = aw.schema(name)
            self.assertEqual(data['$id'], name)
            self.assertEqual(data['properties']['schema']['const'], name)

    def test_examples_validate(self):
        self.assertEqual(aw.validate(self.request(), aw.schema('aw-request-1')), [])
        self.assertEqual(aw.validate(self.result(), aw.schema('aw-result-1')), [])
        for kind in aw.KINDS:
            self.assertEqual(aw.validate(self.request(kind=kind), aw.schema('aw-request-1')), [], kind)

    def test_bad_documents_are_refused(self):
        req = aw.schema('aw-request-1')
        self.assertTrue(aw.validate(self.request(kind='deploy'), req))
        self.assertTrue(aw.validate(self.request(time='2026-10-10T14:30'), req))
        self.assertTrue(aw.validate(self.request(version='0.0.36'), req))
        self.assertTrue(aw.validate(self.request(extra=1), req))
        missing = self.request()
        del missing['reason']
        self.assertTrue(aw.validate(missing, req))
        res = aw.schema('aw-result-1')
        self.assertTrue(aw.validate(self.result(status='green'), res))
        self.assertTrue(aw.validate(self.result(run_name='final4b'), res))
        self.assertTrue(aw.validate(self.result(numbers={'tests_run': -1}), res))
        self.assertTrue(aw.validate(self.result(steps={'suite': {'exit': 0}}), res))

    def test_stamp_format(self):
        self.assertRegex(aw.stamp(), r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$')


class RunNameTests(unittest.TestCase):
    def test_format(self):
        day = datetime.date(2026, 10, 10)
        self.assertEqual(aw.make_run_name('0.0.36-dev1', 'gate-1530', 'abc1234def', 'First use!', day),
                         '2026_10_10_v0.0.36-dev1_gate-1530-first-use_abc1234')
        self.assertEqual(aw.make_run_name('v0.0.35', 'miniwind-animkit', '853d9b2', 'companion run', day, 2),
                         '2026_10_10_v0.0.35_miniwind-animkit-companion-run-try2_853d9b2')
        self.assertEqual(aw.make_run_name('0.0.36-dev1', 'full', None, None, day), '2026_10_10_v0.0.36-dev1_full_nogit')

    def test_a_long_reason_is_shortened_to_a_valid_request_id(self):
        # AW-RUN-NAME-LONG-REASON-36: gate 1981 was refused after leasing its number (id over 128 characters)
        day = datetime.date(2026, 10, 11)
        reason = 'chimport-x divided CHIM region cells (CHIM-REGION-DIVIDED-CELLS-36), retry of 1980 (MSYS path setup error)'
        for attempt in (1, 3):
            name = aw.make_run_name('0.0.36-dev5', 'gate-1981', '3aef4a5', reason, day, attempt)
            self.assertLessEqual(len(name), aw.RUN_NAME_MAX)
            self.assertRegex(name, r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
            self.assertTrue(name.startswith('2026_10_11_v0.0.36-dev5_gate-1981-chimport-x-divided'))
            self.assertTrue(name.endswith(('_3aef4a5' if attempt == 1 else '-try3_3aef4a5')))
            self.assertTrue(aw.RUN_NAME.fullmatch(name))

    def test_names_match_the_rule(self):
        self.assertTrue(aw.RUN_NAME.fullmatch('2026_10_10_v0.0.35-dev1_full_901f8e9'))
        for bad in ('final4b', 'rc1c', 'dev1-901f8e9', '2026_10_10_0.0.35_full_901f8e9', '2026_10_10_v0.0.35__901f8e9'):
            self.assertIsNone(aw.RUN_NAME.fullmatch(bad), bad)


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.path, self.config = config_in(self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def test_gate_numbers_are_never_reused(self):
        first = aw.lease_gate(self.config, 'a')
        self.assertEqual(first['key'], '10')
        aw.release(self.config, first['id'], 'a')
        second = aw.lease_gate(self.config, 'b')
        self.assertEqual(second['key'], '11', 'a released number stays spent')

    def test_numbers_with_outputs_are_skipped(self):
        Path(self.base, 'gate', 'par-10-repo.out').write_text('x', encoding='utf-8')
        Path(self.base, 'gate', 'suite-11').mkdir()
        self.assertEqual(aw.lease_gate(self.config, 'a')['key'], '12')

    def test_range_exhausted(self):
        for _ in range(3):
            aw.lease_gate(self.config, 'a')
        with self.assertRaisesRegex(aw.AwError, 'exhausted'):
            aw.lease_gate(self.config, 'a')

    def test_explicit_number_outside_range_or_taken(self):
        with self.assertRaisesRegex(aw.AwError, 'outside range'):
            aw.lease_gate(self.config, 'a', number=99)
        aw.lease_gate(self.config, 'a', number=11)
        with self.assertRaisesRegex(aw.AwError, 'not free'):
            aw.lease_gate(self.config, 'b', number=11)
        with self.assertRaisesRegex(aw.AwError, 'not in the config'):
            aw.lease_gate(self.config, 'a', range_name='nope')

    def test_concurrent_processes_get_distinct_numbers(self):
        _, config = config_in(self.base, gate={'out_dir': str(self.base / 'gate'),
                                               'ranges': {'test': [100, 139]}, 'default_range': 'test'})
        script = textwrap.dedent(f'''
            import sys
            sys.path.insert(0, {str(ROOT / "tools")!r})
            import aw
            config = aw.load_config({str(self.path)!r})
            for _ in range(4):
                print(aw.lease_gate(config, 'p')['key'])
        ''')
        procs = [subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, text=True)
                 for _ in range(6)]
        keys = []
        for proc in procs:
            out, _ = proc.communicate(timeout=120)
            self.assertEqual(proc.returncode, 0)
            keys += out.split()
        self.assertEqual(len(keys), 24)
        self.assertEqual(len(set(keys)), 24, 'two processes got the same gate number')
        state = aw.load_state(config)
        self.assertEqual(len(state['gate_spent']), 24)
        self.assertEqual(len({lease['id'] for lease in state['leases']}), 24)

    def test_stale_lock_is_broken_and_logged(self):
        lock = aw.state_dir(self.config) / 'aw-state.lock'
        lock.write_text('dead holder\n', encoding='utf-8')
        old = time.time() - 1000
        os.utime(lock, (old, old))
        self.assertEqual(aw.lease_gate(self.config, 'a')['key'], '10')
        self.assertFalse(lock.exists())
        events = [json.loads(line)['event'] for line in aw.trial_log_path(self.config).read_text().splitlines()]
        self.assertIn('stale-lock', events)

    def test_fresh_lock_blocks_until_timeout(self):
        lock = aw.state_dir(self.config) / 'aw-state.lock'
        lock.write_text('live holder\n', encoding='utf-8')
        with self.assertRaisesRegex(aw.AwError, 'live holder'):
            with aw.Lock(self.config, 'b', timeout=0.3):
                pass
        self.assertTrue(lock.exists())

    def test_worktree_lease_is_exclusive_and_renewable(self):
        lease = aw.lease_worktree(self.config, self.base / 'wt-a', 'job-a')
        self.assertEqual(aw.lease_worktree(self.config, self.base / 'wt-a', 'job-a')['id'], lease['id'])
        with self.assertRaisesRegex(aw.AwError, 'leased by job-a'):
            aw.lease_worktree(self.config, self.base / 'wt-a', 'job-b')
        before = lease['expires_epoch']
        time.sleep(0.01)
        self.assertGreater(aw.renew(self.config, lease['id'], 'job-a')['expires_epoch'], before)
        aw.release(self.config, lease['id'], 'job-a')
        self.assertEqual(aw.lease_worktree(self.config, self.base / 'wt-a', 'job-b')['requester'], 'job-b')
        with self.assertRaisesRegex(aw.AwError, 'released'):
            aw.renew(self.config, lease['id'])

    def test_expired_lease_frees_the_worktree(self):
        lease = aw.lease_worktree(self.config, self.base / 'wt-a', 'job-a')
        with aw.Lock(self.config):
            state = aw.load_state(self.config)
            state['leases'][0]['expires_epoch'] = time.time() - 1
            aw.save_state(self.config, state)
        self.assertEqual(aw.lease_worktree(self.config, self.base / 'wt-a', 'job-b')['requester'], 'job-b')
        statuses = {item['id']: item['status'] for item in aw.list_leases(self.config, everything=True)}
        self.assertEqual(statuses[lease['id']], 'expired')

    def test_run_names_get_try_suffixes(self):
        repo = self.base / 'repo'
        repo.mkdir()
        (repo / 'VERSION').write_text('0.0.36-dev1\n', encoding='utf-8')
        short = 'abc1234'
        with FakeGit(short).patch():
            names = [aw.lease_run_name(self.config, repo, 'smoke', 'a', 'check')['key'] for _ in range(3)]
        today = datetime.date.today().strftime('%Y_%m_%d')
        self.assertEqual(names, [f'{today}_v0.0.36-dev1_smoke-check_{short}',
                                 f'{today}_v0.0.36-dev1_smoke-check-try2_{short}',
                                 f'{today}_v0.0.36-dev1_smoke-check-try3_{short}'])


class GateParseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def parse(self, files, number=7, head='abc1234'):
        write_gate(self.dir, number, files)
        return aw.parse_gate(self.dir, number, head)

    def test_green_gate(self):
        result = self.parse(GREEN)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['numbers']['tests_run'], 3165)
        self.assertEqual(result['numbers']['engine_warnings'], 0)
        self.assertEqual(result['head'], 'abc1234')
        self.assertEqual(result['timings']['queue_wait_s'], 2)

    def test_exit_zero_steps_but_suite_failed(self):
        """A gate whose every exit line is 0 but the receipt says failures: failed."""
        files = dict(GREEN, suite=['suite-exit=0 image=gate', 'FAIL test_release.Release.test_x',
                                   '{"started": "a", "tests_run": 262, "failures": 2, "errors": 20, "skipped": 0, '
                                   '"successful": false}'])
        result = self.parse(files)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_steps'], ['suite'])
        self.assertEqual(result['numbers']['errors'], 20)
        self.assertEqual(result['failures'], ['FAIL test_release.Release.test_x'])

    def test_failed_preflight_with_suite_green(self):
        result = self.parse(dict(GREEN, preflight=['preflight-exit=1', "FileNotFoundError: 'git'"]))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_steps'], ['preflight'])
        self.assertIn('git', result['steps']['preflight']['detail'])

    def test_each_step_failure_is_seen(self):
        cases = {
            'host-parity-windows': dict(GREEN, hostparity=['host-parity-linux-exit=0', 'host-parity-windows-exit=1']),
            'engine': dict(GREEN, engine=['engine-exit=0', '3', 'x']),
            'smoke': dict(GREEN, smoke=['smoke-exit=1', 'FAIL emulator exited loading seyda']),
        }
        for number, (step, files) in enumerate(cases.items(), start=20):
            result = self.parse(files, number)
            self.assertEqual(result['failed_steps'], [step], step)

    def test_missing_step_files_fail(self):
        files = {k: v for k, v in GREEN.items() if k not in ('engine', 'hostparity')}
        result = self.parse(files)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_steps'], ['host-parity-linux', 'host-parity-windows', 'engine'])

    def test_suite_without_receipt_or_tests_fails(self):
        self.assertEqual(self.parse(dict(GREEN, suite=['suite-exit=0']))['failed_steps'], ['suite'])
        zero = dict(GREEN, suite=['suite-exit=0', '{"started": "a", "tests_run": 0, "failures": 0, "errors": 0, '
                                                 '"successful": true}'])
        self.assertEqual(self.parse(zero, 8)['failed_steps'], ['suite'])

    def test_receipt_file_wins_over_cut_line(self):
        files = dict(GREEN, suite=['suite-exit=0', '{"started": "a", "tests_run": 3165, "failures": 0, "errors": 0, '
                                                  '"skipped": 3, "unexpected_skips": 0, "node": "/usr/loc'])
        (self.dir / 'suite-9').mkdir()
        (self.dir / 'suite-9' / 'receipt.json').write_text(json.dumps(
            {'tests_run': 3000, 'failures': 1, 'errors': 0, 'successful': False}), encoding='utf-8')
        result = self.parse(files, 9)
        self.assertEqual(result['numbers']['tests_run'], 3000)
        self.assertEqual(result['failed_steps'], ['suite'])

    def test_cut_short_line_is_read_field_by_field(self):
        files = dict(GREEN, suite=['suite-exit=0', '{"started": "a", "seconds": 5.0, "tests_run": 3165, "failures": 0, '
                                                  '"errors": 0, "skipped": 3, "successful": true, "source_mut'])
        result = self.parse(files)
        self.assertEqual(result['status'], 'passed', result)

    def test_other_head_fails(self):
        result = self.parse(GREEN, head='fff0000')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('not the requested commit', ' '.join(result['notes']))

    def test_no_files_is_refused(self):
        self.assertEqual(aw.parse_gate(self.dir, 5)['status'], 'refused')


FAKE_GATE = '''
import os, sys
from pathlib import Path
n = sys.argv[1]
out = Path(sys.argv[2])
mode = sys.argv[3]
files = {
    'repo': 'gate %s repo %s head %s dirty 0' % (n, os.environ['REPO'], os.environ['FAKE_HEAD']),
    'preflight': 'preflight-exit=0\\nok',
    'suite': 'suite-exit=0\\n{"started": "a", "tests_run": 5, "failures": %d, "errors": 0, "successful": %s}'
             % ((0, 'true') if mode == 'green' else (1, 'false')),
    'hostparity': 'host-parity-linux-exit=0\\nhost-parity-windows-exit=0',
    'engine': 'engine-exit=0\\n0',
    'smoke': 'smoke-exit=0\\nPASS',
}
for name, text in files.items():
    (out / ('par-%s-%s.out' % (n, name))).write_text(text + '\\n')
print('fake gate', n, mode)
sys.exit(0)
'''


class GateCommandTests(unittest.TestCase):
    """aw gate end to end with a stand-in gate script that always exits 0."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        (self.repo / 'VERSION').write_text('0.0.36-dev1\n', encoding='utf-8')
        self.fake = FakeGit()
        (self.base / 'fake_gate.py').write_text(FAKE_GATE, encoding='utf-8')
        record = self.base / 'WORKING_VERSION.json'
        record.write_text(json.dumps({'working_version': '0.0.36-dev1'}), encoding='utf-8')
        self.head = self.fake.head
        os.environ['FAKE_HEAD'] = self.head

    def tearDown(self):
        os.environ.pop('FAKE_HEAD', None)
        self.tmp.cleanup()

    def run_gate(self, mode, *extra):
        path, config = config_in(self.base, working_version_file=str(self.base / 'WORKING_VERSION.json'))
        config_data = json.loads(path.read_text())
        config_data['gate']['command'] = [sys.executable, str(self.base / 'fake_gate.py'), '{number}',
                                          str(self.base / 'gate'), mode]
        path.write_text(json.dumps(config_data))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), self.fake.patch():
            code = aw.main(['--config', str(path), 'gate', '--repo', str(self.repo), '--reason', 'unit test',
                            '--requester', 'tester', '--quiet', *extra])
        return code, aw.load_config(path), out.getvalue()

    def result_files(self, config):
        return sorted((Path(config['state_dir']) / 'results').glob('*.json'))

    def test_green(self):
        code, config, out = self.run_gate('green')
        self.assertEqual(code, 0, out)
        result = json.loads(self.result_files(config)[0].read_text())
        self.assertEqual(aw.validate(result, aw.schema('aw-result-1')), [])
        self.assertEqual((result['status'], result['gate'], result['numbers']['tests_run']), ('passed', 10, 5))
        self.assertTrue(result['run_name'].endswith(f'_gate-10-unit-test_{self.head}'))
        self.assertEqual(aw.list_leases(config), [], 'leases are released after the gate')
        events = [json.loads(line)['event'] for line in aw.trial_log_path(config).read_text().splitlines()]
        for event in ('lease', 'request', 'result', 'release'):
            self.assertIn(event, events)

    def test_script_exit_zero_but_red_exits_nonzero(self):
        code, config, out = self.run_gate('red')
        self.assertEqual(code, 1, out)
        result = json.loads(self.result_files(config)[0].read_text())
        self.assertEqual((result['status'], result['script_exit'], result['failed_steps']), ('failed', 0, ['suite']))
        self.assertIn("exited 0 but steps failed", ' '.join(result['notes']))

    def test_wrong_commit_and_dirty_tree_are_refused(self):
        code, config, _ = self.run_gate('green', '--commit', '0000000')
        self.assertEqual(code, 2)
        self.fake.dirty = '?? new.txt'
        code, config, _ = self.run_gate('green')
        self.assertEqual(code, 2)
        results = [json.loads(p.read_text()) for p in self.result_files(config)]
        self.assertEqual({r['status'] for r in results}, {'refused'})
        self.assertEqual(aw.load_state(config)['gate_spent'], [], 'a refused request spends no gate number')

    def test_a_test_file_missing_from_the_public_file_list_is_refused_by_name(self):
        # OPS-GATE-UNLISTED-TESTS-36: the gate stages only listed files; an unlisted test would never run.
        (self.repo / 'tools').mkdir()
        (self.repo / 'tests').mkdir()
        (self.repo / 'tests' / 'test_listed.py').write_text('x = 1\n', encoding='utf-8')
        (self.repo / 'tools' / 'release-files.json').write_text(json.dumps(['tests/test_listed.py']),
                                                                encoding='utf-8')
        code, _, _ = self.run_gate('green')
        self.assertEqual(code, 0)
        (self.repo / 'tests' / 'test_forgotten.py').write_text('x = 1\n', encoding='utf-8')
        code, config, _ = self.run_gate('green')
        self.assertEqual(code, 2)
        refused = [json.loads(p.read_text()) for p in self.result_files(config)]
        refused = [r for r in refused if r['status'] == 'refused']
        self.assertEqual(len(refused), 1)
        self.assertIn('tests/test_forgotten.py', ' '.join(refused[0]['notes']))
        self.assertEqual(len(aw.load_state(config)['gate_spent']), 1, 'the refused request spends no gate number')

    def test_version_mismatch_is_refused(self):
        (self.base / 'WORKING_VERSION.json').write_text(json.dumps({'working_version': '0.0.99'}))
        code, _, _ = self.run_gate('green')
        self.assertEqual(code, 2)
        code, _, _ = self.run_gate('green', '--accept-version-mismatch', 'test')
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
