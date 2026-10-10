# SPDX-License-Identifier: GPL-3.0-only
"""The live build tracker (tools/live_tracker.py): the prompt and flags, the incremental files, the server lifecycle."""
import json
import re
import socket
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import live_tracker as lt  # noqa: E402
from test_cell_progress import chim_run  # noqa: E402


class PromptTests(unittest.TestCase):
    def ask(self, answer, **kw):
        said = []
        mode = lt.choose(kw.get('requested'), kw.get('disabled', False), kw.get('guided', True),
                         ask=lambda prompt: answer, say=said.append)
        return mode, said

    def test_guided_builds_ask_once_and_explain_in_plain_words(self):
        mode, said = self.ask('')
        self.assertEqual(mode, 'file')                      # the default: no server
        text = ' '.join(said)
        for needle in ('127.0.0.1', 'Nothing leaves your computer', 'read-only', 'stops with the build', 'no server',
                       '--no-live-tracker', 'every 10 seconds'):
            self.assertIn(needle, text)

    def test_answers(self):
        self.assertEqual(self.ask('s')[0], 'server')
        self.assertEqual(self.ask('Server')[0], 'server')
        self.assertEqual(self.ask('F')[0], 'file')
        self.assertIsNone(self.ask('n')[0])
        self.assertIsNone(self.ask('whatever')[0])

    def test_non_guided_default_is_off_and_flags_decide(self):
        mode, said = self.ask('', guided=False)
        self.assertIsNone(mode)
        self.assertEqual(said, [])                          # no prompt at all
        self.assertEqual(self.ask('', guided=False, requested='server')[0], 'server')
        mode, said = self.ask('', requested='file')
        self.assertEqual((mode, said), ('file', []))        # asked for by flag: not asked again
        mode, said = self.ask('s', disabled=True)
        self.assertEqual((mode, said), (None, []))          # --no-live-tracker wins and never prompts

    def test_eof_means_no(self):
        def eof(prompt):
            raise EOFError
        self.assertIsNone(lt.choose(None, False, True, ask=eof, say=lambda *_: None))

    def test_builder_flags(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        for flag in ('--live-tracker', '--no-live-tracker', '--keep-tracker'):
            self.assertIn("'%s'" % flag, text)
        self.assertIn("choices=('file', 'server')", text)
        self.assertIn('live_tracker.choose(args.live_tracker, args.tracker_declined', text)


class FilesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.run = Path(self._tmp.name) / 'run'

    def state(self, steps, status='running'):
        self.run.mkdir(parents=True, exist_ok=True)
        (self.run / 'build-state.json').write_text(json.dumps({'status': status, 'steps': steps}))

    def tracker(self, mode='file'):
        t = lt.LiveTracker(self.run, mode, total_stages=4, interval=1, say=lambda *_: None)
        self.addCleanup(t.stop, False)
        return t

    def test_stage_line_and_eta(self):
        self.state([{'name': 'a', 'status': 'passed', 'elapsed_seconds': 10}, {'name': 'b', 'status': 'passed', 'elapsed_seconds': 30},
                    {'name': 'chim', 'status': 'running'}])
        st = lt.stage_status(self.run, 4)
        self.assertEqual((st['stage'], st['stages_done'], st['stages_total'], st['eta_s']), ('chim', 2, 4, 40))
        self.assertEqual(lt.stage_status(self.run / 'nothing', 4)['state'], 'starting')

    def test_files_are_valid_mid_build_and_update_as_the_world_appears(self):
        t = self.tracker()
        t._tick()                                           # the run folder does not exist yet: nothing happens
        self.assertFalse((self.run / 'toolkit').exists())
        self.state([{'name': 'census', 'status': 'running'}])
        t._tick()                                           # no CHIM world yet: an empty but valid tracker
        progress = self.run / 'toolkit' / 'cell-progress.json'
        self.assertEqual(json.loads(progress.read_text())['format'], 'aw-cell-progress-1')
        status = json.loads((self.run / 'toolkit' / lt.STATUS_FILE).read_text())
        self.assertEqual((status['stage'], status['mode']), ('census', 'file'))
        chim_run(self.run / 'chim-world')                   # the CHIM stage finished
        self.state([{'name': 'census', 'status': 'passed', 'elapsed_seconds': 5}, {'name': 'chim', 'status': 'passed', 'elapsed_seconds': 9}])
        t._tick()
        doc = json.loads(progress.read_text())
        self.assertTrue(doc['cells']['2,2']['chim']['converted'])
        self.assertEqual(json.loads((self.run / 'toolkit' / lt.STATUS_FILE).read_text())['stages_done'], 2)
        # atomic writes leave no temporary files behind, and the data script holds the same document
        self.assertEqual(list((self.run / 'toolkit').rglob('*.tmp')), [])
        data = (self.run / 'toolkit' / lt.LIVE_FOLDER / lt.DATA_FILE).read_text()
        self.assertTrue(data.startswith('window.AW_LOGO_SRC='))
        self.assertTrue((self.run / 'toolkit' / lt.LIVE_FOLDER / 'AmiWind_logo_name_only.png').is_file())
        body = data.split('window.AW_PROGRESS=', 1)[1].split(';\nwindow.AW_LIVE=')[0]
        self.assertEqual(json.loads(body)['generated'], doc['generated'])
        page = (self.run / 'toolkit' / lt.LIVE_FOLDER / 'world-map.html').read_text(encoding='utf-8')
        self.assertIn('<script src="cell-progress-data.js"></script>', page)
        self.assertNotIn(lt.DATA_MARKER, page)
        for name in ('header.js', 'chim-legend.js', 'zebra.js'):
            self.assertTrue((self.run / 'toolkit' / lt.LIVE_FOLDER / name).is_file())
        self.assertIn('Track the build on the map: open file:', t.final_line())

    def test_a_failing_refresh_is_one_warning_not_an_error(self):
        said = []
        t = lt.LiveTracker(self.run, 'file', total_stages=1, say=said.append)
        self.state([])
        (self.run / 'toolkit').write_text('a file where the folder should be')
        t._tick()
        t._tick()
        self.assertEqual(len([s for s in said if s.startswith('WARNING')]), 1)

    def test_atomic_write(self):
        target = Path(self._tmp.name) / 'x' / 'f.json'
        lt.atomic_write(target, '{"a": 1}')
        lt.atomic_write(target, b'{"a": 2}')
        self.assertEqual(json.loads(target.read_text()), {'a': 2})
        self.assertEqual(list(target.parent.glob('*.tmp')), [])

    def test_the_page_has_the_data_marker_and_the_refresh_toggle(self):
        page = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
        self.assertEqual(page.count(lt.DATA_MARKER), 1)
        for needle in ('id="chimlive"', 'id="livestatus"', 'const LIVE_MS = 10000', 'FILE_LIVE', "'cell-progress-data.js?t='",
                       'document.createElement(\'script\')', "'../data/live-status.json"):
            self.assertIn(needle, page, needle)
        self.assertRegex(page, r"\$\('chimlive'\)\.onchange = \(\) => \{ if \(\$\('chimlive'\)\.checked\)")
        self.assertIn('liveStop(true)', page)          # a finished build stops the refresh


class ServerTests(unittest.TestCase):
    def test_server_lifecycle_loopback_only_and_stopped_with_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            run.mkdir()
            (run / 'build-state.json').write_text(json.dumps({'status': 'running', 'steps': []}))
            said = []
            t = lt.LiveTracker(run, 'server', total_stages=2, interval=1, say=said.append)
            t._tick()
            self.assertIsNotNone(t.server)
            self.assertRegex(t.url, r'^http://127\.0\.0\.1:\d+/$')
            self.assertTrue(any('Track the build on the map: ' + t.url in s for s in said))
            port = int(t.url.rstrip('/').rsplit(':', 1)[1])
            body = None
            for _ in range(50):
                try:
                    body = urllib.request.urlopen(t.url + 'data/cell-progress.json', timeout=2).read()
                    break
                except OSError:
                    time.sleep(0.2)
            self.assertIsNotNone(body, 'the server did not answer')
            self.assertEqual(json.loads(body)['format'], 'aw-cell-progress-1')
            self.assertEqual(json.loads(urllib.request.urlopen(t.url + 'data/live-status.json', timeout=2).read())['mode'], 'server')
            proc = t.server
            t.stop()
            self.assertIsNotNone(proc.poll(), 'the server process is still running: orphan')
            self.assertIsNone(t.server)
            with socket.socket() as s:
                s.settimeout(1)
                self.assertNotEqual(s.connect_ex(('127.0.0.1', port)), 0)       # nothing listens any more
            t.stop()                                                           # twice is fine
            self.assertIn('stopped with the build', t.final_line())
            self.assertIn('127.0.0.1', (ROOT / 'tools' / 'toolkit_serve.py').read_text(encoding='utf-8'))
            self.assertNotIn('0.0.0.0', (ROOT / 'tools' / 'toolkit_serve.py').read_text(encoding='utf-8'))

    def test_low_priority_children_and_no_network_beyond_loopback(self):
        text = (ROOT / 'tools' / 'live_tracker.py').read_text(encoding='utf-8')
        self.assertIn('BELOW_NORMAL_PRIORITY_CLASS', text)
        self.assertIn('os.nice(10)', text)
        self.assertIsNone(re.search(r'0\.0\.0\.0|urlopen|requests', text))


if __name__ == '__main__':
    unittest.main()
