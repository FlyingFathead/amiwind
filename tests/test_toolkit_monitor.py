# SPDX-License-Identifier: GPL-3.0-only
"""The AmiWind Toolkit Monitor: read-only build monitoring (tools/monitor_read.py, tools/toolkit_serve.py /monitor/,
amiwind-toolkit/monitor.html). Sample run folders only; DOM stubbed in the page check (no browser claim)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import monitor_read  # noqa: E402
import toolkit_serve  # noqa: E402

RUN = '2026_10_10_v0.0.36-dev3_full-sample_abc1234'


def sample_run(builds, run=RUN, status='running'):
    d = Path(builds) / run
    (d / 'logs').mkdir(parents=True)
    (d / 'build-progress.json').write_text(json.dumps({
        'schema': 'amiwind-build-progress-v1', 'run': run, 'status': status, 'updated_at': '2026-10-10T20:38:38+00:00',
        'updated_epoch': 1791664718.8, 'elapsed_seconds': 3459.2, 'budget': 24, 'percent': 19.0, 'eta_seconds': 16916.2,
        'eta_basis': 'critical path', 'eta_at': '2026-10-11T01:20:35+00:00', 'critical_path': ['chim', 'image'],
        'counts': {'passed': 2, 'running': 1, 'pending': 1, 'failed': 0, 'total': 4}, 'cores_now': 23.2,
        'stages': [{'name': 'setup', 'status': 'passed', 'expected_seconds': 5, 'elapsed_seconds': 0.2},
                   {'name': 'bsp', 'status': 'passed', 'expected_seconds': 24, 'elapsed_seconds': 16.7},
                   {'name': 'chim', 'status': 'running', 'expected_seconds': 6000, 'elapsed_seconds': 3300},
                   {'name': 'image', 'status': 'pending', 'expected_seconds': 900}]}), encoding='utf-8')
    (d / 'build-state.json').write_text(json.dumps({
        'schema': 'amiwind-build-receipt-v1', 'status': status, 'input_sha256': {'x%d' % i: 'a' * 64 for i in range(500)},
        'steps': [{'name': 'setup', 'status': 'passed', 'log': '/vol/ws8/build/%s/logs/01-setup.log' % run,
                   'command': ['python3', 'secret-arg'], 'started_seconds': 0.1, 'elapsed_seconds': 0.2, 'returncode': 0},
                  {'name': 'bsp', 'status': 'passed', 'started_seconds': 1.0, 'elapsed_seconds': 16.7, 'jobs': 12},
                  {'name': 'npcs', 'status': 'passed', 'started_seconds': 1.0, 'elapsed_seconds': 12.0, 'jobs': 1},
                  {'name': 'chim', 'status': 'running', 'started_seconds': 20.0, 'jobs': 8}]}), encoding='utf-8')
    (d / 'logs' / '01-setup.log').write_bytes(b'setup done\n')
    (d / 'profile' / 'reads').mkdir(parents=True)
    (d / 'profile' / 'reads' / '32-chim.txt').write_bytes(b'<tools/chim/heap.py\n@tools/chim/heap.py\tring_peak\n>chim-world/chim-heap.json\n')
    (d / 'logs' / '32-chim.log').write_bytes(''.join('CHIM stair gate: frames/x+%02d/y+00/frame.ccf: %d steps\n' % (i, i)
                                                     for i in range(2000)).encode())
    return d


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.builds = self.tmp / 'build'
        self.run_dir = sample_run(self.builds)
        (self.builds / 'not-a-run').mkdir()
        (self.tmp / 'secret.log').write_bytes(b'outside\n')
        self.r = monitor_read.Reader(self.builds)

    def test_runs_files_progress_state(self):
        self.assertEqual([r['run'] for r in self.r.runs()['runs']], [RUN])
        self.assertEqual([f['name'] for f in self.r.files(RUN)['logs']], ['01-setup.log', '32-chim.log'])
        self.assertEqual(self.r.progress(RUN)['progress']['counts']['total'], 4)
        state = self.r.state(RUN)['state']
        self.assertEqual(state['steps'][0], {'name': 'setup', 'status': 'passed', 'jobs': None, 'started_seconds': 0.1,
                                             'elapsed_seconds': 0.2, 'returncode': 0, 'log': '01-setup.log'})
        self.assertNotIn('input_sha256', state)             # a summary, not the whole receipt
        self.assertNotIn('secret-arg', json.dumps(state))

    def test_log_ranges(self):
        size = (self.run_dir / 'logs' / '32-chim.log').stat().st_size
        tail = self.r.log(RUN, '32-chim.log', -1, 100)
        self.assertEqual((tail['offset'], tail['next'], tail['size']), (size - 100, size, size))
        head = self.r.log(RUN, '32-chim.log', 0, 50)
        self.assertEqual((head['offset'], head['next']), (0, 50))
        more = self.r.log(RUN, '32-chim.log', head['next'], 50)
        self.assertEqual(more['offset'], 50)
        self.assertEqual(head['text'] + more['text'], (self.run_dir / 'logs' / '32-chim.log').read_bytes()[:100].decode())
        self.assertEqual(self.r.log(RUN, '32-chim.log', size + 99, 50)['text'], '')       # past the end: nothing yet
        big = self.r.log(RUN, '32-chim.log', 0, 10 ** 9)
        self.assertLessEqual(len(big['text'].encode()), monitor_read.MAX_READ)

    def test_stage_trace(self):
        self.assertEqual([t['name'] for t in self.r.files(RUN)['traces']], ['32-chim.txt'])
        t = self.r.answer({'op': 'trace', 'run': RUN, 'name': '32-chim.txt', 'offset': 0})
        self.assertTrue(t['ok'])
        self.assertIn('@tools/chim/heap.py\tring_peak', t['text'])
        for name in ('../../logs/01-setup.log', '01-setup.log', '../reads/32-chim.txt', 'x/32-chim.txt'):
            self.assertFalse(self.r.answer({'op': 'trace', 'run': RUN, 'name': name})['ok'], name)

    def test_sections_from_the_profile_and_derived_from_the_trace(self):
        import os as _os
        d = self.run_dir
        epoch = 1791660000.0
        prog = json.loads((d / 'build-progress.json').read_text(encoding='utf-8'))
        prog['started_at'] = '2026-10-10T19:20:00+00:00'
        (d / 'build-progress.json').write_bytes(json.dumps(prog).encode())
        epoch = monitor_read.Reader(self.builds)._build_epoch(d, None)
        # the profile: bsp has a section timer; chim has none (sections come from its trace)
        series = [[t, 1.0] for t in range(20, 140)] + [[t, 12.0] for t in range(140, 200)]
        (d / 'build-profile.json').write_bytes(json.dumps({'stages': [
            {'name': 'bsp', 'start': 1.0, 'end': 17.7, 'sections': [
                {'name': 'exec qbsp', 'start': 1.5, 'wall': 6.0, 'cores_avg': 1.4, 'calls': 2, 'min_depth': 0},
                {'name': 'exec vis', 'start': 7.6, 'wall': 4.0, 'cores_avg': 14.4, 'calls': 1, 'min_depth': 0}]},
            {'name': 'chim', 'start': 20.0, 'end': 200.0}],
            'timeline': {'t': [], 'cores': [], 'stages': {'chim': series}}}).encode())
        out = d / 'chim-world' / 'frames'
        out.mkdir(parents=True)
        lines = ['@tools/chim/frame_map.py\tbuild_region']
        for k in range(30):
            f = out / ('vf%04d.chim' % k)
            f.write_bytes(b'x')
            _os.utime(f, (epoch + 25 + 3 * k, epoch + 25 + 3 * k))
            lines.append('>chim-world/frames/vf%04d.chim' % k)
            if k == 10:                         # an import inside the write-heavy stretch is not work
                lines.append('@tools/check_actor_ground.py\t<module>')
                lines.append('@tools/build_parallel.py\t_pool_worker_init')
        trace = d / 'profile' / 'reads' / '32-chim.txt'
        trace.write_bytes(('\n'.join(lines) + '\n').encode())
        _os.utime(trace, (epoch + 200, epoch + 200))
        a = self.r.answer({'op': 'sections', 'run': RUN, 'stage': '05-bsp'})
        self.assertEqual(a['source'], 'profile')
        self.assertEqual([s['name'] for s in a['sections']], ['exec qbsp', 'exec vis'])
        b = self.r.answer({'op': 'sections', 'run': RUN, 'stage': '32-chim'})
        self.assertTrue(b['ok'], b)
        self.assertEqual(b['source'], 'trace')
        self.assertIn('approximate', b['note'])
        names = ' '.join(s['name'] for s in b['sections'])
        self.assertIn('vf*.chim x30', names)                      # named by what it wrote
        self.assertNotIn('check_actor_ground', names)            # the import is not what ran
        self.assertNotIn('_pool_worker_init', names)
        low = [s for s in b['sections'] if s.get('low_run') or (s['cores'] is not None and s['cores'] < 4 and s['end'] - s['start'] > 60)]
        self.assertTrue(low, b['sections'])
        self.assertTrue(all(s['start'] >= 20 for s in b['sections']))
        for bad in ('../32-chim', '32-chim/../x', 'chim', '32-chim.txt'):
            self.assertFalse(self.r.answer({'op': 'sections', 'run': RUN, 'stage': bad})['ok'], bad)

    def test_traversal_and_bad_names_are_refused(self):
        for run, name in ((RUN, '../build-progress.json'), (RUN, '..'), (RUN, 'x/../../secret.log'), ('..', 'secret.log'),
                          ('../' + RUN, '01-setup.log'), (RUN, '01-setup.txt'), (RUN, '/etc/passwd'), (RUN, 'a\\b.log'),
                          ('x;rm -rf ~', '01-setup.log'), (RUN, '$(id).log'), ('', '01-setup.log')):
            with self.assertRaises(monitor_read.Refused, msg=(run, name)):
                self.r.log(run, name)
        for op in ('progress', 'state', 'timeline', 'files'):
            self.assertFalse(self.r.answer({'op': op, 'run': '../build'})['ok'])
        self.assertFalse(self.r.answer({'op': 'shell', 'cmd': 'id'})['ok'])
        self.assertFalse(self.r.answer(['op'])['ok'])

    @unittest.skipIf(os.name == 'nt', 'symbolic links need privileges on Windows')
    def test_symbolic_links_are_not_followed(self):
        os.symlink(self.tmp / 'secret.log', self.run_dir / 'logs' / '99-link.log')
        with self.assertRaises(monitor_read.Refused):
            self.r.log(RUN, '99-link.log')
        self.assertNotIn('99-link.log', [f['name'] for f in self.r.files(RUN)['logs']])

    def test_timeline_is_downsampled(self):
        n = 5000
        (self.run_dir / 'build-profile.json').write_text(json.dumps({
            'status': 'passed', 'wall_seconds': n, 'budget': 24, 'host_cpus': 24,
            'stages': [{'name': 'chim', 'status': 'passed', 'start': 10, 'end': 4000, 'wall': 3990, 'cores_avg': 3.1}],
            'timeline': {'t': list(range(n)), 'cores': [1.0] * n}}), encoding='utf-8')
        t = self.r.timeline(RUN)['timeline']
        self.assertLessEqual(len(t['cores']), 2 * monitor_read.TIMELINE_POINTS)
        self.assertEqual(t['stages'][0]['name'], 'chim')

    def test_serve_protocol(self):
        import io
        out = io.StringIO()
        monitor_read.serve(self.r, io.StringIO('{"op":"runs"}\nnot json\n{"op":"log","run":"..","name":"x.log"}\n'), out)
        answers = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertTrue(answers[0]['ok'])
        self.assertFalse(answers[1]['ok'])
        self.assertFalse(answers[2]['ok'])

    def test_console_tail(self):
        logs = self.tmp / 'aw-logs'
        logs.mkdir()
        (logs / (RUN + '.console.log')).write_bytes(b'line 1\nline 2\n')
        self.assertEqual(monitor_read.tail_file(logs, RUN + '.console.log', 0)['text'], 'line 1\nline 2\n')
        for bad in ('../secret.log', 'x.log', RUN + '.console.log/..'):
            with self.assertRaises(monitor_read.Refused):
                monitor_read.tail_file(logs, bad)


class ServerTests(unittest.TestCase):
    """The /monitor/ endpoints through a real server on a free port: GET only, checked names, nothing else served."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.builds = cls.tmp / 'build'
        sample_run(cls.builds)
        (cls.tmp / 'secret.json').write_bytes(b'{"secret": 1}')
        cls.results = cls.tmp / 'results'
        cls.results.mkdir()
        (cls.results / 'gate-1.json').write_text(json.dumps({'schema': 'aw-result-1', 'kind': 'gate', 'gate': 1,
                                                             'status': 'passed', 'seconds': 12.5, 'run_name': 'g1',
                                                             'numbers': {'tests': 10, 'blob': 'x' * 500}}))
        (cls.results / 'other.json').write_bytes(b'{"schema": "something-else"}')
        cls.logs = cls.tmp / 'logs'
        cls.logs.mkdir()
        (cls.logs / (RUN + '.console.log')).write_bytes(b'console line\n')
        H = toolkit_serve.Handler
        cls.saved = (H.builds, H.results_dir, H.console_dir)
        H.builds = toolkit_serve.Cached(toolkit_serve.LocalBuilds(cls.builds))
        H.results_dir, H.console_dir = cls.results, cls.logs
        cls.server = toolkit_serve.ThreadingHTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = 'http://127.0.0.1:%d' % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        toolkit_serve.Handler.builds, toolkit_serve.Handler.results_dir, toolkit_serve.Handler.console_dir = cls.saved
        shutil.rmtree(cls.tmp, True)

    def get(self, path, method='GET'):
        req = urllib.request.Request(self.base + path, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_endpoints(self):
        code, body = self.get('/monitor/runs.json')
        self.assertEqual((code, json.loads(body)['runs'][0]['run']), (200, RUN))
        code, body = self.get('/monitor/run/%s/progress.json' % RUN)
        self.assertEqual(json.loads(body)['progress']['status'], 'running')
        code, body = self.get('/monitor/run/%s/log/32-chim.log?offset=0&max=40' % RUN)
        d = json.loads(body)
        self.assertEqual((d['offset'], d['next']), (0, 40))
        code, body = self.get('/monitor/run/%s/trace/32-chim.txt?offset=0' % RUN)
        self.assertEqual((code, json.loads(body)['next']), (200, 77))
        self.assertEqual(self.get('/monitor/run/%s/trace/01-setup.log' % RUN)[0], 400)
        code, body = self.get('/monitor/console/%s?offset=0' % RUN)
        self.assertEqual(json.loads(body)['text'], 'console line\n')
        rows = json.loads(self.get('/monitor/results.json')[1])['results']
        self.assertEqual([r['run_name'] for r in rows], ['g1'])                 # aw-result-1 only
        self.assertNotIn('blob', rows[0]['numbers'])                           # long values left out
        self.assertEqual(json.loads(self.get('/monitor/config.json')[1]),
                         {'ok': True, 'builds': True, 'results': True, 'console': True})

    def test_traversal_and_bad_input_are_refused(self):
        for path in ('/monitor/run/..%2f..%2fsecret.json/progress.json', '/monitor/run/%2e%2e/progress.json',
                     '/monitor/run/%s/log/..%%2f..%%2fbuild-progress.json' % RUN, '/monitor/run/%s/log/x;id.log' % RUN,
                     '/monitor/run/%s/log/01-setup.log?offset=1e9' % RUN, '/monitor/run/%s/log/01-setup.log?max=abc' % RUN,
                     '/monitor/console/..%2fsecret', '/monitor/run/%s/../secret.json' % RUN, '/monitor/run/a%5cb/files.json',
                     '/monitor/run/%s/build-state.json' % RUN, '/monitor/../secret.json'):
            code, body = self.get(path)
            self.assertIn(code, (400, 404), path)
            self.assertNotIn(b'secret', body.replace(b'secret.json', b''), path)

    def test_nothing_but_get(self):
        for method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            code, _ = self.get('/monitor/runs.json', method)
            self.assertIn(code, (405, 501), method)

    def test_command_source_is_fixed_and_requests_are_data(self):
        argv = [sys.executable, '-I', str(ROOT / 'tools' / 'monitor_read.py'), '--root', 'builds=%s' % self.builds, '--serve']
        source = toolkit_serve.CommandBuilds(argv)
        try:
            self.assertEqual(source.ask({'op': 'runs'})['runs'][0]['run'], RUN)
            answer = source.ask({'op': 'log', 'run': RUN, 'name': '01-setup.log', 'offset': 0, 'max': 100})
            self.assertEqual(answer['text'], 'setup done\n')
            self.assertFalse(source.ask({'op': 'log', 'run': '$(touch pwned)', 'name': 'x.log'})['ok'])
            self.assertEqual(source.argv, argv)                                 # requests never change the command
        finally:
            source.stop()
        self.assertFalse((Path.cwd() / 'pwned').exists())


class DockerSourceTests(unittest.TestCase):
    """--monitor-docker VOLUME[:PATH]: a fixed, read-only container command built once from the operator's options."""

    def test_the_command_is_read_only_and_fixed(self):
        argv = toolkit_serve.docker_monitor_command('amiwind-docker-builds', name='amiwind-toolkit-monitor-8031')
        joined = ' '.join(argv)
        for part in ('--rm', '--network none', '--read-only', '--cap-drop ALL', '--pull never', '--user 65534:65534',
                     'type=volume,source=amiwind-docker-builds,target=/vol,readonly',
                     '/amiwind-monitor/monitor_read.py,readonly', 'builds=/vol/build', '--serve'):
            self.assertIn(part, joined)
        self.assertEqual(argv[-5:-3], ['-I', '/amiwind-monitor/monitor_read.py'])
        self.assertNotIn('sh', argv)                                   # no shell anywhere in the command
        self.assertIn('builds=/vol/ws8/build', toolkit_serve.docker_monitor_command('v:ws8/build'))
        self.assertIn('builds=/vol/ws8/build', toolkit_serve.docker_monitor_command('v:/ws8/build/'))

    def test_bad_options_are_refused(self):
        for spec in ('', 'a b', 'v;rm', 'v:../x', 'v:a/../../x', 'v:a b', 'v:$(id)', '-v', 'v:a,b'):
            with self.assertRaises(ValueError, msg=spec):
                toolkit_serve.docker_monitor_command(spec)
        for image in ('', 'a b', 'img;id', '-it'):
            with self.assertRaises(ValueError, msg=image):
                toolkit_serve.docker_monitor_command('v', image)
        with self.assertRaises(ValueError):
            toolkit_serve.docker_monitor_command('v', name='x y')

    def test_page_requests_reach_the_container_as_data_only(self):
        # the argv is fixed at start; a request is one JSON line on the reader's input, checked by the server first
        source = toolkit_serve.CommandBuilds(toolkit_serve.docker_monitor_command('v', docker='docker-never-run'))
        before = list(source.argv)
        H = toolkit_serve.Handler
        self.assertEqual(before, source.argv)
        for bad in ('$(id)', 'a;b', '../x', 'a b'):
            with self.assertRaises(monitor_read.Refused):
                monitor_read.check_name(bad, what='run')
        self.assertIsNone(source.proc)                                  # nothing was started by building it
        self.assertTrue(hasattr(H, 'monitor'))

    def test_bind_is_one_named_address(self):
        self.assertEqual(toolkit_serve.check_bind('localhost'), '127.0.0.1')
        self.assertEqual(toolkit_serve.check_bind('192.168.1.20'), '192.168.1.20')
        for bad in ('0.0' + '.0.0', '::', 'example.com', '224.0.0.1'):
            with self.assertRaises(ValueError, msg=bad):
                toolkit_serve.check_bind(bad)

    def test_server_options(self):
        with self.assertRaises(SystemExit):
            toolkit_serve.main(['--builds', '.', '--monitor-docker', 'v'])
        with self.assertRaises(SystemExit):
            toolkit_serve.main(['--monitor-docker', 'v:../etc'])


class PageTests(unittest.TestCase):
    def test_page_reads_only_and_carries_the_header(self):
        html = (ROOT / 'amiwind-toolkit' / 'monitor.html').read_text(encoding='utf-8')
        self.assertIn('<script src="header.js"></script>', html)
        self.assertIn("AmiWindToolkitHeader.mount('Monitor')", html)
        self.assertNotIn('method:', html)                       # every fetch is a plain GET
        self.assertIn('/monitor/runs.json', html)
        index = (ROOT / 'amiwind-toolkit' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<button role="tab" id="tab-monitor" aria-selected="false">Monitor</button>', index)

    def test_the_follow_choices_are_remembered_and_start_on(self):
        # the maintainer, 24 October 2026: on a load or a reload, "follow latest" and "follow the running stage" follow
        # the running build ("maybe you could cookie the user prefs"): both on when nothing is saved, the last choice
        # kept in this browser, and a running build found by follow latest wins over the page's ?run= link
        html = (ROOT / 'amiwind-toolkit' / 'monitor.html').read_text(encoding='utf-8')
        self.assertIn('<input type="checkbox" id="followlatest" checked autocomplete="off">', html)
        self.assertIn('<input type="checkbox" id="follow" checked autocomplete="off">', html)
        self.assertIn("const FOLLOW_KEY = 'amiwind-monitor-follow-1';", html)
        self.assertIn('return {latest: true, stage: true};', html)          # nothing saved: both on
        self.assertIn("$('followlatest').checked = saved.latest; $('follow').checked = saved.stage;", html)
        self.assertEqual(html.count('saveFollowPrefs();'), 4)                # every way a choice changes is saved
        self.assertIn('if (S.run) return;', html)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_page_renders_a_sample_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            builds = Path(tmp) / 'build'
            sample_run(builds)
            r = monitor_read.Reader(builds)
            answers = {'/monitor/config.json': {'ok': True, 'builds': True, 'results': True, 'console': False},
                       '/monitor/results.json': {'ok': True, 'results': toolkit_serve.recent_results(builds)},
                       '/monitor/runs.json': r.answer({'op': 'runs'}),
                       '/monitor/run/%s/progress.json' % RUN: r.answer({'op': 'progress', 'run': RUN}),
                       '/monitor/run/%s/files.json' % RUN: r.answer({'op': 'files', 'run': RUN}),
                       '/monitor/run/%s/state.json' % RUN: r.answer({'op': 'state', 'run': RUN}),
                       '/monitor/run/%s/log/32-chim.log' % RUN: r.answer({'op': 'log', 'run': RUN, 'name': '32-chim.log',
                                                                          'offset': -1, 'max': 65536})}
            fixture = Path(tmp) / 'answers.json'
            fixture.write_text(json.dumps(answers), encoding='utf-8')
            out = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / 'test_toolkit_monitor.js'),
                                  str(ROOT / 'amiwind-toolkit' / 'monitor.html'), str(fixture)],
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            page = json.loads(out.stdout)
        self.assertEqual(page['status'], 'running')
        self.assertIn('2 passed, 1 running, 1 pending, 0 failed of 4', page['facts'])
        self.assertIn('critical path', page['facts'])
        self.assertEqual(page['stages'], 4)
        self.assertEqual(page['log'], '32-chim.log')                          # follows the running stage
        self.assertIn('frames/x+1999/y+00', page['text'])
        self.assertEqual(page['text'].count('frames/x+1999/y+00'), 1)          # read once, not appended twice
        self.assertTrue(page['text'].rstrip().endswith('1999 steps'))
        # the live stage timeline: bsp and npcs ran side by side (two rows), chim running to now
        self.assertIn('Live, from build-state.json: 4 stages on 2 rows', page['timeline'])
        self.assertIn('<line', page['chart'])
        # red stretches: only runs under 2.5 cores held for 30 s or more
        self.assertEqual([(r['start'], r['end']) for r in page['red']], [(0, 40), (90, 130)])
        self.assertTrue(page['redLine'])
        self.assertEqual((page['sel']['start'], page['sel']['end']), (0, 60))
        self.assertIn('Red stretch 1 of 1', page['detail'])
        self.assertIn('chim', page['detail'])
        self.assertTrue(page['highlight'])
        self.assertTrue(page['full1'])
        self.assertIn('maximized', page['fullClass'])
        self.assertFalse(page['full2'])
        self.assertNotIn('maximized', page['fullClassAfter'])
        self.assertIn('RED STRETCH', page['hover'])
        self.assertIn('red: under 2.5', page['hover'])
        self.assertEqual(page['runValue'], RUN)                                # the selection is kept
        self.assertTrue(any(t.startswith('\u25cf new') and 'vivec-stage-a' in t for t in page['runOptions']))
        self.assertFalse(any(t.startswith('\u25cf new') and RUN in t for t in page['runOptions']))


if __name__ == '__main__':
    unittest.main()
