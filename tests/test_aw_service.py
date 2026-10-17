# SPDX-License-Identifier: GPL-3.0-only
"""The master builder's request service (tools/aw_service.py): request forms, refusals (stale builder head, version
mismatch, retired and managed flags, unexplained rebuilds, input hashes), run names and result writing. Docker and
git are replaced by fakes: nothing here runs a container."""
import contextlib
import io
import json
import time
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import aw  # noqa: E402
import aw_service  # noqa: E402

FULL = 'abc1234' + '0' * 33
HEAD = 'def5678'
SHA = 'a' * 64

CHECK_OK = '\n'.join([
    'Run name: 2026_10_10_v0.0.36-dev3_full_abc1234',
    '=' * 72,
    'Developer mode: OK (source /vol/src/v036-abc1234)',
    '  (a) working version: source 0.0.36-dev3, record 0.0.36-dev3 (/vol/WORKING_VERSION.json)',
    '  (b) source: every builder module from the source tree',
    '  (f) reuse preflight: 34 of 36 stages reusable, 2 rebuilt, 0 unexpected',
    '=' * 72,
    'Prerequisites passed. Scope: aga; data: /owned',
    'Checks completed. No build outputs created.',
])

INTEGRATION_FILE = """PUBLISHED (aw gate 1596 PASSED): def5678  branch integration/latest = v0.0.36-dev  (VERSION 0.0.36-dev3)
CONTAINS since 642c1ea: VERSION 0.0.36-dev3 + dev3 presets; chunk references.

PUBLISHED (aw gate 1595 PASSED): 642c1ea  branch integration/latest = v0.0.36-dev  (VERSION 0.0.36-dev2)
CONTAINS since ec6dacf: older.
"""


class FakeRunner:
    """Answers every container command by its --name; records what ran."""

    def __init__(self, check=CHECK_OK, check_exit=0, build_exit=0, summary=None, inputs=None, existing=(),
                 records_exit=0, guard=None, guard_exit=0, guard_err=''):
        self.check, self.check_exit, self.build_exit = check, check_exit, build_exit
        self.guard = guard if guard is not None else {'verdict': 'passed', 'failed': 0, 'waived': 0, 'busy': 0,
                                                      'sections': 12, 'failing': [], 'waivers': []}
        self.guard_exit, self.guard_err = guard_exit, guard_err
        self.records_exit = records_exit
        self.summary = summary if summary is not None else {
            'found': True, 'status': 'passed', 'stages': 36, 'reused': 34, 'rebuilt': 2, 'failed_stage': None,
            'not_started': 0}
        self.inputs = inputs if inputs is not None else f'{SHA}  /vol/in/cells.csv\n'
        self.existing = existing
        self.version = '0.0.36-dev3'
        self.ran = []

    @staticmethod
    def name(command):
        return command[command.index('--name') + 1]

    def capture(self, command, timeout=None):
        if command[1:3] == ['update', '--cpus']:
            self.ran.append('update %s %s' % (command[4], command[3]))
            return 0, command[4] + '\n', ''
        name = self.name(command)
        self.ran.append(name)
        if '-ls-' in name:
            return 0, '\n'.join(self.existing) + '\n', ''
        if '-check-' in name:
            return self.check_exit, self.check, ''
        if '-inputs-' in name:
            return 0, self.inputs, ''
        if '-summary-' in name:
            return 0, json.dumps(self.summary) + '\n', ''
        if '-ingest-' in name:
            return 0, 'ingested 36 stages\n', ''
        if '-perf-guard-' in name:
            if self.guard_err:
                return self.guard_exit, '', self.guard_err
            return self.guard_exit, json.dumps(self.guard) + '\n', ''
        if '-stair-records-' in name:
            if self.records_exit:
                return self.records_exit, '', "python3: can't open file 'tools/stair_records.py'\n"
            return 0, json.dumps({'run': 'r', 'reports': 1, 'marked': 270, 'already': 0, 'changed': 0, 'missing': 0,
                                  'reused': 0, 'walked': 270}) + '\n', ''
        raise AssertionError(f'unexpected command {command}')

    def pipe(self, producer, consumer):
        self.ran.append(self.name(consumer))
        return 0, f'aw: source exists\n{self.version}\n', ''

    def logged(self, command, log_path):
        self.ran.append(self.name(command))
        Path(log_path).write_text('build log\n', encoding='utf-8')
        return self.build_exit


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / 'WORKING_VERSION.json').write_text(json.dumps({'working_version': '0.0.36-dev3', 'head': HEAD}),
                                                   encoding='utf-8')
        (base / 'integration-head.txt').write_text(INTEGRATION_FILE, encoding='utf-8')
        config = {'schema': 'aw-config-1', 'state_dir': 'state', 'working_version_file': 'WORKING_VERSION.json',
                  'integration_ref': 'integration/latest', 'integration_head_file': 'integration-head.txt',
                  'gate': {'ranges': {'t': [1, 2]}, 'default_range': 't'},
                  'build': {'image': 'builder:test', 'volume': 'pool-vol', 'inputs_volume': 'game-vol',
                            'workspace': '/vol/ws8', 'cpus': 24, 'memory': '44g', 'jobs': 24, 'host_threads': 24,
                            'host_memory_gib': 100, 'memory_reserve_gib': 4, 'gate_memory_gib': 6,
                            'queue_timeout_s': 0, 'queue_poll_s': 0,
                            'default_flags': [['--chim-native-towns', 'on'], ['--live-logs']],
                            'trials_log': 'trials/TRIALS.jsonl',
                            'ingest': {'image': 'perf:test', 'mounts': ['/host/notes:/c'],
                                       'command': ['python3', '/c/ingest.py', '{run_dir}', '--label', '{run_name}']}}}
        path = base / 'aw-config.json'
        path.write_text(json.dumps(config), encoding='utf-8')
        self.config = aw.load_config(path)
        self.base = base
        self.version = '0.0.36-dev3'
        self.contains = True
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(aw_service, 'git_text', self.git))
        stack.enter_context(mock.patch.object(aw, 'git_short', lambda repo, rev='HEAD': HEAD if rev ==
                                              'integration/latest' else 'abc1234'))
        stack.enter_context(mock.patch.object(aw, 'is_ancestor', lambda repo, commit, rev='HEAD': self.contains))
        self.addCleanup(stack.close)
        self.addCleanup(self.tmp.cleanup)

    def git(self, repo, *args):
        if args[0] == 'ls-tree':
            # the published head and (unless a test says otherwise) the requested commit have the records layer
            return args[-1] + '\n' if args[2] == HEAD or getattr(self, 'records_layer', True) else ''
        if args[0] == 'rev-parse':
            return FULL if args[-1].startswith('abc1234') else None
        if args[0] == 'show' and args[-1].endswith(':config/miniwind-presets.json'):
            return json.dumps({'format': 1, 'presets': [{'name': 'balmora'}, {'name': 'vivec-arena-pit'}]})
        if args[0] == 'show':
            return self.version + '\n'
        if args[0] == 'diff':
            return 'tools/chim/regions.py\n'
        return None

    def request(self, **change):
        doc = {'schema': 'aw-request-1', 'id': 'req-1', 'kind': 'build', 'repo': '/src/wt', 'commit': 'abc1234',
               'purpose': 'full', 'version': 'v0.0.36-dev3', 'reason': 'dev3 sea ring', 'requester': 'worker-a',
               'time': '2026-10-10 18:00:00 +0300',
               'options': {'flags': ['--no-npc-gallery'],
                           'reuse_from': '/vol/ws8/build/2026_10_10_v0.0.36-dev2_full_642c1ea'}}
        doc.update(change)
        return doc

    def submit(self, request, runner=None, dry_run=False):
        runner = runner or FakeRunner()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code, path = aw_service.submit(self.config, request, dry_run=dry_run, runner=runner)
        result = json.loads(Path(path).read_text(encoding='utf-8')) if path else None
        return code, result, runner

    # ---- forms

    def test_request_forms(self):
        self.assertEqual(aw_service.request_errors(self.request()), [])
        for kind in aw.KINDS:
            self.assertEqual(aw_service.request_errors(self.request(kind=kind, options={})), [], kind)
        bad = [self.request(options={'flags': '--no-npc-gallery'}),
               self.request(options={'reuse_from': 'C:/Program Files/Git/vol/ws8/build/x'}),
               self.request(options={'inputs': [{'path': '/vol/a.csv', 'sha256': 'abc'}]}),
               self.request(options={'colour': 'red'}),
               self.request(override={'reason': 'short', 'allow': ['retired-flags']}),
               self.request(override={'reason': 'a long enough reason', 'allow': ['everything']}),
               self.request(kind='gate', options={'flags': []})]
        for doc in bad:
            self.assertTrue(aw_service.request_errors(doc), doc)
        self.assertIn('MSYS_NO_PATHCONV', ' '.join(aw_service.request_errors(bad[1])))
        with self.assertRaisesRegex(aw_service.Refused, 'malformed request'):
            aw_service.submit(self.config, self.request(kind='deploy'), runner=FakeRunner())

    def test_flag_parsing(self):
        self.assertEqual(aw_service.retired_hits(['--chim-native-towns', 'on']), [])
        self.assertEqual(len(aw_service.retired_hits(['--chim-native-towns=off'])), 1)
        self.assertEqual(len(aw_service.retired_hits(['--chim-native-towns', 'off', '--legacy-area', 'balmora'])), 2)
        self.assertEqual(len(aw_service.managed_hits(['--name', 'x', '--reuse-from=/vol/r', '--jobs', '3'])), 3)
        self.assertEqual(aw_service.with_defaults(['--chim-native-towns', 'off'], [['--chim-native-towns', 'on'],
                                                                                   ['--live-logs']]),
                         ['--chim-native-towns', 'off', '--live-logs'])
        self.assertEqual(aw_service.series('v0.0.36-dev3'), 'v036')
        self.assertEqual(aw_service.reuse_commit_of('/vol/ws8/build/2026_10_10_v0.0.36-dev2_full-x-try2_642c1ea/'),
                         '642c1ea')

    def test_published_head(self):
        published = aw_service.published_integration(self.config)
        self.assertEqual(published['head'], HEAD)
        self.assertEqual(len(published['contains']), 1)
        self.assertIn('chunk references', published['contains'][0])

    def test_status_shows_the_published_builder_head(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            aw.cmd_status(aw.parser().parse_args(['status']), self.config)
        self.assertIn(f'published builder head: {HEAD}', out.getvalue())
        self.assertIn('CONTAINS since 642c1ea', out.getvalue())

    def test_parse_check_reads_the_developer_mode_block(self):
        found = aw_service.parse_check(CHECK_OK)
        self.assertEqual(found['preflight'], {'reused': 34, 'stages': 36, 'rebuilt': 2, 'unexpected': 0,
                                              'too_broad': []})
        self.assertTrue(found['completed'])
        broad = aw_service.parse_check('(f) reuse preflight: 9 of 36 stages reusable, 27 rebuilt, 0 unexpected, '
                                       'keys too broad: scene, bsp')
        self.assertEqual(broad['preflight']['too_broad'], ['scene', 'bsp'])

    # ---- the resource plan in the check (tools/resource_plan.py, fixlist B41)

    def with_resource_plan(self):
        plain = self.git

        def git(repo, *args):
            if args[0] == 'cat-file' and args[-1].endswith(':' + aw_service.RESOURCE_MODULE):
                return ''
            return plain(repo, *args)
        return mock.patch.object(aw_service, 'git_text', git)

    def test_the_check_carries_the_resource_plan_of_the_leased_container(self):
        check = CHECK_OK + '\n' + '\n'.join([
            'Resource plan: 5 of 22 stages run; the build gets 30720 MiB (asked) and 24 threads (asked); --jobs 24',
            '  WILL THROTTLE chim                     8 of 11 workers; about 2643 MiB a worker',
            'ADVISORY: this build would run up to 27 % faster in chim with 10 GiB more memory '
            '(the lease to ask for: --threads 24 --mem-gb 40)',
            'Resource plan: THROTTLED (4 OK, 1 WILL THROTTLE, 0 WILL NOT FIT)'])
        found = aw_service.parse_check(check)
        self.assertEqual(len(found['resources']), 4)
        with self.with_resource_plan():
            code, result, runner = self.submit(self.request(), FakeRunner(check=check))
        self.assertEqual(code, 0, result['notes'])
        command = [c for c in result['commands'] if ' --check' in c][0]
        self.assertIn('--resource-plan --resource-memory-gb', command)
        self.assertIn('--resource-threads', command)
        self.assertTrue(any(note.startswith('resource plan: ADVISORY:') for note in result['notes']))

    def test_a_check_without_the_resource_plan_module_stays_as_it_was(self):
        code, result, _ = self.submit(self.request())
        command = [c for c in result['commands'] if ' --check' in c][0]
        self.assertNotIn('--resource-plan', command)

    def test_will_not_fit_in_the_check_refuses_the_build(self):
        check = CHECK_OK + '\n  WILL NOT FIT  chim refused before any stage: one unit (stair walk) needs 2643 MiB'
        with self.with_resource_plan():
            code, result, runner = self.submit(self.request(),
                                               FakeRunner(check=check, check_exit=aw_service.RESOURCE_PLAN_EXIT))
        self.assertNotEqual(code, 0)
        self.assertTrue(any('WILL NOT FIT' in text for text in result['refusals']), result['refusals'])
        self.assertFalse(any('-build-' in name for name in runner.ran))

    def test_a_busy_host_makes_the_build_wait_and_says_so(self):
        states = iter([{'line': 'machine: CPU 97 %', 'busy': True, 'wait_reason': 'host busy: CPU >= 90 %'},
                       {'line': 'machine: CPU 40 %', 'busy': False}])
        self.config['build']['machine_state_command'] = ['state-tool']
        self.config['build']['queue_timeout_s'] = 60
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return mock.Mock(stdout=json.dumps(next(states)) + '\n')
        out = io.StringIO()
        with mock.patch.object(aw_service.subprocess, 'run', run), contextlib.redirect_stdout(out):
            request, info, lease = aw_service.take_cores(self.config, self.request(), 'run-x', FakeRunner(), [],
                                                         sleep=lambda s: None)
        self.assertEqual(len(calls), 2)
        self.assertIn('--threads', calls[0])
        self.assertIn('waiting', out.getvalue())
        self.assertIn('machine: CPU 40 %', out.getvalue())

    # ---- a full build, docker replaced

    def test_build_runs_and_writes_its_result_and_trial(self):
        code, result, runner = self.submit(self.request())
        self.assertEqual(code, 0, result['notes'])
        self.assertEqual(result['status'], 'passed')
        self.assertRegex(result['run_name'], r'^\d{4}_\d{2}_\d{2}_v0\.0\.36-dev3_full-dev3-sea-ring_abc1234$')
        self.assertEqual(result['numbers']['reused_stages'], 34)
        self.assertEqual(result['reuse']['planned_reuse'], 34)
        self.assertEqual(result['reuse']['diff_files'], 1)
        self.assertEqual(sorted(result['steps']),
                         sorted(['checks', 'stage-source', 'check', 'build', 'summary', 'perf-guard', 'stair-records',
                                 'trial-log',
                                 'perf-ingest']))
        # a passed build's stair-walk records become master-checked (tools/stair_records.py promote)
        self.assertEqual(result['stair_walk']['marked'], 270)
        promote = [c for c in result['commands'] if 'stair_records.py promote' in c][0]
        self.assertIn('--request req-1', promote)
        build = [c for c in result['commands'] if ' --check' not in c and 'tools/build.py' in c][0]
        for part in ('--pull never', '--network none', '--user 1000:1000', '--developer-mode', '--storage-pool on',
                     '--reuse-mode pool', '--source-commit abc1234', '--chim-native-towns on', '--no-npc-gallery',
                     'PYTHONPATH=/vol/src/v036-abc1234/src:/vol/src/v036-abc1234/tools', '--cpus 24'):
            self.assertIn(part, build)
        self.assertIn('AMIWIND_AW_REQUEST=req-1', build)
        self.assertEqual(aw.validate(result, aw.schema('aw-result-1')), [])
        trials = (self.base / 'trials' / 'TRIALS.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(trials), 1)
        line = json.loads(trials[0])
        self.assertEqual((line['result'], line['commit'], line['version']), ('passed', 'abc1234', '0.0.36-dev3'))
        self.assertTrue(any('-check-' in name for name in runner.ran))

    def test_a_failed_record_marking_never_fails_a_passed_build(self):
        # e.g. a commit from before the records layer: the build passed, its walks just stay candidates
        code, result, _ = self.submit(self.request(), FakeRunner(records_exit=2))
        self.assertEqual((code, result['status']), (0, 'passed'))
        self.assertFalse(result['steps']['stair-records']['ok'])
        self.assertIn('stair_records.py', result['steps']['stair-records']['detail'])
        self.assertNotIn('stair_walk', result)

    # ---- machine-wide core leases (docs/AW.md "Core leases")

    def test_core_plan_never_oversubscribes_and_follows_priority(self):
        holders = [{'id': 'a', 'priority': 'dev', 'want': 24}, {'id': 'b', 'priority': 'optional', 'want': 24},
                   {'id': 'c', 'priority': 'release', 'want': 24}]
        plan = aw.core_plan(24, holders, fixed=0, minimum=2)
        self.assertEqual(sum(plan.values()), 24)
        self.assertGreater(plan['c'], plan['a'])
        self.assertGreater(plan['a'], plan['b'])
        self.assertEqual(aw.core_plan(24, holders[:1]), {'a': 24})
        self.assertEqual(aw.core_plan(24, [dict(holders[0], want=6)]), {'a': 6})       # never more than it asks
        self.assertEqual(sum(aw.core_plan(24, holders, fixed=8).values()), 16)          # running gates hold cores
        self.assertIsNone(aw.core_plan(5, holders, minimum=2))                          # full: no build squeezed in

    def test_leases_rebalance_when_builds_start_and_end(self):
        first, changes = aw.lease_cores(self.config, 'run-dev', 'w1', 'dev', 24, 'aw-build-run-dev')
        self.assertEqual((first['cores'], changes), (24, []))
        second, changes = aw.lease_cores(self.config, 'run-rc', 'w2', 'release', 24, 'aw-build-run-rc')
        self.assertEqual(second['cores'] + changes[0][2], 24)
        self.assertGreater(second['cores'], changes[0][2])
        self.assertEqual(changes[0][:2], ('aw-build-run-dev', 24))
        grown = aw.release_cores(self.config, second['id'])
        self.assertEqual(grown, [('aw-build-run-dev', changes[0][2], 24)])
        aw.release_cores(self.config, first['id'])
        self.assertEqual(aw.active(aw.load_state(self.config), 'cores'), [])

    def test_running_builds_grow_back_when_a_gate_ends(self):
        # AW-LEASE-NO-GROW-36: a gate that starts takes its cores from the running builds, and gives them back
        build, _ = aw.lease_cores(self.config, 'run-a', 'w1', 'dev', 24, 'aw-build-run-a')
        self.assertEqual(build['cores'], 24)
        gate = aw.lease_gate(self.config, 'w2')
        shrunk = aw.rebalance_running(self.config)
        gate_cores = aw.core_settings(self.config)[2]
        self.assertEqual(shrunk, [('aw-build-run-a', 24, 24 - gate_cores)])
        aw.release(self.config, gate['id'])
        self.assertEqual(aw.rebalance_running(self.config), [('aw-build-run-a', 24 - gate_cores, 24)])
        aw.release_cores(self.config, build['id'])

    def test_a_build_runs_on_its_leased_cores_and_gives_them_back(self):
        running, _ = aw.lease_cores(self.config, 'run-optional', 'w1', 'optional', 24, 'aw-build-run-optional')
        request = self.request(purpose='rc1')
        code, result, runner = self.submit(request)
        self.assertEqual((code, result['status']), (0, 'passed'), result['notes'])
        cores = result['cores']
        self.assertEqual(cores['priority'], 'release')
        self.assertEqual(cores['host_threads'], 24)
        self.assertLess(cores['leased'], 24)
        build = [line for line in result['commands'] if ' --jobs ' in line][-1]
        self.assertIn(f"--jobs {cores['leased']}", build)
        self.assertIn(f"--cpus {cores['leased']}", build)
        # the running optional build shrank for it, and got its cores back when it ended
        updates = [name for name in runner.ran if name.startswith('update aw-build-run-optional')]
        self.assertEqual(updates, [f"update aw-build-run-optional {24 - cores['leased']}",
                                   'update aw-build-run-optional 24'])
        self.assertEqual([lease['key'] for lease in aw.active(aw.load_state(self.config), 'cores')], ['run-optional'])
        aw.release_cores(self.config, running['id'])

    def test_a_full_machine_refuses_the_build(self):
        for index in range(12):
            aw.lease_cores(self.config, f'run-{index}', 'w', 'dev', 2, f'aw-build-run-{index}')
        code, result, _ = self.submit(self.request())
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('no cores free' in text for text in result['refusals']), result['refusals'])

    def test_memory_is_leased_and_a_misfit_waits_in_the_queue(self):
        build = self.config['build']
        build['host_memory_gib'] = 62
        build['queue_timeout_s'] = 600
        first, _ = aw.lease_cores(self.config, 'run-a', 'w1', 'dev', 24, 'aw-build-run-a', memory_gib=44)
        self.assertEqual(first['memory_gib'], 44)
        with self.assertRaisesRegex(aw.AwError, 'no memory free: 44 GiB wanted, 14 GiB of 62 free'):
            aw.lease_cores(self.config, 'run-b', 'w2', 'dev', 24, 'aw-build-run-b', memory_gib=44)
        # a queued release build goes before a dev build that asked later, once the memory is free
        self.assertEqual(aw.lease_cores(self.config, 'run-rel', 'w3', 'release', 24, 'c-rel', memory_gib=44,
                                        ticket='run-rel')[0], None)
        self.assertEqual(aw.lease_cores(self.config, 'run-dev', 'w4', 'dev', 24, 'c-dev', memory_gib=10,
                                        ticket='run-dev'),
                         (None, 'a queued request of higher or equal priority goes first'))
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            aw.release_cores(self.config, first['id'])     # the running build ends while the request waits

        request = self.request(purpose='release', options={'memory': '44g'})
        notes = []
        request, info, lease = aw_service.take_cores(self.config, dict(request, requester='w3'), 'run-rel',
                                                     FakeRunner(), notes, sleep=sleep)
        self.assertEqual(len(slept), 1)
        self.assertEqual((info['priority'], info['memory_gib'], lease['memory_gib']), ('release', 44.0, 44.0))
        self.assertEqual(request['options']['memory'], '44g')
        self.assertTrue(any(note.startswith('queued') for note in notes), notes)
        self.assertEqual([item['ticket'] for item in aw.load_state(self.config)['queue']], ['run-dev'])
        aw.dequeue(self.config, 'run-dev')
        aw.release_cores(self.config, lease['id'])

    def test_a_queued_request_gives_up_after_the_timeout(self):
        # AW-LEASE-MEMORY-DEADLOCK-36: a request that could fit waits; here a running build holds the memory
        self.config['build'].update(host_memory_gib=20, queue_timeout_s=60, queue_poll_s=30)
        held, _ = aw.lease_cores(self.config, 'run-held', 'w', 'dev', 2, 'c-held', memory_gib=12)
        slept = []
        with self.assertRaisesRegex(aw.AwError, r'no memory free.*queued 60 s'):
            # the in-memory config of this test (no file to read again)
            config = {k: v for k, v in self.config.items() if k != '_path'}
            aw_service.take_cores(config, self.request(options={'memory': '8g'}), 'run-x', FakeRunner(), [],
                                  sleep=slept.append)
        self.assertEqual(slept, [30, 30])
        self.assertEqual(aw.load_state(self.config)['queue'], [])
        aw.release_cores(self.config, held['id'])

    def test_memory_leases_never_deadlock_behind_gates(self):
        # AW-LEASE-MEMORY-DEADLOCK-36: 44 GiB against 47 - 3 - 6 per gate never fit while a gate ran
        build = self.config['build']
        build.update(host_memory_gib=47, memory_reserve_gib=3, gate_memory_gib=6, memory='44g')
        memory, note = aw_service.memory_lease(self.config)
        self.assertEqual(memory, 38)                       # the default fits beside one running gate
        self.assertIn('fits beside a running gate', note)
        self.assertEqual(aw_service.memory_lease(self.config, '16g'), (16, None))
        memory, note = aw_service.memory_lease(self.config, '42g')
        self.assertEqual(memory, 42)                       # explicit: kept, said to wait for a gate-free moment
        self.assertIn('only while no gate runs', note)
        with self.assertRaisesRegex(aw.AwError, 'can never fit: 45 GiB wanted'):
            aw_service.memory_lease(self.config, '45g')    # more than the host leases: refused at once

    def test_a_waiting_request_reads_the_config_again(self):
        # AW-LEASE-MEMORY-DEADLOCK-36: a lease size changed in the config reaches a request already waiting
        path = self.base / 'aw-config.json'
        self.config['build'].update(host_memory_gib=20, memory_reserve_gib=4, gate_memory_gib=0, memory='16g',
                                    queue_timeout_s=600, queue_poll_s=30)
        held, _ = aw.lease_cores(self.config, 'run-held', 'w', 'dev', 2, 'c-held', memory_gib=8)
        saved = {k: v for k, v in self.config.items() if k != '_path'}
        path.write_text(json.dumps(saved), encoding='utf-8')
        config = aw.load_config(path)
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            changed = json.loads(path.read_text(encoding='utf-8'))
            changed['build']['memory'] = '6g'               # the owner of the config lowers the default
            path.write_text(json.dumps(changed), encoding='utf-8')

        request, info, lease = aw_service.take_cores(config, self.request(), 'run-y', FakeRunner(), [], sleep=sleep)
        self.assertEqual((len(slept), info['memory_gib']), (1, 6.0))
        aw.release_cores(config, lease['id'])
        aw.release_cores(config, held['id'])

    def test_leases_of_finished_jobs_end(self):
        # worktree name -> (HEAD merged into the integration ref, git status --porcelain, last commit epoch)
        old = str(int(time.time()) - 7200)
        repos = {'wt-done': (True, '', old), 'wt-busy': (False, '', old), 'wt-dirty': (True, ' M wip.txt', old),
                 'wt-recent': (True, '', str(int(time.time())))}
        for name in repos:
            (self.base / name).mkdir()

        def git(repo, *args):
            merged, status, committed = repos[Path(repo).name]
            return {'rev-parse': 'f' * 40, 'status': status, 'log': committed}[args[0]]

        def is_ancestor(repo, commit, rev='HEAD'):
            return repos[Path(repo).name][0]

        self.config['lease_idle_s'] = {'worktree': 3600}
        for name in list(repos) + ['wt-gone']:       # wt-gone: removed after its merge (its parent folder remains)
            aw.lease_worktree(self.config, str(self.base / name), name)
        lease = aw.load_state(self.config)
        for row in lease['leases']:                    # the leases were taken two hours ago and never renewed
            row['expires_epoch'] -= 7200
        aw.save_state(self.config, lease)
        with mock.patch.object(aw, 'git', git), mock.patch.object(aw, 'is_ancestor', is_ancestor):
            left = sorted(row['requester'] for row in aw.list_leases(self.config) if row['kind'] == 'worktree')
        self.assertEqual(left, ['wt-busy', 'wt-dirty', 'wt-recent'])
        why = {row['requester']: row['expired_because'] for row in aw.list_leases(self.config, everything=True)
               if row['status'] == 'expired'}
        self.assertIn('merged into integration/latest, the worktree is clean and idle', why['wt-done'])
        self.assertEqual(why['wt-gone'], 'the worktree is gone')
        # a worktree this host cannot see is never judged
        aw.lease_worktree(self.config, '/nowhere/at/all/wt', 'wt-elsewhere')
        self.assertIn('wt-elsewhere', [row['requester'] for row in aw.list_leases(self.config)])

    def test_a_job_reports_done_and_all_its_leases_end(self):
        aw.lease_worktree(self.config, str(self.base), 'job-x')
        cores, _ = aw.lease_cores(self.config, 'run-x', 'job-x', 'dev', 24, 'aw-build-run-x')
        other, changes = aw.lease_cores(self.config, 'run-y', 'job-y', 'dev', 24, 'aw-build-run-y')
        ended, grown = aw.job_done(self.config, 'job-x')
        self.assertEqual(len(ended), 2)
        self.assertEqual(grown, [('aw-build-run-y', other['cores'], 24)])
        self.assertEqual([lease['requester'] for lease in aw.list_leases(self.config)], ['job-y'])

    def test_priority_defaults(self):
        self.assertEqual(aw_service.core_priority({'purpose': 'release'}), 'release')
        self.assertEqual(aw_service.core_priority({'purpose': 'rc1-coast'}), 'release')
        self.assertEqual(aw_service.core_priority({'purpose': 'full-coast2'}), 'dev')
        self.assertEqual(aw_service.core_priority({'purpose': 'full', 'options': {'priority': 'optional'}}),
                         'optional')

    # ---- perf guard (docs/BUILD_PROFILE.md "Perf guard")

    def test_a_passed_perf_guard_is_in_the_result(self):
        code, result, runner = self.submit(self.request())
        self.assertEqual((code, result['status']), (0, 'passed'))
        self.assertTrue(result['steps']['perf-guard']['ok'])
        self.assertEqual(result['perf_guard']['verdict'], 'passed')
        self.assertIn('perf guard PASSED', aw.perf_guard_text(result['perf_guard']))

    def test_a_failed_perf_guard_fails_the_build_result(self):
        guard = {'verdict': 'failed', 'failed': 1, 'waived': 1, 'busy': 0, 'sections': 9, 'waivers': ['X-36'],
                 'failing': ['image / Image: stair walk: parallel -> serial: 1.10 cores, was 11.60']}
        code, result, _ = self.submit(self.request(), FakeRunner(build_exit=3, guard=guard, guard_exit=1))
        self.assertEqual(result['status'], 'failed')
        self.assertNotEqual(code, 0)
        self.assertTrue(result['steps']['build']['ok'], result['steps']['build'])
        self.assertFalse(result['steps']['perf-guard']['ok'])
        self.assertIn('parallel -> serial', result['steps']['perf-guard']['detail'])
        self.assertEqual(result['failed_stage'], 'perf-guard')
        self.assertEqual(result['failed_steps'], ['perf-guard'])
        # the stages passed: their stair walks still become reusable records
        self.assertTrue(result['steps']['stair-records']['ok'])
        self.assertIn('FAILED (1 failing), 1 waived (X-36)', aw.perf_guard_text(result['perf_guard']))

    def test_a_failed_size_guard_fails_the_result_but_keeps_the_stages(self):
        code, result, _ = self.submit(self.request(), FakeRunner(build_exit=4))
        self.assertEqual(result['status'], 'failed')
        self.assertNotEqual(code, 0)
        self.assertTrue(result['steps']['build']['ok'], result['steps']['build'])
        self.assertFalse(result['steps']['size-guard']['ok'])
        self.assertEqual(result['failed_stage'], 'size-guard')
        self.assertTrue(result['steps']['stair-records']['ok'])

    def test_exit_3_with_a_failed_stage_is_a_failed_build(self):
        summary = {'found': True, 'status': 'failed', 'stages': 36, 'reused': 0, 'rebuilt': 3,
                   'failed_stage': 'image', 'not_started': 0}
        code, result, _ = self.submit(self.request(), FakeRunner(build_exit=3, summary=summary))
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['steps']['build']['ok'])
        self.assertNotIn('perf-guard', result['steps'])

    def test_a_builder_without_the_perf_guard_passes_and_says_so(self):
        runner = FakeRunner(guard_exit=2, guard_err="python3: can't open file '/src/tools/perf_guard.py': "
                                                     "[Errno 2] No such file or directory\n")
        code, result, _ = self.submit(self.request(), runner)
        self.assertEqual((code, result['status']), (0, 'passed'))
        self.assertIn('no perf guard', result['steps']['perf-guard']['detail'])

    def test_a_missing_or_unreadable_verdict_fails(self):
        for runner in (FakeRunner(guard={'verdict': 'missing', 'detail': 'no perf-guard.json in the run'}),
                       FakeRunner(guard_exit=1, guard_err='Traceback: boom\n')):
            code, result, _ = self.submit(self.request(), runner)
            self.assertEqual(result['status'], 'failed')
            self.assertFalse(result['steps']['perf-guard']['ok'])

    def test_a_commit_without_the_published_records_layer_is_refused(self):
        self.records_layer = False
        code, result, _ = self.submit(self.request())
        self.assertEqual((code, result['status']), (2, 'refused'))
        self.assertTrue(any('HASHED STAIR WALKS' in text and 'tools/stair_records.py' in text
                            and 'git -C /src/wt merge integration/latest' in text for text in result['refusals']))

    def test_a_full_stair_walk_needs_the_regression_override(self):
        flags = {'flags': ['--no-npc-gallery', '--stair-walk-cache', 'full']}
        code, result, _ = self.submit(self.request(options=flags))
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('stair-walk-full' in text for text in result['refusals']))
        override = {'reason': 'nightly regression check of the stair walk', 'allow': ['stair-walk-full']}
        code, result, _ = self.submit(self.request(id='req-2', options=flags, override=override))
        self.assertEqual((code, result['status']), (0, 'passed'), result['notes'])
        self.assertIn('regression-beta-test', result['run_name'])
        self.assertEqual(result['override'], override)
        self.assertTrue(any(note.startswith('override (stair-walk-full') for note in result['notes']))
        self.assertTrue(aw_service.stair_walk_full(['--stair-walk-cache=full']))
        self.assertFalse(aw_service.stair_walk_full(['--stair-walk-cache', 'cached']))

    def test_status_shows_the_stair_walk_records_of_a_build(self):
        self.submit(self.request())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            aw.cmd_status(aw.parser().parse_args(['status']), self.config)
        self.assertIn('stair walks 0 reused, 270 walked, 270 records checked', out.getvalue())

    def test_existing_run_on_disk_gets_try2(self):
        first = aw.make_run_name('v0.0.36-dev3', 'full', 'abc1234', 'dev3 sea ring')
        code, result, _ = self.submit(self.request(), FakeRunner(existing=[first]))
        self.assertEqual(result['run_name'], first.replace('sea-ring_', 'sea-ring-try2_'))

    def test_failed_build_reports_the_failed_stage(self):
        runner = FakeRunner(build_exit=1, summary={'found': True, 'status': 'failed', 'stages': 36, 'reused': 30,
                                                   'rebuilt': 6, 'failed_stage': 'image', 'not_started': 0})
        code, result, _ = self.submit(self.request(), runner)
        self.assertEqual((code, result['status'], result['failed_stage']), (1, 'failed', 'image'))
        self.assertIn('build', result['failed_steps'])
        self.assertNotIn('stair-records', result['steps'])     # a failed build's records stay candidates
        line = json.loads((self.base / 'trials' / 'TRIALS.jsonl').read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual((line['result'], line['failed_stage']), ('failed', 'image'))

    def test_dry_run_prints_commands_runs_nothing(self):
        runner = FakeRunner()
        code, result, runner = self.submit(self.request(), runner, dry_run=True)
        self.assertEqual((code, result['dry_run']), (0, True))
        self.assertEqual([name for name in runner.ran if '-ls-' not in name], [])
        self.assertEqual(len(result['commands']), 7)  # source, check, build, summary, perf guard, stair records, ingest
        self.assertFalse((self.base / 'trials' / 'TRIALS.jsonl').exists())
        state = aw.load_state(self.config)
        self.assertEqual(state['run_names'], [])  # a dry run spends no name

    # ---- refusals

    def assertRefused(self, request, text, runner=None):
        code, result, runner = self.submit(request, runner)
        self.assertEqual((code, result['status']), (2, 'refused'), result['notes'])
        self.assertIn(text, ' '.join(result['refusals']))
        self.assertFalse(any('-build-' in name for name in runner.ran), 'refused requests never build')
        self.assertEqual(aw.validate(result, aw.schema('aw-result-1')), [])
        return result

    def test_stale_builder_head_is_refused_with_the_merge_instruction(self):
        self.contains = False
        result = self.assertRefused(self.request(), 'STALE BUILDER')
        self.assertIn('git -C /src/wt merge integration/latest', ' '.join(result['refusals']))
        self.assertEqual(sum('STALE BUILDER' in text for text in result['refusals']), 1)

    def test_version_mismatch_is_refused_unless_overridden(self):
        self.version = '0.0.36-dev2'
        self.assertRefused(self.request(version='v0.0.36-dev2'), 'working version')
        override = {'reason': 'resume of the dev2 playtest build', 'allow': ['version-mismatch']}
        runner = FakeRunner()
        runner.version = '0.0.36-dev2'
        code, result, _ = self.submit(self.request(version='v0.0.36-dev2', override=override), runner)
        self.assertEqual(code, 0, result['notes'])
        build = [c for c in result['commands'] if 'tools/build.py' in c and ' --check' not in c][0]
        self.assertIn("--accept-version-mismatch 'resume of the dev2 playtest build'", build)

    def test_request_version_must_match_the_commit(self):
        self.assertRefused(self.request(version='v0.0.36-dev2'), 'has VERSION v0.0.36-dev3')

    def test_retired_and_managed_flags_are_refused(self):
        self.assertRefused(self.request(options={'flags': ['--legacy-area', 'balmora']}), 'retired flag --legacy-area')
        self.assertRefused(self.request(options={'flags': ['--chim-native-towns', 'off']}), 'retired flag')
        self.assertRefused(self.request(options={'flags': ['--name', 'final4b']}), 'flag --name')

    def test_retired_flag_override_labels_the_run(self):
        override = {'reason': 'A/B of the dev1 Balmora regression', 'allow': ['retired-flags']}
        code, result, _ = self.submit(self.request(options={'flags': ['--legacy-area', 'balmora']},
                                                   override=override))
        self.assertEqual(code, 0, result['notes'])
        self.assertIn('ab-regression', result['run_name'])
        self.assertTrue(any('override (retired-flags' in note for note in result['notes']))

    def test_unexplained_rebuilds_are_refused_before_the_build(self):
        broad = CHECK_OK.replace('34 of 36 stages reusable, 2 rebuilt, 0 unexpected',
                                 '9 of 36 stages reusable, 27 rebuilt, 0 unexpected, keys too broad: scene, bsp')
        self.assertRefused(self.request(), 'does not explain (scene, bsp)', FakeRunner(check=broad))
        damaged = CHECK_OK.replace('2 rebuilt, 0 unexpected', '2 rebuilt, 3 unexpected')
        self.assertRefused(self.request(), 'UNEXPECTED', FakeRunner(check=damaged))
        override = {'reason': 'key fix is in this very commit', 'allow': ['unexplained-rebuilds']}
        code, result, _ = self.submit(self.request(override=override), FakeRunner(check=broad))
        self.assertEqual(code, 0, result['notes'])
        self.assertTrue(any('--accept-rebuild' in c for c in result['commands']))

    def test_developer_mode_refusal_in_the_check_stops_the_build(self):
        refused = CHECK_OK.replace('Developer mode: OK', 'Developer mode: REFUSED') + (
            '\n  REFUSED: storage pool not writable\nError: developer mode refused the build: storage pool not '
            'writable')
        self.assertRefused(self.request(), 'developer mode: storage pool not writable',
                           FakeRunner(check=refused, check_exit=1))

    def test_declared_inputs_are_hashed_and_recorded(self):
        options = dict(self.request()['options'], flags=['--chim-regions', '@/vol/in/cells.csv'],
                       inputs=[{'path': '/vol/in/cells.csv', 'sha256': SHA, 'role': 'cells'}])
        code, result, _ = self.submit(self.request(options=options))
        self.assertEqual(code, 0, result['notes'])
        self.assertEqual(result['inputs'][0]['sha256'], SHA)
        wrong = dict(options, inputs=[{'path': '/vol/in/cells.csv', 'sha256': 'b' * 64}])
        self.assertRefused(self.request(options=wrong), 'is not the requested')

    def test_unknown_commit_and_later_kinds_are_refused(self):
        self.assertRefused(self.request(commit='fff0000'), 'is not in /src/wt')
        for kind in aw_service.NOT_YET:
            self.assertRefused(self.request(kind=kind, options={}), 'not implemented yet')

    def test_miniwind_kind_builds_the_preset_through_the_build_path(self):
        request = self.request(kind='miniwind', purpose='miniwind',
                               options={'preset': 'vivec-arena-pit', 'flags': ['--miniwind-town', 'vivec_city'],
                                        'reuse_from': '/vol/ws8/build/2026_10_10_v0.0.36-dev2_full_642c1ea'})
        code, result, runner = self.submit(request)
        self.assertEqual(code, 0, result['notes'])
        self.assertEqual(result['kind'], 'miniwind')
        self.assertRegex(result['run_name'], r'_v0\.0\.36-dev3_miniwind-vivec-arena-pit-dev3-sea-ring_abc1234$')
        build = [c for c in result['commands'] if ' --check' not in c and 'tools/build.py' in c][0]
        for part in ('--miniwind-preset vivec-arena-pit', '--miniwind-town vivec_city', '--developer-mode',
                     '--storage-pool on', '--reuse-mode pool', '--source-commit abc1234'):
            self.assertIn(part, build)
        self.assertEqual(aw.validate(result, aw.schema('aw-result-1')), [])
        line = json.loads((self.base / 'trials' / 'TRIALS.jsonl').read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual(line['result'], 'passed')

    def test_miniwind_kind_refusals(self):
        def mini(**options):
            return self.request(kind='miniwind', purpose='miniwind', options=options)
        self.assertRefused(mini(), 'options.preset')
        self.assertRefused(mini(preset='nowhere'), 'unknown MiniWind preset nowhere')
        self.assertRefused(mini(preset='balmora', flags=['--miniwind-preset', 'balmora']), 'the server sets')
        self.assertRefused(mini(preset='balmora', flags=['--miniwind-balmora']), 'the server sets')
        self.assertRefused(self.request(kind='miniwind', purpose='full', options={'preset': 'balmora'}),
                           'miniwind-<scene>')
        self.assertRefused(mini(preset='balmora', flags=['--legacy-area', 'balmora']), 'retired flag')

    def test_miniwind_request_command(self):
        args = aw.parser().parse_args(['request', '--kind', 'miniwind', '--repo', str(self.base), '--commit',
                                       'abc1234', '--purpose', 'miniwind', '--reason', 'arena', '--version',
                                       'v0.0.36-dev3', '--preset', 'vivec-arena-pit', '--flags',
                                       '--miniwind-town vivec_city', '--reuse-from', '/vol/ws8/build/r',
                                       '--requester', 'worker-b'])
        request = aw_service.make_request(args)
        self.assertEqual(aw_service.request_errors(request), [])
        self.assertEqual(request['options']['preset'], 'vivec-arena-pit')
        self.assertEqual(request['options']['flags'], ['--miniwind-town', 'vivec_city'])

    def test_request_command_writes_a_valid_request(self):
        args = aw.parser().parse_args(['request', '--kind', 'build', '--repo', str(self.base), '--commit', 'abc1234',
                                       '--purpose', 'full', '--reason', 'dev3', '--version', 'v0.0.36-dev3',
                                       '--flags', '--no-npc-gallery --extra-town bcoast_x7y2',
                                       '--reuse-from', '/vol/ws8/build/r', '--input', f'/vol/in/c.csv={SHA}=cells',
                                       '--requester', 'worker-b'])
        request = aw_service.make_request(args)
        self.assertEqual(aw_service.request_errors(request), [])
        self.assertEqual(request['options']['flags'], ['--no-npc-gallery', '--extra-town', 'bcoast_x7y2'])
        self.assertEqual(request['options']['inputs'][0]['role'], 'cells')


if __name__ == '__main__':
    unittest.main()
