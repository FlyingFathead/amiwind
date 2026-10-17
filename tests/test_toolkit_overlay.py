# SPDX-License-Identifier: GPL-3.0-only
"""User-data map routes through a real temporary local server; synthetic bytes only.
Page checks below are source contracts, not browser or rendered-map acceptance.
"""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolkit_serve


class OverlayRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        data, progress = root / 'data', root / 'progress'
        data.mkdir()
        progress.mkdir()
        self.data, self.progress = data, progress
        (data / 'island-world.png').write_bytes(b'synthetic-map-bytes')
        (data / 'island-world.json').write_text(json.dumps(
            {'bounds': [-1, -2, 2, 3], 'pixels_per_cell': 9, 'style': 'world'}))
        (data / 'private-master.esm').write_bytes(b'private-input-not-served')
        (progress / 'cell-progress.json').write_bytes(b'{"source":"progress"}')
        (data / 'cell-progress.json').write_bytes(b'{"source":"wrong-data"}')
        class H(toolkit_serve.Handler):
            data_dir = data
            progress_dir = progress
        self.server = toolkit_serve.ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)
        self.url = 'http://127.0.0.1:%d' % self.server.server_address[1]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def get(self, route):
        try:
            r = urllib.request.urlopen(self.url + route, timeout=3)
        except urllib.error.HTTPError as error:
            r = error
        with r:
            return r.status, r.headers, r.read()

    def test_png_and_json_exact_bytes_types_and_no_store(self):
        for name, ctype in [('island-world.png', 'image/png'),
                            ('island-world.json', 'application/json')]:
            code, headers, body = self.get('/data/' + name)
            self.assertEqual(code, 200)
            self.assertEqual(body, (self.data / name).read_bytes())
            self.assertEqual(headers['Content-Type'], ctype)
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_rereads_changed_metadata_without_restart(self):
        self.get('/data/island-world.json')
        updated = b'{"bounds":[-3,-4,5,6],"style":"world","pixels_per_cell":8}'
        (self.data / 'island-world.json').write_bytes(updated)
        self.assertEqual(self.get('/data/island-world.json')[2], updated)

    def test_progress_binding_is_independent_of_background(self):
        self.assertEqual(self.get('/data/cell-progress.json')[2], b'{"source":"progress"}')

    def test_private_game_file_is_not_an_exposed_data_route(self):
        self.assertEqual(self.get('/data/private-master.esm')[0], 404)

    def test_traversal_is_refused(self):
        for route in ['/data/../private-master.esm', '/data/%2e%2e/private-master.esm',
                      '/data/a%5cb.json']:
            self.assertEqual(self.get(route)[0], 400, route)

    def test_missing_optional_background_is_404(self):
        (self.data / 'island-world.png').unlink()
        self.assertEqual(self.get('/data/island-world.png')[0], 404)

    def test_page_and_data_share_the_expected_route(self):
        code, _, body = self.get('/amiwind-toolkit/world-map.html?served=1')
        self.assertEqual(code, 200)
        self.assertEqual(body, (ROOT / 'amiwind-toolkit/world-map.html').read_bytes())
        self.assertEqual(self.get('/data/island-world.json?reload=1')[0], 200)


class OverlayPageContract(unittest.TestCase):
    def test_existing_loader_retains_world_pair_and_explicit_selection(self):
        page = (ROOT / 'amiwind-toolkit/world-map.html').read_text()
        self.assertIn("['world', 'island-world']", page)
        self.assertIn("images[style].bounds = meta.bounds", page)
        self.assertIn("URL.createObjectURL(png)", page)
        self.assertIn("setBottom($('bottom').value)", page)
        self.assertIn("const style = /world/i.test(f.name) ? 'world' : 'topo'", page)
        self.assertIn("images[j.style || style].bounds = j.bounds", page)


if __name__ == '__main__':
    unittest.main()
