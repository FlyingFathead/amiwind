# SPDX-License-Identifier: GPL-3.0-only
"""Map metrics layer (tools/world_metrics.py) from a synthetic world estimate table."""
import csv
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import world_metrics as wm  # noqa: E402

HEAP = 11534336


def row(ident, space='exterior', cells='', refs=10, heap=HEAP // 2, texinfo=100, set_='vvardenfell', **extra):
    r = {'map': ident, 'set': set_, 'space': space, 'name': 'Synthetic ' + ident, 'mw_region': '', 'frame': 'f0',
         'core_cells': cells, 'refs_total': refs, 'npc': 1, 'creatures': 2, 'lights': 3,
         'cur_heap': heap - 1000, 'evr_heap': heap, 'cur_faces': 1000, 'evr_faces': 2000,
         'cur_texinfo': texinfo, 'evr_texinfo': texinfo, 'cur_nodes': 10, 'evr_nodes': 20,
         'cur_clipnodes': 30, 'evr_clipnodes': 40, 'cur_marksurfaces': 5, 'evr_marksurfaces': 6,
         'cur_vertexes': 7, 'evr_vertexes': 8, 'cur_edicts': 50, 'evr_edicts': 60,
         'cur_inline_models': 4, 'evr_inline_models': 5, 'cur_flames': 0, 'evr_flames': 1}
    r.update(extra)
    return r


ROWS = [
    row('w000', cells='0,0 1,0', heap=HEAP + 1),                 # over budget, two core cells
    row('w001', cells='0,0', heap=HEAP // 2, texinfo=40000),       # over texinfo today, not planned
    row('w002', cells='1,0', heap=int(HEAP * .55)),
    row('w003', cells='5,5', refs=0, heap=HEAP * 3),               # sea only: left out
    row('b000', cells='-20,20', set_='bloodmoon', heap=int(HEAP * .95), lights=40),
    row('i0001', space='interior', heap=HEAP * 2, cur_heap=HEAP // 2, refs=5),
    row('ti0001', space='interior', set_='tribunal', heap=HEAP // 3, refs=5),
    row('i0002', space='interior', refs=0),
]


class ConvertTests(unittest.TestCase):
    def setUp(self):
        self.layer = wm.convert(ROWS)
        self.cells = {(c['x'], c['y']): c for c in self.layer['cells']}

    def test_cells_take_the_worst_region_of_their_core(self):
        self.assertEqual(self.layer['format'], 'aw-world-metrics-1')
        self.assertEqual(set(self.cells), {(0, 0), (1, 0), (-20, 20)})
        c00 = self.cells[(0, 0)]
        self.assertEqual(c00['regions'], ['w000', 'w001'])
        self.assertEqual(c00['worst']['evr']['heap'], [HEAP + 1, round((HEAP + 1) / HEAP, 4), 'w000'])
        self.assertEqual(c00['worst']['evr']['texinfo'][2], 'w001')
        self.assertEqual(self.cells[(1, 0)]['worst']['evr']['heap'][2], 'w000')
        self.assertEqual(self.cells[(1, 0)]['worst']['cur']['heap'][0], HEAP + 1 - 1000)
        self.assertEqual(self.layer['regions']['w000']['cells'], [[0, 0], [1, 0]])
        self.assertNotIn('w003', self.layer['regions'])

    def test_sets_interiors_and_summary(self):
        self.assertEqual(self.cells[(-20, 20)]['set'], 'bloodmoon')
        self.assertEqual([i['id'] for i in self.layer['interiors']], ['i0001', 'ti0001'])
        s = self.layer['summary']
        self.assertEqual((s['cells'], s['regions'], s['interiors'], s['bloodmoon_cells']), (3, 4, 2, 1))
        self.assertEqual(s['skipped'], {'exterior_without_objects': 1, 'interior_without_objects': 1, 'other': 0})
        heap = s['over']['evr']['heap']
        self.assertEqual((heap['cells'], heap['regions'], heap['interiors']), (2, 1, 1))
        self.assertEqual(s['over']['cur']['heap']['interiors'], 0)
        self.assertEqual(s['over']['evr']['texinfo']['cells'], 1)
        self.assertEqual(s['over']['evr']['lights']['cells'], 1)      # 40 lights > MAX_DLIGHTS 32
        self.assertEqual(self.layer['regions']['b000']['evr']['lights'], 40)

    def test_texinfo_limit_is_selectable(self):
        planned = wm.convert(ROWS, texinfo='planned')
        self.assertEqual(planned['limits']['texinfo']['limit'], 65535)
        self.assertEqual(planned['limits']['texinfo']['choices'], {'today': 32767, 'planned': 65535})
        self.assertEqual(planned['summary']['over']['evr']['texinfo']['cells'], 0)
        self.assertEqual(self.layer['limits']['texinfo']['limit'], 32767)
        with self.assertRaises(ValueError):
            wm.convert(ROWS, texinfo='never')

    def test_missing_optional_columns_are_tolerated(self):
        bare = [{'map': 'w9', 'space': 'exterior', 'core_cells': '2,3', 'evr_heap': '100'},
                {'map': 'i9', 'space': 'interior', 'name': 'Room'}]
        layer = wm.convert(bare)
        cell = layer['cells'][0]
        self.assertEqual(cell['worst']['evr']['heap'][0], 100)
        self.assertNotIn('faces', cell['worst']['evr'])
        self.assertIsNone(layer['regions']['w9']['cur']['heap'])
        self.assertEqual(layer['interiors'][0]['evr']['heap'], None)
        with self.assertRaises(ValueError):
            wm.convert([{'map': 'w8', 'space': 'exterior', 'core_cells': 'x'}])

    def test_csv_and_json_tables_give_the_same_layer(self):
        keys = []
        for r in ROWS:
            keys += [k for k in r if k not in keys]
        buf = io.StringIO()
        w = csv.DictWriter(buf, keys, lineterminator='\n')
        w.writeheader()
        w.writerows(ROWS)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / 'metrics.csv').write_bytes(buf.getvalue().encode('utf-8'))
            (t / 'metrics.json').write_bytes(json.dumps({'limits': {}, 'rows': ROWS}).encode('utf-8'))
            a, b = wm.convert_file(t / 'metrics.csv'), wm.convert_file(t / 'metrics.json')
            self.assertEqual(a['source']['rows'], len(ROWS))
            a.pop('source'), b.pop('source')
            self.assertEqual(a, b)
            out = t / 'layer.json'
            self.assertEqual(wm.main([str(t / 'metrics.json'), '--out', str(out), '--texinfo-limit', 'planned']), 0)
            raw = out.read_bytes()
            self.assertNotIn(b'\r', raw)
            self.assertTrue(raw.endswith(b'}\n'))
            again = wm.load_any(out)
            self.assertEqual(again['limits']['texinfo']['choice'], 'planned')
            self.assertEqual(again['format'], wm.FORMAT)
            (t / 'other.json').write_text('{"format": "x"}', encoding='utf-8')
            with self.assertRaises(ValueError):
                wm.load_any(t / 'other.json')


class LimitTests(unittest.TestCase):
    """The layer's limits are the engine's and the builder's own constants."""

    def define(self, path, name):
        text = (ROOT / path).read_text(encoding='utf-8')
        return int(re.search(r'#define\s+%s\s+(\d+)' % name, text).group(1))

    def test_limits_match_the_sources(self):
        lim = {k: v['limit'] for k, v in wm.limits_table().items()}
        self.assertEqual(lim['heap'], self.define('engine/aga/src/sys_amiga.c', 'AMIWIND_HEAP_MB') * 1024 * 1024)
        self.assertEqual(lim['heap'], HEAP)
        self.assertEqual(lim['faces'], self.define('engine/aga/src/bspfile.h', 'MAX_MAP_FACES'))
        self.assertEqual(lim['marksurfaces'], self.define('engine/aga/src/bspfile.h', 'MAX_MAP_MARKSURFACES'))
        self.assertEqual(lim['vertexes'], self.define('engine/aga/src/bspfile.h', 'MAX_MAP_VERTS'))
        self.assertEqual(lim['nodes'], self.define('engine/aga/src/bspfile.h', 'MAX_MAP_NODES'))
        self.assertEqual(lim['edicts'], self.define('engine/aga/src/quakedef.h', 'MAX_EDICTS'))
        self.assertEqual(lim['lights'], self.define('engine/aga/src/client.h', 'MAX_DLIGHTS'))
        self.assertEqual(lim['flames'], self.define('engine/aga/src/aw_guard_torch.c', 'STATIC_FLAME_MAX'))
        self.assertIn('count>65520', (ROOT / 'engine/aga/src/model.c').read_text(encoding='utf-8'))
        self.assertEqual(lim['clipnodes'], 65520)
        self.assertIn("['unique_models']>220", (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8'))
        self.assertEqual(lim['inline_models'], 220)
        self.assertEqual((lim['texinfo'], wm.TEXINFO_LIMITS['planned']), (32767, 65535))


class ServeMetricsTests(unittest.TestCase):
    def test_metrics_endpoint_serves_the_layer_or_nothing(self):
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer
        import toolkit_serve as ts
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / 'metrics.json').write_bytes(json.dumps({'rows': ROWS}).encode('utf-8'))
            (t / 'world-metrics.json').write_text('{"format": "planted"}', encoding='utf-8')
            ts.Handler.data_dir, ts.Handler.maps_dir = t, None
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
                ts.Handler.metrics = None    # no --metrics: no layer, and never the data folder's file
                self.assertEqual(get('/data/world-metrics.json')[0], 404)
                ts.Handler.metrics = ts.load_metrics(t / 'metrics.json')     # raw table, converted
                status, body = get('/data/world-metrics.json')
                self.assertEqual(status, 200)
                layer = json.loads(body)
                self.assertEqual(layer['format'], 'aw-world-metrics-1')
                self.assertEqual(layer['summary']['cells'], 3)
                out = t / 'layer.json'
                wm.main([str(t / 'metrics.json'), '--out', str(out)])
                self.assertEqual(ts.load_metrics(out), out.read_bytes())    # a layer file as is
            finally:
                ts.Handler.metrics = None
                server.shutdown()
                server.server_close()


class LayerPageTests(unittest.TestCase):
    def test_world_map_layer_javascript(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable; the World Map layer checks need an existing interpreter')
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / 'layer.json'
            fixture.write_bytes(wm.dumps(wm.convert(ROWS)).encode('utf-8'))
            result = subprocess.run([node, str(ROOT / 'tests/test_world_metrics_layer.js'),
                                     str(ROOT / 'amiwind-toolkit/world-map.html'), str(fixture)],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for milestone in ('PASS metrics hidden without a layer', 'PASS metrics colours and counts',
                          'PASS metrics hover and panel', 'PASS metrics interiors table', 'PASS metrics state'):
            self.assertIn(milestone, result.stdout)


if __name__ == '__main__':
    unittest.main()
