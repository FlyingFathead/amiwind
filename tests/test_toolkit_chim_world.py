# SPDX-License-Identifier: GPL-3.0-only
"""tools/toolkit_serve.py --chim-world NAME=DIR: a build's CHIM world served read-only for the Polycount inspector."""
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import toolkit_serve  # noqa: E402


class ChimWorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.world = self.tmp / 'world'
        (self.world / 'chim/frames/x-07/y-04').mkdir(parents=True)
        (self.world / 'chim-heap.json').write_text('{"frames": []}')
        (self.world / 'chim/frames/x-07/y-04/frame.ccf').write_bytes(b'CHIM')
        (self.tmp / 'secret.txt').write_text('outside')
        self.saved = toolkit_serve.Handler.chim_worlds
        toolkit_serve.Handler.chim_worlds = {'hlaoad': self.world.resolve()}
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), toolkit_serve.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = 'http://127.0.0.1:%d' % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        toolkit_serve.Handler.chim_worlds = self.saved

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b''

    def test_world_files_and_index_are_served(self):
        self.assertEqual(self.get('/chim-world/index.json'), (200, b'["hlaoad"]'))
        self.assertEqual(self.get('/chim-world/hlaoad/chim-heap.json')[1], b'{"frames": []}')
        self.assertEqual(self.get('/chim-world/hlaoad/chim/frames/x-07/y-04/frame.ccf'), (200, b'CHIM'))

    def test_nothing_outside_the_world_or_unknown_names(self):
        self.assertNotEqual(self.get('/chim-world/hlaoad/../secret.txt')[1], b'outside')
        self.assertIn(self.get('/chim-world/hlaoad/%2e%2e/secret.txt')[0], (400, 404))
        self.assertEqual(self.get('/chim-world/other/chim-heap.json')[0], 404)
        self.assertEqual(self.get('/chim-world/hlaoad/missing.json')[0], 404)

    def test_switch_refuses_a_bad_value(self):
        with self.assertRaises(SystemExit):
            toolkit_serve.main(['--chim-world', 'nofolder=' + str(self.tmp / 'none')])


class EverywhereRecipeTests(unittest.TestCase):
    def setUp(self):
        import visual_recipes
        self.vr = visual_recipes
        self.doc = {'format': 1, 'everywhere': 'all-v1', 'recipes': {'all-v1': {'models': {
            'meshes/l/lamp.nif': {'sha256': 'a' * 64, 'primitive': {'kind': 'lantern_shell'}}}}}}

    def test_named_mesh_gets_its_replacement_in_any_cell(self):
        name = self.vr.everywhere_recipe(self.doc)
        out = self.vr.apply_recipe({'ratio': 1}, {'source': 'meshes\\l\\lamp.nif', 'sha256': 'a' * 64}, name, self.doc)
        self.assertEqual(out['visual_primitive'], {'kind': 'lantern_shell'})
        other = self.vr.apply_recipe({'ratio': 1}, {'source': 'meshes/x/rock.nif', 'sha256': 'b' * 64}, name, self.doc)
        self.assertEqual(other, {'ratio': 1})

    def test_switch_off_keeps_the_originals(self):
        import os
        os.environ[self.vr.EVERYWHERE_VARIABLE] = 'off'
        try:
            self.assertIsNone(self.vr.everywhere_recipe(self.doc))
        finally:
            del os.environ[self.vr.EVERYWHERE_VARIABLE]

    def test_everywhere_recipe_may_not_cap_unnamed_meshes(self):
        self.doc['recipes']['all-v1']['default_visual_ratio'] = 0.2
        with self.assertRaises(ValueError):
            self.vr.everywhere_recipe(self.doc)

    def test_repository_recipe_replaces_the_streetlight(self):
        doc = self.vr.load_recipes()
        name = self.vr.everywhere_recipe(doc)
        self.assertIn('meshes/l/light_de_streetlight_01.nif', doc['recipes'][name]['models'])


if __name__ == '__main__':
    unittest.main()
