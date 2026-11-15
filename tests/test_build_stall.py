"""The builder's own stall alert (tools/build_stall.py), its pass-through in the monitor reader and the Toolkit's
--on-stall hook: each state (ok, slow, under-cores, stalled), the start-up file, the runs list, one hook per incident."""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_stall  # noqa: E402
import monitor_read  # noqa: E402


class StateTests(unittest.TestCase):
    def assessor(self):
        return build_stall.Assessor(stream=io.StringIO())

    def test_ok(self):
        a = self.assessor()
        self.assertEqual(a.assess(100, 'chim', 5, 20.0, 22, 100, 300)['state'], 'ok')

    def test_slow_past_its_history(self):
        a = self.assessor()
        block = a.assess(1000, 'chim', 5, 20.0, 22, 1000, 300)
        self.assertEqual(block['state'], 'slow')
        self.assertIn('recorded 300 s', block['reason'])
        self.assertIn('[stall] slow', a.stream.getvalue())

    def test_under_half_the_planned_cores_for_five_minutes(self):
        a = self.assessor()
        for t in range(0, 300, 30):
            self.assertEqual(a.assess(t, 'start-up', 1, 1.0, 22)['state'], 'ok')
        block = a.assess(301, 'start-up', 1, 1.0, 22)
        self.assertEqual(block['state'], 'under-cores')
        self.assertIn('1.0 of 22 planned cores', block['reason'])

    def test_stalled_no_progress_and_idle(self):
        a = self.assessor()
        block = a.assess(2000, 'chim', build_stall.STALL_S + 1, 0.0, 22)
        self.assertEqual(block['state'], 'stalled')
        self.assertEqual(block['since'], 2000)

    def test_from_progress_uses_the_heartbeat_silence(self):
        a = self.assessor()
        progress = {'elapsed_seconds': 5000, 'cores_now': 0.0, 'budget': 22, 'stages': [
            {'name': 'chim', 'status': 'running', 'elapsed_seconds': 4000, 'expected_seconds': 3000,
             'heartbeat': {'silent_seconds': build_stall.STALL_S + 5}}]}
        self.assertEqual(build_stall.from_progress(a, progress)['state'], 'stalled')


class StartupAndReaderTests(unittest.TestCase):
    def test_startup_file_and_the_runs_list(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / '.startup' / 'run-a' / 'build-progress.json'
            w = build_stall.StartupWatch(path, 22, interval=0.05).start()
            try:
                print('Run name: run-a')
                time.sleep(0.3)
            finally:
                w.stop()
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'starting')
            self.assertEqual(data['budget'], 22)
            self.assertIn('stall', data)
            self.assertEqual(data['phase'], 'Run name: run-a')
            reader = monitor_read.Reader(d)
            runs = reader.runs()['runs']
            self.assertEqual([r['run'] for r in runs], ['run-a'])
            self.assertTrue(runs[0]['starting'])
            self.assertEqual(reader.progress('run-a')['progress']['status'], 'starting')

    def test_runs_carry_the_stall_block(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d) / 'run-b'
            run.mkdir()
            (run / 'build-progress.json').write_text(json.dumps(
                {'status': 'running', 'stall': {'state': 'stalled', 'since': 10, 'reason': 'x'}}),
                encoding='utf-8', newline='\n')
            runs = monitor_read.Reader(d).runs()['runs']
            self.assertEqual(runs[0]['stall']['state'], 'stalled')


class StatusFolderTests(unittest.TestCase):
    def test_writer_and_catcher(self):
        import stall_watch
        with tempfile.TemporaryDirectory() as d:
            status = Path(d) / 'run-c' / 'status'
            writer = build_stall.StatusWriter(status, resume='build again with --reuse-from run-c', make_parents=True)
            a = build_stall.Assessor(stream=io.StringIO(), on_incident=writer.incident)
            beat = {'run': 'run-c', 'status': 'running', 'stages': [{'name': 'chim', 'status': 'running'}],
                    'budget': 22, 'cores_now': 0.0, 'seconds_since_progress': 0, 'elapsed_seconds': 10,
                    'stall': a.assess(10, 'chim', 0, 20.0, 22)}
            writer.heartbeat(build_stall.heartbeat_of(beat))
            hb = json.loads((status / 'heartbeat.json').read_text(encoding='utf-8'))
            self.assertEqual(hb['format'], build_stall.STATUS_FORMAT)
            self.assertEqual((hb['phase'], hb['cores_planned'], hb['stall']['state']), ('chim', 22, 'ok'))
            self.assertEqual(list(status.glob('*.tmp*')), [])          # renamed into place
            calls, out = [], io.StringIO()
            catcher = stall_watch.Catcher(Path(d) / 'run-c', max_age=60, on_stall=['alert'], runner=calls.append,
                                          stream=out)
            self.assertEqual(catcher.check(), [])
            a.assess(2000, 'chim', build_stall.STALL_S + 1, 0.0, 22)    # an incident: one line in stall.jsonl
            found = catcher.check()
            self.assertEqual([s for s, _ in found], ['stalled'])
            self.assertEqual(calls[0][:2], ['alert', 'stalled'])
            self.assertIn('resume: build again', out.getvalue())
            self.assertEqual(catcher.check(), [])                       # once per incident
            catcher.clock = lambda: time.time() + 600                   # the heartbeat goes stale: the builder is stuck
            self.assertEqual([s for s, _ in catcher.check()], ['no-heartbeat'])
            # a fresh catcher reads the incident already in stall.jsonl
            self.assertEqual(stall_watch.main([str(Path(d) / 'run-c'), '--once', '--max-age', '100000']),
                             stall_watch.STALL_EXIT)
            (status / 'stall.jsonl').unlink()
            self.assertEqual(stall_watch.main([str(Path(d) / 'run-c'), '--once', '--max-age', '100000']), 0)

    def test_catcher_exits_on_stall(self):
        import stall_watch
        with tempfile.TemporaryDirectory() as d:
            w = build_stall.StatusWriter(Path(d) / 'status')
            w.heartbeat({'status': 'running'})
            w.incident('chim', {'state': 'stalled', 'since': 1, 'reason': 'x'})
            self.assertEqual(stall_watch.main([d, '--exit-on-stall', '--interval', '0.01']), stall_watch.STALL_EXIT)


class HookTests(unittest.TestCase):
    def test_one_call_per_incident(self):
        import toolkit_serve

        class Builds:
            def __init__(self):
                self.state = 'ok'

            def ask(self, request):
                return {'ok': True, 'runs': [{'run': 'r', 'stall': {'state': self.state, 'since': 5, 'reason': 'why'}}]}

        calls = []
        builds = Builds()
        hook = toolkit_serve.StallHook(builds, ['alert'], runner=calls.append)
        hook.check()
        builds.state = 'stalled'
        hook.check()
        hook.check()
        self.assertEqual(calls, [['alert', 'r', 'stalled', 'why']])


if __name__ == '__main__':
    unittest.main()
