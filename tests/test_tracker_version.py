"""The Toolkit's version values follow VERSION (TOOLKIT-ELIGIBLE-RELEASE-STALE-64): the tracker data's version fields are
computed from VERSION, the pregate check refuses data and pages that lag it, and the served version stamp changes when the
commit, the version line or the tracker data changes (the pages reload on that)."""
import copy
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cell_progress as cp  # noqa: E402
import toolkit_stamp as ts  # noqa: E402
import tracker_version_check as tvc  # noqa: E402

KIT = ROOT / 'amiwind-toolkit'


def good_doc(version):
    doc = {'headline': {'in_game_label': 'v0.0.1-dev1 (abc)', 'in_game_build': 'v0_0_1_dev1_full_x'}}
    return cp.stamp_document(doc, path=version)


class VersionFollowTests(unittest.TestCase):
    def version_file(self, text):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (d / 'VERSION').write_text(text + '\n')
        return d / 'VERSION'

    def test_data_fields_are_computed_from_version(self):
        doc = good_doc(self.version_file('0.0.64-dev3'))
        self.assertEqual(doc['headline']['eligible_release'], 'v0.0.64')
        self.assertNotIn('version', doc['headline'])          # the release only: a dev number change rewrites nothing
        self.assertEqual(doc['version_stamp'], {'release': 'v0.0.64', 'source': 'the version file'})
        self.assertEqual(tvc.data_problems(doc, '0.0.64-dev3'), [])
        self.assertEqual(tvc.data_problems(doc, '0.0.64-dev4'), [])       # same release line: still current
        self.assertTrue(tvc.data_problems(doc, '0.0.65-dev1'))            # a new release line: restamp

    def test_the_real_version_line_is_followed(self):
        version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(cp.eligible_release('v0.0.57', version), 'v' + version.split('-')[0])   # never the plan's value
        self.assertEqual(tvc.data_problems(cp.stamp_document({'headline': {}}), version), [])

    def test_stale_data_fails_the_check(self):
        doc = good_doc(self.version_file('0.0.57-dev2'))
        self.assertEqual(doc['headline']['eligible_release'], 'v0.0.57')
        problems = tvc.data_problems(doc, '0.0.64-dev3')
        self.assertTrue(any('eligible for v0.0.57' in p for p in problems), problems)
        self.assertTrue(any('restamp' in p for p in problems))
        edited = copy.deepcopy(good_doc(self.version_file('0.0.64-dev3')))
        edited['headline']['eligible_release'] = 'v0.0.57'                         # a hand-set value
        self.assertTrue(tvc.data_problems(edited, '0.0.64-dev3'))
        del edited['version_stamp']
        self.assertTrue(any('no version_stamp' in p for p in tvc.data_problems(edited, '0.0.64-dev3')))
        newer = good_doc(self.version_file('0.0.64-dev3'))
        newer['headline']['in_game_build'] = 'v0_0_65_dev1_full_x'                 # a build newer than VERSION
        self.assertTrue(any('newer than VERSION' in p for p in tvc.data_problems(newer, '0.0.64-dev3')))

    def test_the_toolkit_types_no_version(self):
        self.assertEqual(tvc.static_problems(ROOT), [])

    def test_a_typed_version_in_a_page_is_found(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / 'amiwind-toolkit').mkdir()
        (root / 'tools').mkdir()
        (root / 'tools' / 'cell_progress.py').write_text('eligible_release(None, working_release())\nstamp_document(doc)\n')
        (root / 'amiwind-toolkit' / 'x.js').write_text("// eligible for v0.0.57 in a comment is fine\n"
                                                      "const a = 'Last updated with AmiWind v0.0.64';\n"
                                                      "const label = 'eligible for v0.0.57';\n")
        problems = tvc.static_problems(root)
        self.assertEqual(len(problems), 1)
        self.assertIn('x.js:3', problems[0])

    def test_restamp_rewrites_only_the_version_fields(self):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        doc = good_doc(self.version_file('0.0.57-dev2'))
        doc['cells'] = {'0,0': {'x': 1}}
        (out / 'cell-progress.json').write_text(json.dumps(doc))
        self.assertEqual(cp.main(['restamp', '--out', str(out)]), 0)
        fresh = json.loads((out / 'cell-progress.json').read_text())
        self.assertEqual(fresh['cells'], {'0,0': {'x': 1}})
        self.assertEqual(tvc.data_problems(fresh, (ROOT / 'VERSION').read_text().strip()), [])

    def test_every_ingest_stamps_its_data(self):
        source = (ROOT / 'tools' / 'cell_progress.py').read_text(encoding='utf-8')
        self.assertIn('stamp_document(doc)', source)       # every ingest stamps its data from VERSION


class HeadlineTests(unittest.TestCase):
    def test_the_headline_rows_and_labels(self):
        head = (KIT / 'chim-head.js').read_text(encoding='utf-8')
        for needle in ("'Vvardenfell (main game)'", "'Solstheim (Bloodmoon DLC)'", "'Mournhold (Tribunal DLC)'",
                       "FULL_CELLS = 'Fully approved cells:'", "FULL_TERRAIN = 'Fully approved terrain:'",
                       "newest ingested build", "release || 'the next release'"):
            self.assertIn(needle, head)
        self.assertNotIn("' · cell complete '", head)
        self.assertIn('not a single polygon off', head)     # the legend text for the two approved statuses


class StampTests(unittest.TestCase):
    def tree(self, version='0.0.64-dev3', own='0.1.26', named='v0.0.64'):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / 'amiwind-toolkit').mkdir()
        (root / 'VERSION').write_text(version + '\n')
        (root / 'amiwind-toolkit' / 'world-map.html').write_text("const TOOLKIT = {name: 'x', version: '%s'};\n" % own)
        (root / 'amiwind-toolkit' / 'header.js').write_text("const VERSION_TEXT = 'Last updated with AmiWind %s';\n" % named)
        return root

    def test_stamp_reads_version_line_and_ingest(self):
        root = self.tree()
        data = root / 'data'
        data.mkdir()
        (data / 'cell-progress.json').write_text('{}')
        s = ts.make_stamp(root, None, data)
        self.assertEqual((s['format'], s['version'], s['follow']), (ts.FORMAT, '0.0.64-dev3', False))
        self.assertEqual(s['line'], {'toolkit': '0.1.26', 'last_updated_with': 'v0.0.64'})
        self.assertEqual(s['ingest']['size'], 2)

    def test_change_detection(self):
        root = self.tree()
        old = ts.make_stamp(root)
        self.assertFalse(ts.changed(old, ts.make_stamp(root)))
        (root / 'VERSION').write_text('0.0.64-dev4\n')
        self.assertTrue(ts.changed(old, ts.make_stamp(root)))                       # a new version
        root2 = self.tree(own='0.1.27')
        self.assertTrue(ts.changed(old, ts.make_stamp(root2)))                      # the Toolkit's own version line
        for k in ('commit', 'ingest'):
            moved = dict(old, **{k: 'x' if k == 'commit' else {'mtime': 5, 'size': 9}})
            self.assertTrue(ts.changed(old, moved), k)
        self.assertFalse(ts.changed(old, dict(old, note='something else')))        # unwatched fields never reload
        self.assertFalse(ts.changed(None, old))                                    # nothing known yet: no reload
        self.assertFalse(ts.changed(old, {'format': 'other'}))                     # an unreadable answer: no reload
        self.assertFalse(ts.changed(old, None))

    def test_record_and_follow(self):
        # git is faked (the gate image has none): the commit objects are a dict of path -> text per commit
        root = self.tree()
        first = 'a' * 40
        objects = {first: {'VERSION': '0.0.64-dev3\n',
                           'amiwind-toolkit/world-map.html': "const TOOLKIT = {name: 'x', version: '0.1.20'};\n",
                           'amiwind-toolkit/header.js': "const VERSION_TEXT = 'Last updated with AmiWind v0.0.63';\n"}}
        saved = ts.resolve_commit, ts.file_at, ts.git
        self.addCleanup(lambda: [setattr(ts, n, f) for n, f in zip(('resolve_commit', 'file_at', 'git'), saved)])
        ts.resolve_commit = lambda r, ref: first if first.startswith(ref) else None
        ts.file_at = lambda r, c, p: objects[c][p].encode() if c in objects and p in objects[c] else None
        ts.git = lambda r, *a: 'f' * 40 + '\n'
        (root / 'VERSION').write_text('0.0.65-dev1\n')
        record = root / 'rec.json'
        record.write_text(json.dumps({'head': first[:9], 'working_version': '0.0.64-dev3'}))
        s = ts.make_stamp(root, record)
        self.assertTrue(s['follow'])
        self.assertEqual((s['commit'], s['version']), (first, '0.0.64-dev3'))      # the record's head, not the checkout's files
        self.assertEqual(s['line'], {'toolkit': '0.1.20', 'last_updated_with': 'v0.0.63'})   # the pages of that commit
        record.write_text(json.dumps({'head': 'b' * 40, 'working_version': '0.0.64-dev3'}))
        s = ts.make_stamp(root, record)
        self.assertIn('does not have', s['note'])                                   # an unknown head: the checkout's own HEAD
        self.assertEqual(s['commit'], 'f' * 40)
        self.assertIsNone(ts.read_record(root / 'missing.json'))

    def test_the_server_answers_the_stamp(self):
        import toolkit_serve as srv
        srv.Handler.follow_record, srv.Handler.stamp_cache, srv.Handler.progress_dir = None, (0.0, None), None
        server = ThreadingHTTPServer(('127.0.0.1', 0), srv.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urllib.request.urlopen('http://127.0.0.1:%d/amiwind-toolkit/version.json' % server.server_address[1], timeout=20) as r:
            doc = json.loads(r.read())
        self.assertEqual(doc['format'], ts.FORMAT)
        self.assertEqual(doc['version'], (ROOT / 'VERSION').read_text().strip())

    def test_the_pages_load_the_auto_refresh_and_it_follows_the_same_rule(self):
        js = (KIT / 'auto-refresh.js').read_text(encoding='utf-8')
        self.assertIn("WATCHED = ['commit', 'version', 'line', 'ingest']", js)
        self.assertEqual(ts.WATCHED, ('commit', 'version', 'line', 'ingest'))
        self.assertIn("/^https?:$/.test(loc.protocol)", js)                         # off when opened from a file
        for page in ('index.html', 'world-map.html', 'monitor.html', 'mesh-compare.html', 'seam-check.html', 'map-inspector.html'):
            self.assertIn('<script src="auto-refresh.js"></script>', (KIT / page).read_text(encoding='utf-8'), page)


if __name__ == '__main__':
    unittest.main()
