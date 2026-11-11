# SPDX-License-Identifier: GPL-3.0-only
"""--served-build (tools/toolkit_serve.py): a delivered build's maps, CHIM world and rooms store are served by themselves, the
newest copy wins without a restart, and the Polycount inspector opens it by default (TOOLKIT-SERVES-LATEST-BUILD-64)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolkit_serve as ts  # noqa: E402


def make_copy(folder, label, rooms=('addamasartus', 'bmcouncil'), maps=('seyda', 'bmhlaalo')):
    folder.mkdir(parents=True)
    (folder / 'maps').mkdir()
    for name in maps:
        (folder / 'maps' / (name + '.bsp')).write_bytes(b'BSP:' + name.encode())
    (folder / 'chim').mkdir()
    (folder / 'chim' / 'world.cwi').write_bytes(b'WORLD')
    (folder / 'chimi' / 'rooms').mkdir(parents=True)
    (folder / 'chimi' / 'world.cwi').write_bytes(b'STORE')
    for name in rooms:
        (folder / 'chimi' / 'rooms' / (name + '.crm')).write_bytes(b'ROOM:' + name.encode())
    (folder / ts.SERVED_MARK).write_text(json.dumps({'label': label, 'version': '0.0.64-dev4', 'run': 'r', 'commit': 'abc'}))


class ServedBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.saved = (ts.Handler.served_build, ts.Handler.served_cache, ts.Handler.maps_dir, ts.Handler.chim_worlds)
        self.addCleanup(lambda: (setattr(ts.Handler, 'served_build', self.saved[0]), setattr(ts.Handler, 'served_cache', self.saved[1]),
                                 setattr(ts.Handler, 'maps_dir', self.saved[2]), setattr(ts.Handler, 'chim_worlds', self.saved[3])))
        ts.Handler.maps_dir, ts.Handler.chim_worlds = None, {}
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), ts.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path):
        try:
            with urllib.request.urlopen('http://127.0.0.1:%d%s' % (self.server.server_address[1], path), timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b''

    def serve(self, folder):
        ts.Handler.served_build = Path(folder).resolve()
        ts.Handler.served_cache = (0.0, None)

    def test_a_copy_is_listed_and_served(self):
        make_copy(self.tmp / 'v0.0.64-dev4', 'v0.0.64-dev4 (abc)')
        self.serve(self.tmp / 'v0.0.64-dev4')
        status, body = self.get('/build/config.json')
        info = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual((info['label'], info['maps'], info['rooms'], info['world'], info['interiors'], info['base']),
                         ('v0.0.64-dev4 (abc)', ['bmhlaalo', 'seyda'], ['addamasartus', 'bmcouncil'], True, True, '/chim-world/build/'))
        self.assertEqual(json.loads(self.get('/maps/index.json')[1]), ['bmhlaalo', 'seyda'])
        self.assertEqual(self.get('/maps/seyda.bsp'), (200, b'BSP:seyda'))
        self.assertEqual(self.get('/chim-world/build/chimi/rooms/bmcouncil.crm'), (200, b'ROOM:bmcouncil'))
        self.assertEqual(self.get('/chim-world/build/chimi/world.cwi'), (200, b'STORE'))
        self.assertEqual(self.get('/chim-world/build/chim/world.cwi'), (200, b'WORLD'))
        self.assertIn('build', json.loads(self.get('/chim-world/index.json')[1]))

    def test_nothing_outside_the_copy_is_served(self):
        make_copy(self.tmp / 'a', 'a')
        (self.tmp / 'secret.txt').write_text('no')
        self.serve(self.tmp / 'a')
        self.assertEqual(self.get('/chim-world/build/%2e%2e/secret.txt')[0], 400)
        self.assertEqual(self.get('/chim-world/build/chimi/rooms/none.crm')[0], 404)

    def test_the_newest_copy_wins_without_a_restart(self):
        make_copy(self.tmp / 'copies' / 'v0.0.64-dev4', 'v0.0.64-dev4')
        self.serve(self.tmp / 'copies')
        self.assertEqual(json.loads(self.get('/build/config.json')[1])['label'], 'v0.0.64-dev4')
        time.sleep(0.05)
        make_copy(self.tmp / 'copies' / 'v0.0.64-dev5', 'v0.0.64-dev5', rooms=('bmnew',))
        os.utime(self.tmp / 'copies' / 'v0.0.64-dev5' / ts.SERVED_MARK, (time.time() + 5, time.time() + 5))
        ts.Handler.served_cache = (0.0, None)                      # the server looks again every two seconds
        info = json.loads(self.get('/build/config.json')[1])
        self.assertEqual((info['label'], info['rooms']), ('v0.0.64-dev5', ['bmnew']))

    def test_a_folder_without_a_marker_is_not_a_copy(self):
        (self.tmp / 'half' / 'maps').mkdir(parents=True)          # a copy still being written has no marker yet
        self.assertIsNone(ts.served_build_root(self.tmp))
        self.serve(self.tmp)
        self.assertEqual(self.get('/build/config.json')[0], 404)

    def test_the_inspector_opens_the_served_build_by_default(self):
        page = (ROOT / 'amiwind-toolkit' / 'map-inspector.html').read_text(encoding='utf-8')
        for needle in ("fetch('/build/config.json'", 'async function servedBuildOpen(sb,q)', "q.get('room')",
                       "if(!w&&!u&&!z&&!rs){const sb=await servedBuild();", 'id="servedmap"', 'chimOpenRooms(AmiWindChim.urlSource(sb.base)'):
            self.assertIn(needle, page)

    def test_the_world_map_reads_the_served_maps(self):
        self.assertIn("fetch('../maps/index.json')", (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
