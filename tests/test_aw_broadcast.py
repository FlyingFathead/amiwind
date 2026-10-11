# SPDX-License-Identifier: GPL-3.0-only
"""The master builder's broadcast (tools/aw_broadcast.py): the message form, calls for fixes reaching every lease
holder, build holds (builds refused, gates allowed), replies and the merge queue line, publish only after a passed
gate (checked by the SHA-256 of its result file), the new-builder message, and the stale-base refusal that a
deferral with a reason lifts. git and docker are replaced by fakes: nothing here runs a container."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import aw  # noqa: E402
import aw_broadcast  # noqa: E402
import aw_service  # noqa: E402
from test_aw_service import FakeRunner  # noqa: E402

A, B, C, D, E = ('a' * 40, 'b' * 40, 'c' * 40, 'd' * 40, 'e' * 40)
VERSION = '0.0.36-dev3'

FAKE_GATE = '''
import os, sys
from pathlib import Path
n, out = sys.argv[1], Path(sys.argv[2])
files = {
    'repo': 'gate %s repo %s head %s dirty 0' % (n, os.environ['REPO'], os.environ['FAKE_HEAD']),
    'preflight': 'preflight-exit=0\\nok',
    'suite': 'suite-exit=0\\n{"started": "a", "tests_run": 5, "failures": 0, "errors": 0, "successful": true}',
    'hostparity': 'host-parity-linux-exit=0\\nhost-parity-windows-exit=0',
    'engine': 'engine-exit=0\\n0',
    'smoke': 'smoke-exit=0\\nPASS',
}
for name, text in files.items():
    (out / ('par-%s-%s.out' % (n, name))).write_text(text + '\\n')
'''


def norm(path):
    return os.path.normcase(os.path.abspath(str(path))).replace('\\', '/')


class FakeRepo:
    """A small commit graph shared by every worktree: A <- B (the builder fix) <- D; A <- C; A <- E (unrelated)."""

    def __init__(self):
        self.ancestors = {A: {A}, B: {A, B}, C: {A, C}, D: {A, B, D}, E: {A, E}}
        self.refs = {'integration/latest': A}
        self.heads = {}

    def resolve(self, repo, rev):
        rev = rev[:-len('^{commit}')] if rev.endswith('^{commit}') else rev
        if rev == 'HEAD':
            return self.heads.get(norm(repo))
        rev = rev[len('refs/heads/'):] if rev.startswith('refs/heads/') else rev
        if rev in self.refs:
            return self.refs[rev]
        matches = [full for full in self.ancestors if len(rev) >= 4 and full.startswith(rev.lower())]
        return matches[0] if len(matches) == 1 else None

    def git(self, repo, *args):
        if args[:1] == ('status',):
            return ''
        if args[:1] == ('rev-parse',):
            return self.resolve(repo, args[-1])
        if args[:1] == ('show',):
            return VERSION + '\n' if args[1].split(':')[0] in self.ancestors else None
        if args[:1] == ('update-ref',):
            ref, new, old = args[3][len('refs/heads/'):], args[4], args[5]
            if self.refs.get(ref, '0' * 40) != old:
                return None
            self.refs[ref] = new
            return ''
        return None

    def short(self, repo, rev='HEAD'):
        full = self.resolve(repo, rev)
        return full[:7] if full else None

    def is_ancestor(self, repo, commit, rev='HEAD'):
        one, two = self.resolve(repo, commit), self.resolve(repo, rev)
        if not one or not two:
            return None
        return one in self.ancestors[two]

    def patch(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(aw, 'git', self.git))
        stack.enter_context(mock.patch.object(aw, 'git_short', self.short))
        stack.enter_context(mock.patch.object(aw, 'is_ancestor', self.is_ancestor))
        return stack


class PoolRunner:
    """Stands in for the container that writes the working-version copies; answers with the bytes' SHA-256."""

    def __init__(self, wrong=False):
        self.calls, self.wrong = [], wrong

    def __call__(self, command, data):
        self.calls.append((command, data))
        digest = '0' * 64 if self.wrong else hashlib.sha256(data).hexdigest()
        return 0, f'{digest}  {command[-1]}\n'


def quiet(function, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
        value = function(*args, **kwargs)
    return value, out.getvalue() + err.getvalue()


class BroadcastBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.repo = FakeRepo()
        stack = self.repo.patch()
        stack.__enter__()
        self.addCleanup(stack.close)
        self.worktrees = {}
        for job, head in (('coordinator', B), ('worker-a', C), ('worker-b', D)):
            path = self.base / job
            path.mkdir()
            (path / 'VERSION').write_text(VERSION + '\n', encoding='utf-8')
            self.repo.heads[norm(path)] = head
            self.worktrees[job] = path
        (self.base / 'gate').mkdir()
        (self.base / 'fake_gate.py').write_text(FAKE_GATE, encoding='utf-8')
        (self.base / 'WORKING_VERSION.json').write_text(json.dumps({'working_version': VERSION, 'head': 'aaaaaaa',
                                                                     'line': 'v0.0.36-dev'}) + '\n', encoding='utf-8')
        (self.base / 'integration-head.txt').write_text(
            'PUBLISHED (aw gate 1 PASSED): aaaaaaa  branch integration/latest (VERSION 0.0.36-dev3)\n'
            'CONTAINS: the start.\n', encoding='utf-8')
        config = {'schema': 'aw-config-1', 'state_dir': 'state', 'working_version_file': 'WORKING_VERSION.json',
                  'integration_ref': 'integration/latest', 'integration_head_file': 'integration-head.txt',
                  'gate': {'out_dir': 'gate', 'ranges': {'t': [10, 40]}, 'default_range': 't',
                           'command': [sys.executable, str(self.base / 'fake_gate.py'), '{number}',
                                       str(self.base / 'gate')]},
                  'build': {'image': 'builder:test', 'volume': 'pool-vol', 'inputs_volume': 'game-vol',
                            'workspace': '/vol/ws8', 'cpus': 24, 'memory': '44g', 'jobs': 24},
                  'broadcast': {'merge_queue_file': 'merge-queue.md', 'reply_within_min': 30,
                                'pool_working_version_files': ['/vol/WORKING_VERSION.json',
                                                               '/vol/ws8/cache/WORKING_VERSION.json']}}
        self.config_path = self.base / 'aw-config.json'
        self.config_path.write_text(json.dumps(config), encoding='utf-8')
        self.config = aw.load_config(self.config_path)
        for job, path in self.worktrees.items():
            aw.lease_worktree(self.config, str(path), job, purpose='job')

    def gate(self, job, *extra):
        os.environ['FAKE_HEAD'] = self.repo.heads[norm(self.worktrees[job])][:7]
        self.addCleanup(os.environ.pop, 'FAKE_HEAD', None)
        code, text = quiet(aw.main, ['--config', str(self.config_path), 'gate', '--repo', str(self.worktrees[job]),
                                     '--reason', 'unit test', '--requester', job, '--quiet', *extra])
        results = sorted((Path(self.config['state_dir']) / 'results').glob('*.json'), key=os.path.getmtime)
        return code, json.loads(results[-1].read_text(encoding='utf-8')), text

    def cli(self, *argv, requester='coordinator'):
        who = [] if argv[0] == 'status' else ['--requester', requester]
        return quiet(aw.main, ['--config', str(self.config_path), *argv, *who])

    def publish(self, **kwargs):
        runner = kwargs.pop('runner', PoolRunner())
        document = aw_broadcast.publish(self.config, kwargs.pop('commit', 'bbbbbbb'),
                                        kwargs.pop('contains', 'fixes BUG-ONE-36 (the late heap check)'),
                                        'coordinator', repo=self.worktrees['coordinator'], runner=runner, **kwargs)
        return document, runner

    def build_request(self, job, **change):
        request = {'schema': 'aw-request-1', 'id': f'req-{job}', 'kind': 'build', 'repo': str(self.worktrees[job]),
                   'commit': self.repo.heads[norm(self.worktrees[job])][:7], 'purpose': 'full',
                   'version': 'v' + VERSION, 'reason': 'unit test', 'requester': job,
                   'time': '2026-10-10 22:00:00 +0300', 'options': {'flags': ['--no-npc-gallery']}}
        request.update(change)
        (code, path), _ = quiet(aw_service.submit, self.config, request, dry_run=True, runner=FakeRunner())
        result = json.loads(Path(path).read_text(encoding='utf-8')) if path else None
        return code, result


class MessageSchemaTests(unittest.TestCase):
    def message(self, **change):
        doc = {'schema': 'aw-message-1', 'id': 'msg-1', 'kind': 'builder-bug', 'time': '2026-10-10 22:00:00 +0300',
               'version': 'v0.0.36-dev3', 'integration_head': '7255e43', 'ids': ['BUILD-CHIM-HEAP-GATE-LATE-36'],
               'summary': 'the heap gate runs after the image step', 'hold': True,
               'reply_by': '2026-10-10 22:30:00 +0300', 'from': 'coordinator'}
        doc.update(change)
        return doc

    def test_schema_file_and_examples(self):
        data = aw.schema('aw-message-1')
        self.assertEqual((data['$id'], data['properties']['schema']['const']), ('aw-message-1', 'aw-message-1'))
        self.assertEqual(aw.validate(self.message(), data), [])
        self.assertEqual(aw.validate(self.message(kind='new-builder', reply_by=None, commit='bbbbbbb',
                                                  closes=['msg-1'], to='worker-a'), data), [])

    def test_bad_messages_are_refused(self):
        data = aw.schema('aw-message-1')
        self.assertTrue(aw.validate(self.message(kind='chat'), data))
        self.assertTrue(aw.validate(self.message(id='call-1'), data))
        self.assertTrue(aw.validate(self.message(ids=['lower-case-id']), data))
        self.assertTrue(aw.validate(self.message(time='2026-10-10T22:00'), data))
        self.assertTrue(aw.validate(self.message(extra=1), data))
        missing = self.message()
        del missing['hold']
        self.assertTrue(aw.validate(missing, data))

    def test_request_override_knows_build_hold(self):
        allow = aw.schema('aw-request-1')['properties']['override']['properties']['allow']['items']['enum']
        self.assertIn('build-hold', allow)
        self.assertIn('build-hold', aw_service.OVERRIDES)


class AnnounceTests(BroadcastBase):
    def test_announce_reaches_every_holder_but_the_sender(self):
        entry = aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36,BUG-TWO-36', 'the heap gate runs late',
                                      True, 'coordinator')
        message = entry['message']
        self.assertEqual(sorted(entry['recipients']), ['worker-a', 'worker-b'])
        self.assertEqual((message['ids'], message['hold'], message['version'], message['integration_head']),
                         (['BUG-ONE-36', 'BUG-TWO-36'], True, 'v' + VERSION, 'aaaaaaa'))
        self.assertRegex(message['reply_by'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$')
        for job in ('worker-a', 'worker-b'):
            path = Path(self.config['state_dir']) / 'inbox' / job / f'{message["id"]}.json'
            doc = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(aw.validate(doc, aw.schema('aw-message-1')), [])
            self.assertEqual(doc['to'], job)
        self.assertFalse((Path(self.config['state_dir']) / 'inbox' / 'coordinator').exists())
        events = [json.loads(line)['event'] for line in aw.trial_log_path(self.config).read_text().splitlines()]
        self.assertIn('announce', events)

    def test_inbox_shows_unread_once(self):
        aw_broadcast.announce(self.config, 'builder-update', 'BUG-ONE-36', 'new reuse keys', False, 'coordinator')
        found, holds = aw_broadcast.inbox(self.config, 'worker-a')
        self.assertEqual(([item['message']['id'] for item in found], holds), (['msg-1'], []))
        self.assertEqual(aw_broadcast.inbox(self.config, 'worker-a')[0], [], 'read messages are not shown again')
        self.assertEqual(len(aw_broadcast.inbox(self.config, 'worker-a', show_all=True)[0]), 1)
        self.assertEqual(aw_broadcast.inbox(self.config, 'nobody')[0], [])

    def test_bad_ids_and_empty_summary_are_refused(self):
        with self.assertRaises(aw.AwError):
            aw_broadcast.announce(self.config, 'builder-bug', 'not-an-id', 'x', False, 'coordinator')
        with self.assertRaises(aw.AwError):
            aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', '  ', False, 'coordinator')

    def test_cli_announce_inbox_reply(self):
        code, text = self.cli('announce', '--kind', 'builder-bug', '--ids', 'BUG-ONE-36', '--summary', 'late check',
                              '--hold')
        self.assertEqual(code, 0, text)
        self.assertIn('worker-a, worker-b', text)
        code, text = self.cli('inbox', requester='worker-a')
        self.assertEqual(code, 0, text)
        self.assertIn('msg-1', text)
        self.assertIn('BUILD HOLD', text)
        code, text = self.cli('reply', 'msg-1', '--none', requester='worker-a')
        self.assertEqual(code, 0, text)
        code, text = self.cli('reply', 'msg-9', '--none', requester='worker-a')
        self.assertEqual(code, 2, text)
        code, text = self.cli('status')
        self.assertEqual(code, 0, text)
        self.assertIn('BUILD HOLD by msg-1', text)
        self.assertIn('not answered: worker-b', text)


class HoldTests(BroadcastBase):
    def test_hold_refuses_build_but_not_gate(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', True, 'coordinator')
        code, result = self.build_request('worker-b')
        self.assertEqual(code, 2)
        self.assertTrue(any(text.startswith('BUILD HOLD: call msg-1') for text in result['refusals']), result)
        code, result, text = self.gate('worker-b')
        self.assertEqual((code, result['status']), (0, 'passed'), text)

    def test_hold_override_with_reason(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', True, 'coordinator')
        code, result = self.build_request('worker-b', override={'reason': 'release build, owner exception',
                                                                'allow': ['build-hold']})
        self.assertFalse(any('BUILD HOLD' in text for text in result.get('refusals') or []), result)
        self.assertTrue(any(note.startswith('override (build-hold)') for note in result['notes']), result)

    def test_no_hold_no_refusal(self):
        aw_broadcast.announce(self.config, 'builder-update', 'BUG-ONE-36', 'new keys', False, 'coordinator')
        self.assertEqual(aw_broadcast.hold_refusals(self.config), [])


class ReplyTests(BroadcastBase):
    def test_replies_are_recorded_and_queued(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', True, 'coordinator')
        aw_broadcast.reply(self.config, 'msg-1', 'worker-a', 'none')
        aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'proposal', 'run the heap gate before the image step')
        info = aw_broadcast.summary(self.config)
        call = info['open_calls'][0]
        self.assertEqual((call['answered'], call['unanswered']),
                         ({'worker-a': 'none', 'worker-b': 'proposal'}, []))
        data = (self.base / 'merge-queue.md').read_bytes()
        self.assertNotIn(b'\r', data)
        lines = data.decode('utf-8').splitlines()
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r'^\| \d{4}-\d{2}-\d{2} \d{2}:\d{2} [+-]\d{4} \[v0\.0\.36-dev3\] \| AW REPLY '
                                   r'\(worker-a\) \| msg-1 builder-bug BUG-ONE-36: no fix or proposal')
        self.assertIn('PROPOSAL: run the heap gate before the image step', lines[1])

    def test_commit_reply_must_resolve(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', False, 'coordinator')
        repo = str(self.worktrees['worker-b'])
        _, answer, _ = aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'commit', '', f'{repo}:ddddddd')
        self.assertEqual(answer['commit'], f'{repo}:{D[:12]}')
        with self.assertRaises(aw.AwError):
            aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'commit', '', f'{repo}:0123456')
        with self.assertRaises(aw.AwError):
            aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'commit', '', 'no-colon')
        with self.assertRaises(aw.AwError):
            aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'proposal', '')

    def test_late_reply_from_a_worker_without_lease(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', False, 'coordinator')
        aw_broadcast.reply(self.config, 'msg-1', 'worker-z', 'none')
        record = aw_broadcast.load_register(self.config)['messages'][0]['recipients']['worker-z']
        self.assertTrue(record['late'])


class PublishTests(BroadcastBase):
    def test_publish_refuses_an_ungated_commit(self):
        with self.assertRaisesRegex(aw.AwError, 'no passed gate of bbbbbbb'):
            self.publish()
        self.assertEqual(self.repo.refs['integration/latest'], A, 'nothing moved')

    def test_publish_refuses_a_changed_result_file(self):
        code, result, text = self.gate('coordinator')
        self.assertEqual(code, 0, text)
        path = Path(result['artifacts'][-1])
        path.write_text(path.read_text(encoding='utf-8').replace('"tests_run": 5', '"tests_run": 6'),
                        encoding='utf-8')
        with self.assertRaisesRegex(aw.AwError, 'the result file changed'):
            self.publish()
        self.assertEqual(self.repo.refs['integration/latest'], A)

    def test_publish_refuses_a_dirty_gate_and_a_given_hash_that_does_not_match(self):
        code, result, text = self.gate('coordinator')
        self.assertEqual(code, 0, text)
        path = result['artifacts'][-1]
        with self.assertRaisesRegex(aw.AwError, 'not the recorded'):
            self.publish(gate_result=path, gate_sha='f' * 64)
        document = json.loads(Path(path).read_text(encoding='utf-8'))
        document['notes'] = ['1 uncommitted/untracked paths (allowed: the result is NOT a clean abc gate)']
        aw.write_json(path, document)
        with self.assertRaisesRegex(aw.AwError, 'uncommitted'):
            self.publish(gate_result=path, gate_sha=aw.file_sha256(path))

    def test_publish_moves_the_head_and_posts_the_new_builder(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', True, 'coordinator')
        code, result, text = self.gate('coordinator')
        self.assertEqual(code, 0, text)
        document, runner = self.publish()
        self.assertEqual((document['status'], document['head'], document['closed'], document['holds_left']),
                         ('passed', 'bbbbbbb', ['msg-1'], []))
        self.assertEqual(document['gate']['sha256'], aw.file_sha256(result['artifacts'][-1]))
        self.assertEqual(self.repo.refs['integration/latest'], B)
        published = aw_service.published_integration(self.config)
        self.assertEqual(published['head'], 'bbbbbbb')
        self.assertIn('CONTAINS: fixes BUG-ONE-36', published['contains'][0])
        self.assertIn('aaaaaaa', (self.base / 'integration-head.txt').read_text(), 'older entries are kept')
        record_bytes = (self.base / 'WORKING_VERSION.json').read_bytes()
        record = json.loads(record_bytes)
        self.assertEqual((record['head'], record['working_version'], record['line']),
                         ('bbbbbbb', VERSION, 'v0.0.36-dev'))
        self.assertEqual([command[-1] for command, _ in runner.calls],
                         ['/vol/WORKING_VERSION.json', '/vol/ws8/cache/WORKING_VERSION.json'])
        for command, data in runner.calls:
            self.assertEqual(data, record_bytes)
            for flag in (['--pull', 'never'], ['--network', 'none'], ['--user', '1000:1000']):
                self.assertIn(command[command.index(flag[0]) + 1], flag[1:])
            self.assertIn('--name', command)
        self.assertEqual(aw_broadcast.hold_refusals(self.config), [], 'the hold is lifted')
        for job in ('worker-a', 'worker-b'):
            found, _ = aw_broadcast.inbox(self.config, job)
            new = [item['message'] for item in found if item['message']['kind'] == 'new-builder']
            self.assertEqual(len(new), 1, job)
            self.assertEqual((new[0]['commit'], new[0]['closes'], new[0]['hold_level']), ('bbbbbbb', ['msg-1'], True))
            self.assertIn("well, here is the new version", new[0]['text'])
            self.assertIn('aw reply msg-2 --defer', new[0]['text'])

    def test_publish_lists_proposals_and_keeps_unfixed_calls_open(self):
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-ONE-36', 'late heap check', True, 'coordinator')
        aw_broadcast.announce(self.config, 'builder-bug', 'BUG-TWO-36', 'stair walk uncached', True, 'coordinator')
        aw_broadcast.reply(self.config, 'msg-1', 'worker-b', 'proposal', 'move the check first')
        self.gate('coordinator')
        document, _ = self.publish(fixes='BUG-ONE-36', contains='the heap check runs first')
        self.assertEqual((document['closed'], document['holds_left']), (['msg-1'], ['msg-2']))
        self.assertEqual(document['proposals'], ['worker-b: move the check first'])
        message = aw_broadcast.load_register(self.config)['messages'][-1]['message']
        self.assertIn('Proposals received: worker-b: move the check first', message['text'])
        self.assertIn('BUILD HOLD still in force for: msg-2', message['text'])
        self.assertTrue(message['hold'])
        self.assertTrue(aw_broadcast.hold_refusals(self.config))

    def test_publish_refuses_a_commit_that_does_not_contain_the_head(self):
        self.repo.heads[norm(self.worktrees['coordinator'])] = E
        self.repo.refs['integration/latest'] = B
        (self.base / 'integration-head.txt').write_text('PUBLISHED (aw gate 2 PASSED): bbbbbbb  x\nCONTAINS: y\n')
        self.repo.ancestors[E] = {A, E}
        os.environ['FAKE_HEAD'] = 'eeeeeee'
        self.addCleanup(os.environ.pop, 'FAKE_HEAD', None)
        # E lacks B, so its gate is refused as stale; give publish a passed gate record directly
        results = Path(self.config['state_dir']) / 'results'
        results.mkdir(parents=True, exist_ok=True)
        path = results / 'gate.json'
        aw.write_json(path, {'schema': 'aw-result-1', 'request_id': 'r', 'kind': 'gate', 'status': 'passed',
                             'version': 'v' + VERSION, 'commit': 'eeeeeee', 'head': 'eeeeeee',
                             'run_name': '2026_10_10_v0.0.36-dev3_gate-9_eeeeeee', 'time': aw.stamp(),
                             'started': aw.stamp(), 'finished': aw.stamp(), 'seconds': 1,
                             'numbers': {'tests_run': 5, 'failures': 0, 'errors': 0, 'engine_warnings': 0},
                             'steps': {}, 'failed_steps': [], 'failures': [], 'artifacts': [], 'logs': [],
                             'timings': {}, 'reuse': {'applicable': False}, 'leases': []})
        with self.assertRaisesRegex(aw.AwError, 'only moves forward'):
            self.publish(commit='eeeeeee', gate_result=str(path), gate_sha=aw.file_sha256(path))

    def test_publishers_list(self):
        self.config['broadcast']['publishers'] = ['coordinator']
        with self.assertRaisesRegex(aw.AwError, 'may not publish'):
            aw_broadcast.publish(self.config, 'bbbbbbb', 'x', 'worker-a', repo=self.worktrees['coordinator'])

    def test_pool_copy_mismatch_reports_failed(self):
        self.gate('coordinator')
        document, _ = self.publish(runner=PoolRunner(wrong=True))
        self.assertEqual(document['status'], 'failed')
        self.assertIn('aw sync-version', ' '.join(document['notes']))
        digest, results = aw_broadcast.sync_version(self.config, runner=PoolRunner())
        self.assertEqual(digest, aw.file_sha256(self.base / 'WORKING_VERSION.json'))
        self.assertTrue(all(item['ok'] for item in results))


class StaleBaseTests(BroadcastBase):
    def published(self, hold_level=False):
        self.gate('coordinator')
        document, _ = self.publish(contains='a builder update', hold_level=hold_level)
        return document['message']

    def test_stale_base_is_refused_until_the_worker_defers(self):
        msg = self.published()
        code, result, text = self.gate('worker-a')
        self.assertEqual(code, 2, text)
        self.assertTrue(any(note.startswith('STALE BUILDER') and f'aw reply {msg} --defer' in note
                            for note in result['notes']), result['notes'])
        aw_broadcast.reply(self.config, msg, 'worker-a', 'defer', 'mid soak test; merging after it, about 23:30')
        code, result, text = self.gate('worker-a')
        self.assertEqual((code, result['status']), (0, 'passed'), text)
        self.assertTrue(any('deferred by worker-a' in note and 'about 23:30' in note for note in result['notes']))
        code, result = self.build_request('worker-a')
        self.assertNotIn('STALE', ' '.join(result.get('refusals') or []), result)
        code, result, text = self.gate('worker-b')
        self.assertEqual(code, 0, text)

    def test_hold_level_fix_refuses_builds_even_when_deferred(self):
        msg = self.published(hold_level=True)
        aw_broadcast.reply(self.config, msg, 'worker-a', 'defer', 'mid soak test; after it')
        code, result, text = self.gate('worker-a')
        self.assertEqual(code, 0, text)
        code, result = self.build_request('worker-a')
        self.assertEqual(code, 2)
        self.assertIn('hold-level builder fix', ' '.join(result['refusals']))

    def test_status_shows_each_holder(self):
        msg = self.published()
        aw_broadcast.reply(self.config, msg, 'worker-a', 'defer', 'after the soak')
        holders = aw_broadcast.summary(self.config)['new_builder']['holders']
        self.assertEqual(holders, {'worker-a': 'deferred: after the soak', 'worker-b': 'merged'})

    def test_merged_reply_must_contain_the_new_builder(self):
        msg = self.published()
        with self.assertRaisesRegex(aw.AwError, 'does not contain the new builder'):
            aw_broadcast.reply(self.config, msg, 'worker-a', 'commit', '', f'{self.worktrees["worker-a"]}:ccccccc')
        aw_broadcast.reply(self.config, msg, 'worker-b', 'commit', '', f'{self.worktrees["worker-b"]}:ddddddd')

    def test_gates_join_the_address_list(self):
        aw.release(self.config, next(lease['id'] for lease in aw.list_leases(self.config)
                                     if lease['requester'] == 'worker-b'), 'worker-b')
        self.assertNotIn('worker-b', aw_broadcast.holders(self.config))
        self.gate('worker-b')
        self.assertIn('worker-b', aw_broadcast.holders(self.config))


if __name__ == '__main__':
    unittest.main()
