# SPDX-License-Identifier: GPL-3.0-only
"""The tracker file is big (cell-progress.json is over 100 MB), so the server validates and compresses it and the page fetches it only
when its stamp changes (TOOLKIT-PROGRESS-FILE-REFETCHED-64)."""
import gzip
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolkit_serve as ts  # noqa: E402


class ProgressServingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.body = json.dumps({'cells': {str(i): {'x': i, 'pad': 'z' * 200} for i in range(500)}}).encode()
        (self.tmp / 'cell-progress.json').write_bytes(self.body)
        self.saved = (ts.Handler.progress_dir, dict(ts.Handler.gz_cache))
        self.addCleanup(lambda: (setattr(ts.Handler, 'progress_dir', self.saved[0]), ts.Handler.gz_cache.clear(), ts.Handler.gz_cache.update(self.saved[1])))
        ts.Handler.progress_dir = self.tmp
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ts.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, **headers):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.server.server_address[1], path), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), b''

    def test_plain_gzip_and_304(self):
        status, head, body = self.get('/data/cell-progress.json')
        self.assertEqual((status, body), (200, self.body))
        etag = head['ETag']
        self.assertEqual(self.get('/data/cell-progress.json', **{'If-None-Match': etag})[0], 304)         # unchanged: nothing sent
        status, head, packed = self.get('/data/cell-progress.json', **{'Accept-Encoding': 'gzip'})
        self.assertEqual((status, head.get('Content-Encoding'), head['ETag']), (200, 'gzip', etag))
        self.assertEqual(gzip.decompress(packed), self.body)
        self.assertLess(len(packed), len(self.body) // 5)
        first = ts.Handler.gz_cache[str(self.tmp / 'cell-progress.json')][1]
        self.get('/data/cell-progress.json', **{'Accept-Encoding': 'gzip'})
        self.assertIs(ts.Handler.gz_cache[str(self.tmp / 'cell-progress.json')][1], first)             # compressed once per file version

    def test_a_new_version_changes_the_stamp_and_the_cache(self):
        etag = json.loads(self.get('/data/progress-stamp.json')[2])['etag']
        (self.tmp / 'cell-progress.json').write_bytes(self.body + b' ')
        self.assertNotEqual(json.loads(self.get('/data/progress-stamp.json')[2])['etag'], etag)
        self.assertEqual(self.get('/data/cell-progress.json', **{'If-None-Match': etag})[0], 200)
        status, _, packed = self.get('/data/cell-progress.json', **{'Accept-Encoding': 'gzip'})
        self.assertEqual(gzip.decompress(packed), self.body + b' ')

    def test_the_page_fetches_only_on_a_changed_stamp(self):
        page = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
        for needle in ("fetch('../data/progress-stamp.json'", 'if (stamp && stamp === chimStamp && chim && !chimImported) return true;',
                       'if (chimLoading) return !!chim;', "fetch('../data/cell-progress.json', {cache: 'no-cache'})"):
            self.assertIn(needle, page)
        self.assertNotIn("cell-progress.json?t=", page)


if __name__ == '__main__':
    unittest.main()
