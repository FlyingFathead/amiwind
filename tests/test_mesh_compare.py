# SPDX-License-Identifier: GPL-3.0-only
"""Mesh Compare: tools/mesh_export.py (deterministic OBJ export through the builder's own mesh path), the read-only
/mesh/ endpoints of tools/toolkit_serve.py, and amiwind-toolkit/mesh-compare.html on a synthetic fixture."""
import hashlib
import json
import shutil
import subprocess
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
sys.path.insert(0, str(ROOT / 'src'))

import mesh_export  # noqa: E402
import toolkit_serve  # noqa: E402

try:
    import numpy as np
except ImportError:                       # the export needs numpy (as the builder does)
    np = None

# a 64-unit box, two triangles per side, outward winding (Morrowind units: 16 Quake units once exported)
BOX_V = [(x, y, z, 0.0, 0.0) for x in (0, 64) for y in (0, 64) for z in (0, 64)]
BOX_F = [(0, 1, 3, 0), (0, 3, 2, 0), (4, 6, 7, 0), (4, 7, 5, 0), (0, 4, 5, 0), (0, 5, 1, 0),
         (2, 3, 7, 0), (2, 7, 6, 0), (0, 2, 6, 0), (0, 6, 4, 0), (1, 5, 7, 0), (1, 7, 3, 0)]
BOX_MATERIALS = [{'texture': 'textures\\tx_box.dds'}]
CUBE_OBJ = """# a unit cube: quads, one written with negative indices and v/vt/vn
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
v 0 0 1
v 1 0 1
v 1 1 1
v 0 1 1
f 1 4 3 2
f 5 6 7 8
f 1 2 6 5
f 2/1/1 3/1/1 7/1/1 6/1/1
f 3 4 8 7
f -4 -1 -5 -8
f 1 2 99
"""


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class NamesTests(unittest.TestCase):
    def test_mesh_names(self):
        self.assertEqual(mesh_export.check_mesh('Meshes\\X\\Ex_Hlaalu_B_01.NIF'), 'meshes/x/ex_hlaalu_b_01.nif')
        for bad in ('meshes/../morrowind.ini', '../meshes/x.nif', 'meshes/x.dds', 'textures/x.nif', 'meshes//x.nif',
                    '/etc/passwd', 'meshes/x/$(id).nif', 'meshes/x/a;b.nif', ''):
            with self.assertRaises(ValueError, msg=bad):
                mesh_export.check_mesh(bad)

    def test_file_names_stay_flat(self):
        self.assertEqual(mesh_export.file_stem('meshes/x/ex_hlaalu_b_01.nif', 'meshopt+merge'), 'x__ex_hlaalu_b_01.meshopt-merge')
        for m in mesh_export.METHODS:
            name = mesh_export.file_stem('meshes/r/silt strider.nif', m) + '.obj'
            self.assertRegex(name, toolkit_serve.MESH_FILE)
            self.assertNotIn('/', name)

    def test_candidates_only_when_the_checkout_has_them(self):
        have = all((ROOT / 'tools' / n).is_file() for n in ('planar_merge.py', 'mesh_methods.py'))
        self.assertEqual(mesh_export.available_methods(), mesh_export.METHODS if have else mesh_export.BASE_METHODS)


@unittest.skipUnless(np is not None, 'numpy unavailable')
class ExportTests(unittest.TestCase):
    def export(self, out, profile=None):
        return mesh_export.export(np.array(BOX_V, float), np.array(BOX_F, int), BOX_MATERIALS, profile or {},
                                  ['original', 'current'], out, 'meshes/test/box.nif')

    def test_export_is_deterministic_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            ra, rb = self.export(a), self.export(b)
            self.assertEqual(ra, rb)
            names = sorted(p.name for p in a.iterdir())
            self.assertEqual(names, ['test__box.current.obj', 'test__box.export.json', 'test__box.mtl', 'test__box.original.obj'])
            for name in names:
                self.assertEqual(sha(a / name), sha(b / name), name)
            for row in ra['files']:
                self.assertEqual(row['sha256'], sha(a / row['file']))           # the record names each file's SHA-256
                self.assertEqual(row['bytes'], (a / row['file']).stat().st_size)
            self.assertEqual(json.loads((a / 'test__box.export.json').read_text())['format'], 'amiwind-mesh-export-1')
            mtl = (a / 'test__box.mtl').read_text()
            self.assertIn('map_Kd tx_box.dds', mtl)                              # a file name only, no texture data
            for f in a.iterdir():
                self.assertNotIn(b'\r', f.read_bytes())

    def test_original_and_current_on_a_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = self.export(tmp)
            rows = {r['method']: r for r in rec['files']}
            self.assertEqual((rows['original']['faces'], rows['original']['vertices']), (12, 8))
            self.assertEqual((rows['current']['faces'], rows['current']['vertices']), (6, 8))   # coplanar pairs: one face each
            text = (Path(tmp) / rows['current']['file']).read_text()
            verts = [tuple(map(float, l.split()[1:])) for l in text.splitlines() if l.startswith('v ')]
            self.assertEqual(max(max(v) for v in verts), 16.0)                  # Quake units (x 0.25)
            # every face counter-clockwise seen from outside the box
            centre = np.array([8.0, 8.0, 8.0])
            for line in text.splitlines():
                if line.startswith('f '):
                    p = np.array([verts[int(k) - 1] for k in line.split()[1:]])
                    n = sum(np.cross(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))
                    self.assertGreater(float(n @ (p.mean(axis=0) - centre)), 0, line)

    def test_unknown_method_is_refused(self):
        with self.assertRaises(ValueError):
            mesh_export.variants(np.array(BOX_V, float), np.array(BOX_F, int), BOX_MATERIALS, {}, ['bogus'])


class FakeExporter:
    def __init__(self):
        self.asked = []

    def methods(self):
        return ['original', 'current']

    def export(self, mesh, methods):
        mesh = mesh_export.check_mesh(mesh)
        if any(m not in self.methods() for m in methods):
            raise ValueError('methods')
        self.asked.append((mesh, methods))
        if mesh.endswith('missing.nif'):
            raise FileNotFoundError(mesh)
        return {'format': 'amiwind-mesh-export-1', 'source': mesh, 'files': []}


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / 'cache'
        self.cache.mkdir()
        (self.cache / 'x__box.original.obj').write_bytes(b'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
        (self.cache / 'secret.txt').write_bytes(b'not served')
        (Path(self.tmp.name) / 'outside.obj').write_bytes(b'outside')
        record = {'format': 'amiwind-mesh-export-1', 'source': 'meshes/x/box.nif', 'profile': {'space': 'town'},
                  'files': [{'source': 'meshes/x/box.nif', 'method': 'original', 'file': 'x__box.original.obj', 'faces': 1,
                             'vertices': 3, 'sha256': 'ab'},
                            {'source': 'meshes/x/box.nif', 'method': 'evil', 'file': '../outside.obj', 'faces': 1}]}
        (self.cache / 'x__box.export.json').write_text(json.dumps(record))
        self.saved = (toolkit_serve.Handler.mesh_cache, toolkit_serve.Handler.mesh_exporter)
        toolkit_serve.Handler.mesh_cache = self.cache
        toolkit_serve.Handler.mesh_exporter = self.exporter = FakeExporter()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), toolkit_serve.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = 'http://127.0.0.1:%d' % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        toolkit_serve.Handler.mesh_cache, toolkit_serve.Handler.mesh_exporter = self.saved
        self.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_list_and_files(self):
        status, body = self.get('/mesh/config.json')
        self.assertEqual(json.loads(body), {'ok': True, 'cache': True, 'export': True, 'methods': ['original', 'current']})
        status, body = self.get('/mesh/list.json')
        rows = json.loads(body)['files']
        self.assertEqual([r['file'] for r in rows], ['x__box.original.obj'])   # the record's '../outside.obj' is dropped
        self.assertEqual(rows[0]['space'], 'town')
        status, body = self.get('/mesh/file/x__box.original.obj')
        self.assertEqual((status, body[:7]), (200, b'v 0 0 0'))

    def test_nothing_outside_the_cache_and_only_obj_mtl(self):
        for path in ('/mesh/file/..%2Foutside.obj', '/mesh/file/../outside.obj', '/mesh/file/secret.txt',
                     '/mesh/file/X__BOX.ORIGINAL.OBJ', '/mesh/file/x__box.export.json', '/mesh/file/%2E%2E%2Foutside.obj',
                     '/mesh/file/sub/x.obj', '/mesh/file/..obj', '/mesh/../tools/toolkit_serve.py', '/mesh/nothing'):
            status, body = self.get(path)
            self.assertIn(status, (400, 404), path)
            self.assertNotIn(b'outside', body)
            self.assertNotIn(b'not served', body)

    def test_export_names_are_checked(self):
        for q in ('mesh=../../etc/passwd', 'mesh=meshes/x/..%2F..%2Fa.nif', 'mesh=meshes/x/a.nif&methods=bogus',
                  'mesh=meshes/x/$(id).nif', 'mesh='):
            status, body = self.get('/mesh/export.json?' + q)
            self.assertEqual(status, 400, q)
            self.assertFalse(json.loads(body)['ok'])
        self.assertEqual(self.exporter.asked, [])
        status, body = self.get('/mesh/export.json?mesh=meshes/x/missing.nif')
        self.assertEqual(status, 404)
        status, body = self.get('/mesh/export.json?mesh=meshes/x/box.nif&methods=original')
        self.assertEqual((status, json.loads(body)['ok']), (200, True))
        self.assertEqual(self.exporter.asked[-1], ('meshes/x/box.nif', ['original']))

    def test_export_off_and_no_cache(self):
        toolkit_serve.Handler.mesh_exporter = None
        status, body = self.get('/mesh/export.json?mesh=meshes/x/box.nif')
        self.assertEqual(status, 404)
        toolkit_serve.Handler.mesh_cache = None
        status, body = self.get('/mesh/list.json')
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(self.get('/mesh/config.json')[1])['export'], False)

    def test_container_command_is_fixed_and_read_only(self):
        ex = toolkit_serve.MeshExporter(self.tmp.name, self.cache, image='amiwind-builder:local', docker='docker-never-run',
                                        name='aw-toolkit-mesh-export-1')
        argv = ex.command('meshes/x/box.nif', ['original', 'current'])
        for flag in ('--network', 'none', '--read-only', '--pull', 'never', '--cap-drop', 'ALL', '--rm'):
            self.assertIn(flag, argv)
        self.assertTrue(any(a.startswith('type=bind,') and a.endswith('target=/data,readonly') for a in argv))
        self.assertTrue(any(a.startswith('type=bind,') and a.endswith('target=/src,readonly') for a in argv))
        with self.assertRaises(ValueError):
            ex.export('meshes/../x.nif', ['original'])
        with self.assertRaises(ValueError):
            toolkit_serve.MeshExporter(self.tmp.name, self.cache, image='bad image;rm')

    def test_server_options(self):
        with self.assertRaises(SystemExit):
            toolkit_serve.main(['--mesh-data-files', self.tmp.name])            # no cache to export into
        with self.assertRaises(SystemExit):
            toolkit_serve.main(['--mesh-cache', str(self.cache), '--mesh-docker', 'amiwind-builder:local'])


class PageTests(unittest.TestCase):
    def test_page_has_the_header_and_the_shared_controls(self):
        html = (ROOT / 'amiwind-toolkit' / 'mesh-compare.html').read_text(encoding='utf-8')
        self.assertIn('<script src="header.js"></script>', html)
        self.assertIn("AmiWindToolkitHeader.mount('Mesh Compare')", html)
        self.assertIn('<script src="view-camera.js"></script>', html)
        self.assertLess(html.index('view-camera.js'), html.index('<script>\n'))  # loaded before the page's script
        self.assertNotIn('method:', html)                                      # every fetch is a plain GET
        index = (ROOT / 'amiwind-toolkit' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<button role="tab" id="tab-meshes" aria-selected="false">Mesh Compare</button>', index)
        self.assertIn("'mesh-compare.html'", index)

    @unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
    def test_page_on_a_synthetic_cube(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / 'cube.obj'
            fixture.write_text(CUBE_OBJ, encoding='utf-8', newline='\n')
            out = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / 'test_mesh_compare.js'),
                                  str(ROOT / 'amiwind-toolkit' / 'mesh-compare.html'), str(fixture)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        page = json.loads(out.stdout)
        self.assertEqual((page['faces'], page['vertices'], page['triangles'], page['bad']), (6, 8, 12, 1))
        self.assertEqual(page['countsA'], {'faces': '6', 'vertices': '8'})
        self.assertEqual(page['countsB'], {'faces': '6', 'vertices': '8'})
        self.assertEqual(page['edges'], 12)                                    # polygon edges, each once (no diagonals)
        self.assertAlmostEqual(page['pivotAfterReset'][0], 0.5)
        self.assertTrue(page['linked'])                                        # both views drew the same camera
        self.assertEqual(page['linesOff'], 0)
        self.assertEqual(page['linesOn'], 2)                                   # wireframe: one line pass per view
        self.assertAlmostEqual(page['flown'], page['expectedFlight'], places=6)
        self.assertAlmostEqual(page['flownSlow'], page['expectedFlight'] / 4, places=6)
        self.assertTrue(page['orbitMoved'])
        self.assertAlmostEqual(page['orbitRadius'][0], page['orbitRadius'][1], places=6)
        self.assertLess(page['dollied'], page['orbitRadius'][1])
        self.assertTrue(page['panKeptOffset'])


if __name__ == '__main__':
    unittest.main()
