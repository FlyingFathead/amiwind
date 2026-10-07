# SPDX-License-Identifier: GPL-3.0-only
"""World progress table and viewer, on synthetic inputs (no game data)."""
from pathlib import Path
import json
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_progress as wp  # noqa: E402


def awr(origins, towns=2):
    out = b'AWR2' + struct.pack('<I', len(origins)) + struct.pack('<7f', *([0.0] * 7)) * towns
    for i, (x, y) in enumerate(origins):
        out += struct.pack('<8s11f', b'vf%04d' % i, x, y, 0, -256, -256, 256, 256, -300, -300, 300, 300)
    return out


ENTITIES = {
    'master_sha256': 'sha',
    'converted_cells': ['exterior:0,0', 'exterior:1,0', 'interior:Town, Shop'],
    'full_cells': ['exterior:0,0', 'interior:Town, Shop'],
    'cells': {'exterior:0,0': {'static': [10, 9], 'npc': [2, 2]}, 'exterior:1,0': {'rock': [5, 5], 'static': [4, 0]},
              'exterior:5,5': {'static': [3, 0]}, 'interior:Town, Shop': {'item': [7, 0]}},
}
PLACES = [
    {'kind': 'exterior place', 'name': 'Secret Town Name', 'region': 'r', 'grids': [[0, 0], [1, 0]], 'converted': False},
    {'kind': 'shop', 'name': 'Town, Shop', 'region': 'r', 'entrances': [{'grid': [0, 0]}], 'reached_through': None,
     'converted': True},
    {'kind': 'cave', 'name': 'Town, Shop, Cellar', 'region': 'r', 'entrances': [], 'reached_through': 'Town, Shop',
     'converted': False},
]


class TerrainTests(unittest.TestCase):
    def test_region_table_gives_terrain_cells(self):
        data = awr([(1024, 1024), (512, 1536), (-1024, 3072), (2048 + 100, -10)])
        self.assertEqual(wp.terrain_cells(data), {(0, 0), (-1, 1), (1, -1)})

    def test_bad_tables_are_rejected(self):
        with self.assertRaises(ValueError):
            wp.terrain_cells(b'AWR1' + awr([(0, 0)])[4:])
        with self.assertRaises(ValueError):
            wp.terrain_cells(awr([(0, 0)]) + b'x')


class ToolkitVersionTests(unittest.TestCase):
    def test_toolkit_names_the_version_it_was_last_updated_with(self):
        # The AmiWind version the Toolkit was last updated with, set by hand; it
        # never follows VERSION automatically, but it cannot name a newer one.
        root = Path(__file__).resolve().parents[1]
        page = (root / 'amiwind-toolkit' / 'index.html').read_text(encoding='utf-8')
        found = re.search(r'id="toolkit-version"[^>]*>Last updated with AmiWind v(\d+)\.(\d+)\.(\d+)<', page)
        self.assertTrue(found, 'Toolkit header must name the AmiWind version it was last updated with')
        current = tuple(int(n) for n in (root / 'VERSION').read_text().strip().split('-')[0].split('.'))
        self.assertLessEqual(tuple(int(n) for n in found.groups()), current)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.result = wp.build(ENTITIES, PLACES, {'cells': [[1, 0]]}, {(0, 0), (1, 0), (2, 0)})
        self.cells = {(c['x'], c['y']): c for c in self.result['cells']}

    def test_topomap_is_the_basis_and_full_maps_sit_on_it(self):
        self.assertEqual([self.cells[k]['map'] for k in ((0, 0), (1, 0), (2, 0), (5, 5))],
                         ['full', 'terrain', 'terrain', 'none'])
        self.assertEqual(self.result['summary']['terrain'], 3)

    def test_counts_places_interiors_and_checked(self):
        c = self.cells[(0, 0)]
        self.assertEqual((c['original'], c['placed'], c['places'], c['interiors'], c['interiors_converted']),
                         (12, 11, 1, 2, 1))
        self.assertTrue(self.cells[(1, 0)]['checked'])
        self.assertEqual(self.result['bounds'], [0, 0, 5, 5])

    def test_no_place_names_in_the_output(self):
        text = json.dumps(self.result)
        for p in PLACES:
            self.assertNotIn(p['name'], text)

    def test_cli_writes_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / 'regions.awr').write_bytes(awr([(1024, 1024)]))
            (t / 'entities.json').write_text(json.dumps(ENTITIES))
            self.assertEqual(wp.main(['--regions', str(t / 'regions.awr'), '--entities', str(t / 'entities.json'),
                                      '--out', str(t / 'out.json')]), 0)
            self.assertEqual(json.loads((t / 'out.json').read_text())['format'], wp.FORMAT)


class BuildStepTests(unittest.TestCase):
    def test_build_step_writes_the_table_from_master_regions_and_entities(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_entity_tracker import MASTER
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / 'master.esm').write_bytes(MASTER)
            (t / 'regions.awr').write_bytes(awr([(1024, 1024), (3072, 1024)]))
            (t / 'entity-tracker.json').write_text(json.dumps(ENTITIES))
            record = wp.build_step(t, t / 'regions.awr', t / 'entity-tracker.json', t / 'master.esm', t / 'none.json')
            table = json.loads((t / 'world-progress.json').read_text())
            self.assertEqual(record['summary'], table['summary'])
            self.assertEqual(table['summary']['terrain'], 2)
            self.assertNotIn('Town', (t / 'world-progress.json').read_text())


class BuildHookTests(unittest.TestCase):
    def test_image_build_writes_world_progress_after_the_entity_gate(self):
        source = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image(args):'):source.index('\ndef main():')]
        gate, step = finalize.index('entity_gate(out, boot/'), finalize.index('world_progress_step(out,')
        self.assertLess(gate, step)
        self.assertLess(step, finalize.index("part=out/'partition.hdf'"))
        self.assertIn("boot/'id1/world/regions.awr'", finalize[step:step + 300])
        self.assertIn("build_record['world_progress'] = world_progress", finalize)


class ToolkitTests(unittest.TestCase):
    KIT = ROOT / 'amiwind-toolkit'

    def test_toolkit_pages_are_self_contained(self):
        for page in ('index.html', 'world-map.html'):
            html = (self.KIT / page).read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'(src|href)\s*=\s*["\']https?:', html), page)
            for target in re.findall(r"fetch\(\s*'([^']*)'", html):
                self.assertTrue(target.startswith(('../data/', '../maps/')), (page, target))
        index = (self.KIT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<title>AmiWind Toolkit</title>', index)
        for target in re.findall(r'(?:src|href)="([^"#]+)"', index):
            self.assertTrue((self.KIT / target).resolve().is_file(), target)

    def test_inspector_accepts_maps_only_from_its_toolkit_window(self):
        html = (self.KIT / 'map-inspector.html').read_text(encoding='utf-8')
        self.assertIn("(e.source===window.parent||e.source===window.opener)&&e.data&&e.data.type==='amiwind-open-map'"
                      "&&e.data.file instanceof File", html)
        self.assertIn("$('file').onchange=()=>openFile($('file').files[0]);", html)

    def test_old_inspector_link_redirects(self):
        stub = (ROOT / 'tools' / 'polycount_inspector.html').read_text(encoding='utf-8')
        self.assertIn('url=../amiwind-toolkit/map-inspector.html', stub)
        self.assertLess(len(stub), 1024)

    def test_toolkit_files_ship_in_release(self):
        shipped = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for name in ('amiwind-toolkit/index.html', 'amiwind-toolkit/world-map.html', 'amiwind-toolkit/map-inspector.html',
                     'tools/polycount_inspector.html', 'resources/media/AmiWind_logo_name_only.png',
                     'docs/AMIWIND_TOOLKIT.md'):
            self.assertIn(name, shipped)
            self.assertTrue((ROOT / name).is_file(), name)


class ServeTests(unittest.TestCase):
    """tools/toolkit_serve.py: this machine only, read-only, only the files it is given."""

    def test_serves_toolkit_data_and_maps_and_refuses_everything_else(self):
        import threading, urllib.error, urllib.request
        from http.server import ThreadingHTTPServer
        import toolkit_serve as ts
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp); (t / 'data').mkdir(); (t / 'maps').mkdir()
            (t / 'data' / 'world-progress.json').write_text('{"format": "x"}')
            (t / 'data' / 'secret.txt').write_text('no')
            (t / 'maps' / 'bm003.bsp').write_bytes(b'BSP!')
            ts.Handler.data_dir, ts.Handler.maps_dir = t / 'data', t / 'maps'
            server = ThreadingHTTPServer(('127.0.0.1', 0), ts.Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = 'http://127.0.0.1:%d' % server.server_address[1]

            def get(path):
                try:
                    with urllib.request.urlopen(base + path) as r:
                        return r.status, r.read()
                except urllib.error.HTTPError as e:
                    return e.code, b''
            try:
                self.assertEqual(server.server_address[0], '127.0.0.1')
                self.assertEqual(get('/data/world-progress.json'), (200, b'{"format": "x"}'))
                self.assertEqual(get('/maps/bm003.bsp'), (200, b'BSP!'))
                self.assertEqual(json.loads(get('/maps/index.json')[1]), ['bm003'])
                self.assertEqual(get('/amiwind-toolkit/index.html')[0], 200)
                self.assertEqual(get('/data/secret.txt')[0], 404)
                self.assertEqual(get('/data/..%2F..%2Ftools%2Ftoolkit_serve.py')[0], 400)
                self.assertEqual(get('/tools/toolkit_serve.py')[0], 404)
            finally:
                server.shutdown(); server.server_close()


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')

    def test_viewer_is_self_contained(self):
        self.assertIsNone(re.search(r'(src|href)\s*=\s*["\']https?:', self.html))
        for target in re.findall(r"fetch\(\s*'([^']*)'", self.html):
            self.assertTrue(target.startswith(('../data/', '../maps/')), target)

    def test_viewer_reads_this_format_and_only_draw_resizes(self):
        self.assertIn(wp.FORMAT, self.html)
        # TRACKER-MAP-BLANK-31: resizing clears the canvas, so only draw() may do it.
        resizes = [m.start() for m in re.finditer(r'canvas\.width\s*=', self.html)]
        draw = self.html.index('function draw()')
        self.assertEqual(len(resizes), 1)
        self.assertGreater(resizes[0], draw)
        self.assertLess(resizes[0], self.html.index('\n}\n', draw))


if __name__ == '__main__':
    unittest.main()
