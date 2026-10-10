# SPDX-License-Identifier: GPL-3.0-only
"""CHIM Progress Tracker (tools/cell_progress.py): schema, sweep orders, audits, results, interiors tree, serving.

Every fixture is synthetic: made-up cell names, numbers and meshes. No game data.
"""
import json
import re
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
import cell_progress as cp  # noqa: E402
import cell_progress_chim as ch  # noqa: E402
import cell_progress_order as order  # noqa: E402
import toolkit_serve as ts  # noqa: E402

NOW = '2026-10-09T05:00:00+03:00'
LAND = [(x, y) for x in range(5) for y in range(5)]     # a 5 x 5 island, cells 0..4


def metrics_layer(cells=LAND, risk=None):
    """A minimal aw-world-metrics-1 layer: every cell has the same small values unless `risk` says otherwise."""
    risk = risk or {}
    limits = {'heap': {'limit': 1000}, 'faces': {'limit': 100}, 'lights': {'limit': 32}}
    out = []
    for x, y in cells:
        r = risk.get((x, y), 0.3)
        w = {'heap': [int(1000 * r), r, 'r%d%d' % (x, y)], 'faces': [int(100 * r / 2), r / 2, 'r%d%d' % (x, y)],
             'lights': [5, 5 / 32, 'r%d%d' % (x, y)]}
        out.append({'x': x, 'y': y, 'set': 'vvardenfell', 'regions': ['r%d%d' % (x, y)], 'worst': {'cur': w, 'evr': w}})
    regions = {'r%d%d' % (x, y): {'cells': [[x, y]], 'refs_total': 4, 'npc': 1, 'creatures': 0, 'lights': 1,
                                  'load_doors': 0, 'refs_items': 0} for x, y in cells}
    interiors = [{'id': 'i0001', 'name': 'Synthetic Hall', 'set': 'vvardenfell', 'refs_total': 9, 'npc': 2, 'creatures': 0,
                  'lights': 3, 'load_doors': 2, 'cur': {'faces': 50}, 'evr': {'faces': 50, 'heap': 400}},
                 {'id': 'i0002', 'name': 'Synthetic Cellar', 'set': 'vvardenfell', 'refs_total': 3, 'npc': 0, 'creatures': 0,
                  'lights': 1, 'load_doors': 1, 'cur': {}, 'evr': {'faces': 20}},
                 {'id': 'i0003', 'name': 'Synthetic Vault', 'set': 'vvardenfell', 'refs_total': 3, 'npc': 0, 'creatures': 0,
                  'lights': 1, 'load_doors': 1, 'cur': {}, 'evr': {'faces': 20}}]
    return {'format': 'aw-world-metrics-1', 'cells': out, 'regions': regions, 'interiors': interiors,
            'limits': limits}


def progress_doc(cells=LAND):
    return {'format': 'AW-WORLD-PROGRESS2', 'cells': [
        {'x': x, 'y': y, 'map': 'full' if (x, y) == (2, 2) else 'terrain', 'placed': 3 if (x, y) == (2, 2) else 0,
         'original': 4, 'places': 0, 'interiors': 1, 'interiors_converted': 0, 'checked': False, 'maps': []} for x, y in cells]}


def census_doc():
    """Meshes 0..5; the cell (0,0) holds 0,1 ; (1,0) holds 1,2 ; (2,2) holds 0,3,4 ; the rest hold mesh 5 only."""
    holds = {(0, 0): [0, 1], (1, 0): [1, 2], (2, 2): [0, 3, 4]}
    cells = {}
    for x, y in LAND:
        cells['%d,%d' % (x, y)] = {'counts': {'STAT': 2, 'DOOR': 1}, 'placements': 3, 'flora': 0,
                                   'meshes': holds.get((x, y), [5]), 'doors': []}
    cells['2,2']['doors'] = [{'ref': 77, 'object': 'door_a', 'pos': [100, 200, 300], 'to': 'Synthetic Hall'}]
    cells['0,0']['doors'] = [{'ref': 5, 'object': 'door_b', 'pos': [1, 2, 3], 'to': 'Synthetic Vault'}]
    ints = {
        'synthetic hall': {'name': 'Synthetic Hall', 'set': 'vvardenfell', 'counts': {'STAT': 5, 'LIGH': 3, 'LOAD_DOOR': 2},
                           'placements': 5, 'unique_meshes': 4,
                           'doors': [{'ref': 10, 'object': 'd1', 'pos': [0, 0, 0], 'to': ''},
                                     {'ref': 11, 'object': 'd2', 'pos': [1, 1, 1], 'to': 'Synthetic Cellar'}]},
        'synthetic cellar': {'name': 'Synthetic Cellar', 'set': 'vvardenfell', 'counts': {'STAT': 2, 'LOAD_DOOR': 1},
                             'placements': 2, 'unique_meshes': 2,
                             'doors': [{'ref': 12, 'object': 'd3', 'pos': [2, 2, 2], 'to': 'Synthetic Hall'},      # a loop
                                       {'ref': 13, 'object': 'd4', 'pos': [3, 3, 3], 'to': 'Synthetic Vault'}]},
        'synthetic vault': {'name': 'Synthetic Vault', 'set': 'vvardenfell', 'counts': {'STAT': 1, 'LOAD_DOOR': 1},
                            'placements': 1, 'unique_meshes': 1,
                            'doors': [{'ref': 14, 'object': 'd5', 'pos': [4, 4, 4], 'to': ''}]},
    }
    return {'format': cp.CENSUS_FORMAT, 'masters': {}, 'meshes': ['meshes/a.nif', 'meshes/b.nif', 'meshes/c.nif',
            'meshes/d.nif', 'meshes/e.nif', 'meshes/f.nif'], 'land': ['%d,%d' % c for c in LAND], 'land_bloodmoon': [],
            'cells': cells, 'interiors': ints, 'names': {'2,2': {'name': 'Synthetic Town', 'region': 'Synthetic Region'}},
            'lights_census': 'aw-cell-lighting-1'}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj) + '\n').encode('utf-8'))


def chim_run(folder, stairs_fail_at=None, heap_ok=True, validate_ok=True):
    """A synthetic CHIM run folder: one frame in cell (2,2); the chunks are owned in (2,2) only."""
    frame = {'cell': [2, 2], 'centre': [2 * 8192 + 4096.0, 2 * 8192 + 4096.0], 'grain': 256, 'low': [-1024.0, -1024.0],
             'nx': 8, 'ny': 8}
    path = ch.frame_path(frame['cell'])
    write(folder / 'chim-receipt.json', {'areas': ['synthetic'], 'builder': 'chim', 'chim_version': '9.9.9',
                                         'frames': [{'frame': frame, 'placements': 3}], 'placements': 3, 'models': 2})
    per = [{'frame': path, 'cell': [i, j], 'owned': 1, 'terrain_faces': 10, 'placed_faces': 20, 'bytes': 100}
           for i in range(8) for j in range(8)]
    write(folder / 'chim-stats.json', {'chim_version': '9.9.9', 'world_format': '0.5', 'chunks': {'per_chunk': per},
                                       'build': {'cpu_seconds': 12.5}, 'memory': {'model_zone_peak_bytes': 4096},
                                       'disk': {'bytes': 6400}})
    write(folder / 'chim-validate.json', {'ok': validate_ok, 'failure_count': 0 if validate_ok else 3})
    fails = []
    if stairs_fail_at:
        fails = [{'map': path, 'point': [stairs_fail_at[0], stairs_fail_at[1], 0.0], 'kind': 'step'}]
    write(folder / 'chim-stairs.json', {'status': 'failed' if fails else 'passed', 'failures': fails,
                                        'advisory_failures': [], 'tested': 10})
    write(folder / 'chim-heap.json', {'ok': heap_ok, 'status': 'passed' if heap_ok else 'failed',
                                      'frames': [{'frame': path, 'ok': heap_ok, 'peak_bytes': 500, 'budget_bytes': 1000,
                                                  'headroom_bytes': 500}]})


def ingest(out, runs=(), **kw):
    kw.setdefault('progress', progress_doc())
    kw.setdefault('metrics', metrics_layer())
    kw.setdefault('census', census_doc())
    return cp.ingest(Path(out), chim_runs=list(runs), now=NOW, **kw)


class OrderTests(unittest.TestCase):
    def test_rings_peel_the_island_from_the_coast(self):
        r = order.rings(set(LAND))
        self.assertEqual(r[(0, 0)], 1)
        self.assertEqual(r[(1, 0)], 1)
        self.assertEqual(r[(1, 1)], 2)
        self.assertEqual(r[(2, 2)], 3)
        self.assertEqual(max(r.values()), 3)

    def test_spiral_visits_every_land_cell_once_coast_first_and_stays_contiguous(self):
        sp = order.spiral(set(LAND))
        cells = [c for c, _, _ in sp]
        self.assertEqual(sorted(cells), sorted(LAND))
        rings = [k for _, k, _ in sp]
        self.assertEqual(rings, sorted(rings), 'outer rings first')
        outer = [c for c, k, _ in sp if k == 1]
        for a, b in zip(outer, outer[1:]):
            self.assertLessEqual(max(abs(a[0] - b[0]), abs(a[1] - b[1])), 1, 'the walk along a ring never jumps')
        self.assertEqual(sp[-1][0], (2, 2), 'the centre is last')

    def test_sea_only_cells_with_content_come_first_as_ring_zero(self):
        sp = order.spiral(set(LAND), {(9, 9), (0, 0)})
        self.assertEqual(sp[0], ((9, 9), 0, 1))
        self.assertEqual(len(sp), len(LAND) + 1)

    def test_groups_keep_touching_land_as_separate_islands(self):
        land = {(0, 0), (1, 0), (2, 0), (3, 0)}
        sp = order.spiral(land, (), {(2, 0): 'b', (3, 0): 'b'})
        self.assertEqual({i for _, _, i in sp}, {1, 2})
        self.assertEqual({k for _, k, _ in sp}, {1})   # each piece is all coast

    def test_reuse_curve_counts_new_and_reused_meshes(self):
        meshes = {(0, 0): {1, 2}, (1, 0): {2, 3}, (2, 0): {1}}
        c = order.reuse_curve([(0, 0), (1, 0), (2, 0)], meshes, {(0, 0): (1, 1), (1, 0): (1, 1), (2, 0): (1, 2)})
        self.assertEqual([p[1] for p in c['points']], [2, 3, 3])
        self.assertEqual([p[2] for p in c['points']], [2, 4, 5])
        self.assertEqual(c['cells_without_new_mesh'], 1)
        self.assertEqual(c['rings'][0]['new_meshes'], 3)

    def test_curve_png_is_written(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest('Pillow not installed')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'c.png'
            order.draw_curve(p, [('a', [[1, 1, 2], [2, 2, 4]], '#fff', 1, False), ('b', [[1, 1, 2], [2, 2, 4]], '#888', 2, True)],
                             'test', [(1, 'ring 1')])
            self.assertEqual(p.read_bytes()[:4], b'\x89PNG')


    def test_reuse_chart_title_is_the_takeaway_and_the_png_is_written(self):
        title, ratio = order.reuse_takeaway(1777, 38790)
        self.assertEqual(title, 'Store-once: 1,777 mesh conversions instead of 38,790 (22x fewer)')
        self.assertAlmostEqual(ratio, 21.8, 1)
        self.assertIn('2.5x fewer', order.reuse_takeaway(100, 250)[0])
        self.assertIsNone(order.reuse_takeaway(0, 0)[1])
        self.assertIn('Risk order meets the most distinct meshes first', order.ORDER_SENTENCE)
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest('Pillow not installed')
        from PIL import Image
        pts = [[i, min(i, 5) + i // 4, i * 3] for i in range(1, 40)]
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'chart.png'
            order.draw_reuse_chart(p, pts, pts, 14, 117, [(5, 'ring 1'), (20, 'ring 3'), (30, 'island 2 ring 1')], 39)
            self.assertEqual(p.read_bytes()[:4], b'\x89PNG')
            width, height = Image.open(p).size
            self.assertGreaterEqual(width, 1400)        # big: the text is 18-34 px
            self.assertGreaterEqual(height, 1100)

    def test_world_map_mesh_chart_has_the_takeaway_and_big_text_outside_the_plot(self):
        page = (ROOT / 'amiwind-toolkit' / 'world-map.html').read_text(encoding='utf-8')
        for needle in ("'Store-once: ' + n(unique) + ' mesh conversions instead of '", 'meshlegend', 'MESH_SENTENCE', 'log scale',
                       'cells converted (in sweep order)', "'14px system-ui", 'staggered over two rows', 'meshes converted'):
            self.assertIn(needle, page, needle)
        self.assertIn('#chimpanel .meshtitle{font-size:20px', page)
        self.assertNotIn('no reuse: every cell converts its own meshes (spiral order) (off the chart', page)


class IngestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / 'out'
        self.run = Path(self._tmp.name) / 'run'
        self.addCleanup(self._tmp.cleanup)

    def run_spec(self, name='syn'):
        return '%s=%s' % (name, self.run)

    def test_nothing_measured_is_never_guessed(self):
        doc = cp.ingest(self.out, progress=progress_doc(), now=NOW)     # only the legacy table: no metrics, no census
        h = doc['headline']
        self.assertEqual((h['passed'], h['converted'], h['not_started']), (0, 0, 25))
        c = doc['cells']['2,2']
        self.assertIsNone(c['risk'])
        self.assertIsNone(c['contents'])
        self.assertEqual(c['stats'], {})
        self.assertTrue(all(a['status'] == 'not_measured' for a in c['audits'].values()))
        self.assertEqual(c['legacy']['grade'], 'B')       # full map, but only 3 of 4 entities placed
        self.assertEqual(c['chim']['bucket'], 'not_started')
        self.assertFalse(doc['sources']['metrics'])
        self.assertIsNone(doc['mesh_curve'])

    def test_a_chim_run_converts_its_cell_and_audits_it_per_mechanism(self):
        chim_run(self.run)
        doc = ingest(self.out, [self.run_spec()], labels={'syn': 'Synthetic run'}, commits={'syn': 'abc1234'})
        c = doc['cells']['2,2']
        self.assertTrue(c['chim']['converted'])
        self.assertEqual(c['audits']['stair_walk']['status'], 'passed')
        self.assertEqual(c['audits']['memory_fit']['status'], 'passed')
        self.assertEqual(c['audits']['format_validation']['status'], 'passed')
        self.assertEqual(c['audits']['seam_tears']['status'], 'not_measured')     # no report: not measured, not passed
        self.assertEqual(c['chim']['bucket'], 'audits_passed')
        self.assertEqual(c['provenance']['chim_version'], '9.9.9')
        self.assertEqual(c['provenance']['world_format'], '0.5')
        self.assertEqual(c['provenance']['source_commit'], 'abc1234')
        self.assertEqual(c['stats']['chunks'], {'count': 64, 'bytes': 6400})
        self.assertEqual(c['stats']['faces'], {'chim_terrain': 640, 'chim_placed': 1280})
        self.assertEqual(c['stats']['memory']['frame_heap_peak_bytes'], 500)
        self.assertEqual(c['stats']['meshes'], {'unique': 3, 'new': 3, 'reused': 0,
                                                'source': 'derived from the original references, in conversion order'})
        h = doc['headline']
        self.assertEqual((h['passed'], h['land_cells'], h['audits_passed'], h['not_started']), (1, 25, 1, 24))
        self.assertEqual(h['with_unmeasured_audits'], 1)
        self.assertEqual(doc['runs'][0]['commit'], 'abc1234')

    def test_failing_audits_are_attributed_to_the_cell_and_never_counted_as_passed(self):
        chim_run(self.run, stairs_fail_at=(100.0, 100.0), heap_ok=False)
        doc = ingest(self.out, [self.run_spec()])
        c = doc['cells']['2,2']
        self.assertEqual(c['audits']['stair_walk']['status'], 'failed')
        self.assertEqual(c['audits']['memory_fit']['status'], 'failed')
        self.assertEqual(c['chim']['bucket'], 'converted_failing')
        self.assertFalse(c['chim']['successful'])
        self.assertEqual(doc['headline']['passed'], 0)
        self.assertEqual(doc['headline']['converted_failing'], 1)

    def test_a_cell_with_nothing_measured_is_converted_but_not_passed(self):
        write(self.run / 'chim-receipt.json',
              {'areas': ['x'], 'frames': [{'frame': {'cell': [1, 1], 'centre': [12288.0, 12288.0], 'grain': 256,
                                                     'low': [-512.0, -512.0], 'nx': 4, 'ny': 4}}]})
        doc = ingest(self.out, [self.run_spec()])
        c = doc['cells']['1,1']
        self.assertTrue(c['chim']['converted'])      # without stats the frame's own cell counts
        self.assertEqual(c['chim']['bucket'], 'converted_unmeasured')
        self.assertTrue(all(a['status'] == 'not_measured' for a in c['audits'].values()))
        self.assertEqual(doc['headline']['passed'], 0)
        self.assertEqual(doc['headline']['converted_unmeasured'], 1)

    def test_owner_verdicts_and_audit_records(self):
        chim_run(self.run)
        ingest(self.out, [self.run_spec()])
        cp.record_audit(self.out, 'seam_tears', 'syn', ['2,2'], 'passed', 'no tears', now=NOW)
        cp.record_audit(self.out, 'sprite_shape', 'syn', {'2,2': {'status': 'failed', 'detail': 'rectangle'}}, now=NOW)
        cp.record_audit(self.out, 'hidden_faces', 'an-older-build', ['2,2'], 'passed', now=NOW)    # stale: other build
        cp.record_owner(self.out, 'approved', ['2,2'], 'walked it', now=NOW)
        doc = ingest(self.out)
        c = doc['cells']['2,2']
        self.assertEqual(c['audits']['seam_tears']['status'], 'passed')
        self.assertEqual(c['audits']['sprite_shape']['status'], 'failed')
        self.assertEqual(c['audits']['hidden_faces']['status'], 'not_measured')
        self.assertTrue(c['audits']['hidden_faces']['stale'])
        self.assertEqual(c['chim']['bucket'], 'converted_failing', 'a failing audit beats the owner verdict')
        cp.record_audit(self.out, 'sprite_shape', 'syn', ['2,2'], 'accepted', 'owner accepted', now='2026-10-09T06:00:00+03:00')
        doc = ingest(self.out)
        self.assertEqual(doc['cells']['2,2']['chim']['bucket'], 'approved')
        self.assertEqual(doc['headline']['approved'], 1)
        self.assertEqual(doc['headline']['passed'], 1)
        with self.assertRaises(ValueError):
            cp.record_audit(self.out, 'nonsense', 'syn', ['2,2'], 'passed')
        with self.assertRaises(ValueError):
            cp.record_owner(self.out, 'perfect', ['2,2'])

    def test_ingest_is_idempotent(self):
        chim_run(self.run)
        a = ingest(self.out, [self.run_spec()])
        first = (self.out / 'cell-progress.json').read_bytes()
        nxt = (self.out / 'next.json').read_bytes()
        ingest(self.out, [self.run_spec()])
        ingest(self.out)         # digests alone give the same answer
        self.assertEqual((self.out / 'cell-progress.json').read_bytes(), first)
        self.assertEqual((self.out / 'next.json').read_bytes(), nxt)
        self.assertEqual(len((self.out / 'history.jsonl').read_text().splitlines()), 1)
        self.assertEqual(len(a['history']), 1)

    def test_history_gains_a_line_when_the_counts_change(self):
        ingest(self.out)
        chim_run(self.run)
        cp.ingest(self.out, progress_doc(), metrics_layer(), None, census_doc(), [self.run_spec()], now='2026-10-10T05:00:00+03:00')
        lines = [json.loads(x) for x in (self.out / 'history.jsonl').read_text().splitlines()]
        self.assertEqual([x['passed'] for x in lines], [0, 1])

    def test_sweep_orders_spiral_and_risk(self):
        risk = {(4, 4): 1.6, (1, 1): 0.9}
        doc = ingest(self.out, metrics=metrics_layer(risk=risk))
        cells = doc['cells']
        self.assertEqual(cells['0,0']['ring'], 1)
        self.assertEqual(cells['2,2']['ring'], 3)
        self.assertEqual(cells['2,2']['spiral_rank'], 25)
        self.assertEqual(cells['4,4']['risk_rank'], 1)
        self.assertEqual(cells['1,1']['risk_rank'], 2)
        self.assertEqual(cells['4,4']['risk']['limiting'], 'heap')
        self.assertEqual(cells['4,4']['risk']['over'], ['heap'])
        self.assertNotIn('lights', {cells['0,0']['risk']['limiting']})
        nxt = json.loads((self.out / 'next.json').read_text())
        self.assertEqual(nxt['risk']['cells'][0]['x'], 4)
        self.assertEqual(nxt['spiral']['cells'][0]['ring'], 1)
        self.assertEqual(nxt['not_started'], 25)

    def test_converted_cells_leave_the_next_lists(self):
        chim_run(self.run)
        ingest(self.out, [self.run_spec()])
        nxt = json.loads((self.out / 'next.json').read_text())
        for order_name in ('spiral', 'risk'):
            self.assertNotIn((2, 2), {(c['x'], c['y']) for c in nxt[order_name]['cells']})

    def test_mesh_first_numbers(self):
        doc = ingest(self.out, png=True)
        curve = json.loads((self.out / 'mesh-curve.json').read_text())
        self.assertEqual(curve['unique_meshes'], 6)
        self.assertEqual(curve['cells_with_meshes'], 25)
        self.assertEqual(curve['meshes_in_one_cell_only'], 3)       # meshes 2, 3 and 4 appear in one cell each
        self.assertEqual(curve['cells_that_own_a_mesh'], 2)
        self.assertEqual(curve['spiral']['points'][-1][1], 6)
        self.assertEqual(doc['mesh_curve']['unique_meshes'], 6)
        try:
            import PIL  # noqa: F401
            self.assertEqual((self.out / 'mesh-curve.png').read_bytes()[:4], b'\x89PNG')
        except ImportError:
            pass

    def test_bugs_are_linked_to_the_cells_of_their_area(self):
        chim_run(self.run)
        bugs = [{'id': 'SYN-1', 'title': 'Synthetic stairs hole', 'where': 'the synthetic town', 'state': 'open', 'tags': []},
                {'id': 'SYN-2', 'title': 'Something in cell 3, 3', 'where': '', 'state': 'fixed', 'tags': []},
                {'id': 'SYN-3', 'title': 'Unrelated', 'where': 'engine', 'state': 'open', 'tags': []}]
        areas = {'areas': {'synthetic': ['synthetic town']}}
        doc = ingest(self.out, [self.run_spec()], bugs=bugs, areas=areas)
        self.assertEqual(doc['cells']['2,2']['bugs'], ['SYN-1'])
        self.assertEqual(doc['cells']['3,3']['bugs'], ['SYN-2'])
        self.assertEqual(doc['cells']['0,0']['bugs'], [])
        self.assertEqual(doc['bugs']['SYN-2']['state'], 'fixed')

    def test_ledger_gives_the_last_build_time(self):
        chim_run(self.run)
        ledger = Path(self.out.parent) / 'ledger.jsonl'
        ledger.write_text(json.dumps({'run': '/vol/ws/build/syn', 'stage': 'chim', 'started_s': 10.0, 'wall_s': 50.0, 'version': 'x'}) + '\n' +
                          json.dumps({'run': '/vol/ws/build/syn', 'stage': 'image', 'started_s': 60.0, 'wall_s': 30.0}) + '\n')
        doc = ingest(self.out, [self.run_spec()], ledger=str(ledger))
        self.assertEqual(doc['cells']['2,2']['last_build']['elapsed_s'], 90.0)
        self.assertEqual(doc['cells']['2,2']['last_build']['chim_stage_s'], 50.0)
        self.assertIsNone(doc['cells']['0,0']['last_build'])


class ResultTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def result(self, **cells):
        return {'format': cp.RESULT_FORMAT, 'build': 'chimport-001', 'generated': NOW,
                'provenance': {'source_commit': 'def5678', 'chim_version': '0.1.0'}, 'cells': cells}

    def test_a_result_file_converts_cells_and_carries_stats_audits_and_errors(self):
        doc = self.result(**{'0,0': {'converted': True, 'audits': {'seam_tears': {'status': 'passed'},
                                                                   'stair_walk': {'status': 'failed', 'detail': '2 flights'}},
                                     'errors': ['one warning'],
                                     'stats': {'meshes': {'unique': 2, 'new': 2, 'reused': 0}, 'time': {'convert_s': 4.5},
                                               'hull': {'clipnodes': 800, 'max_depth': 4}, 'vis': {'entities_sent': 12}}},
                            '1,0': {'converted': False, 'errors': ['qbsp failed']},
                            '77,77': {'converted': True}})
        cp.record_result(self.out, doc)
        out = ingest(self.out)
        a, b = out['cells']['0,0'], out['cells']['1,0']
        self.assertTrue(a['chim']['converted'])
        self.assertEqual(a['provenance']['source_commit'], 'def5678')
        self.assertEqual(a['provenance']['build'], 'chimport-001')
        self.assertEqual(a['audits']['stair_walk']['status'], 'failed')
        self.assertEqual(a['chim']['bucket'], 'converted_failing')
        self.assertEqual(a['errors'], [{'message': 'one warning'}])
        self.assertEqual(a['stats']['hull'], {'clipnodes': 800, 'max_depth': 4})
        self.assertEqual(a['stats']['vis'], {'entities_sent': 12})
        self.assertEqual(a['stats']['time']['convert_s'], 4.5)
        self.assertEqual(a['stats']['records']['refs_total'], 3)      # from the census, next to the measured numbers
        self.assertFalse(b['chim']['converted'])
        self.assertTrue(b['chim']['attempted'])
        self.assertEqual(b['errors'], [{'message': 'qbsp failed'}])
        self.assertEqual(out['result_ignored'], ['77,77'])
        isl = out['totals']['islands'][0]
        self.assertEqual(isl['converted'], 1)
        self.assertEqual(isl['with_errors'], 1)
        ring1 = [r for r in isl['rings'] if r['ring'] == 1][0]
        self.assertEqual(ring1['stats']['time.convert_s'], 4.5)
        self.assertEqual(out['totals']['all']['stats']['meshes.new'], 2)

    def test_later_results_replace_the_fields_they_carry(self):
        cp.record_result(self.out, self.result(**{'0,0': {'converted': True, 'stats': {'time': {'convert_s': 4.5}, 'meshes': {'new': 9}},
                                                          'errors': ['x']}}))
        cp.record_result(self.out, dict(self.result(**{'0,0': {'stats': {'time': {'convert_s': 2.0}}, 'errors': []}}),
                                        generated='2026-10-09T07:00:00+03:00'))
        c = ingest(self.out)['cells']['0,0']
        self.assertEqual(c['stats']['time']['convert_s'], 2.0)
        self.assertEqual(c['stats']['meshes']['new'], 9)        # measured by the job: wins over the derived figure
        self.assertEqual(c['errors'], [])
        self.assertTrue(c['chim']['converted'])

    def test_structured_errors_and_audit_numbers_survive(self):
        doc = self.result(**{'0,0': {'converted': True,
                                     'errors': [{'stage': 'qbsp', 'mechanism': 'hull_bevels', 'message': 'leak'}, 'plain text'],
                                     'audits': {'hull_bevels': {'status': 'failed', 'detail': 'leak', 'numbers': {'leaks': 2}}},
                                     'stats': {'records_by_type': {'STAT': {'placed': 5, 'converted': 4, 'deferred': {'light': 1}}},
                                               'collision': {'clipnodes': 9, 'max_hull_depth': 3}}}})
        cp.record_result(self.out, doc)
        c = ingest(self.out)['cells']['0,0']
        self.assertEqual(c['errors'], [{'stage': 'qbsp', 'mechanism': 'hull_bevels', 'message': 'leak'}, {'message': 'plain text'}])
        self.assertEqual(c['audits']['hull_bevels']['numbers'], {'leaks': 2})
        self.assertEqual(c['stats']['records_by_type']['STAT']['deferred'], {'light': 1})
        self.assertIn('qbsp/hull_bevels: leak | plain text', cp.export_csv(ingest(self.out)))

    def test_empty_sea_cells_have_their_own_status_and_are_not_counted_as_passed(self):
        cp.record_result(self.out, self.result(**{'9,9': {'status': 'empty'}, '0,1': {'empty': True},
                                                  '0,0': {'converted': True, 'audits': {'seam_tears': {'status': 'passed'}}}}))
        doc = ingest(self.out)
        h = doc['headline']
        self.assertEqual(doc['cells']['9,9']['chim']['bucket'], 'empty_sea')
        self.assertFalse(doc['cells']['9,9']['land'])
        self.assertEqual(h['empty_sea'], 2)
        self.assertEqual((h['passed'], h['land_cells'], h['converted']), (1, 25, 1))
        self.assertEqual(h['not_started'], 23)         # the empty land cell 0,1 is neither started nor passed
        nxt = json.loads((self.out / 'next.json').read_text())
        self.assertNotIn((0, 1), {(c['x'], c['y']) for c in nxt['spiral']['cells']})

    def test_hull_policy_pending_is_neither_passed_nor_failed(self):
        cp.record_result(self.out, self.result(**{'0,0': {'converted': True, 'policy_pending': True,
                                                          'audits': {'hull_bevels': {'status': 'failed', 'detail': 'chain depth'}}},
                                                  '1,0': {'converted': True, 'audits': {'seam_tears': {'status': 'passed'}}}}))
        doc = ingest(self.out)
        h = doc['headline']
        self.assertEqual(doc['cells']['0,0']['chim']['bucket'], 'hull_policy_pending')
        self.assertEqual((h['hull_policy_pending'], h['passed'], h['converted_failing'], h['converted']), (1, 1, 0, 2))
        self.assertFalse(doc['cells']['0,0']['chim']['successful'])

    def test_counts_match_the_conversion_jobs_own_summary(self):
        """CHIMport marks cells with a status: passed, failed, not_converted, hull_pending, empty (no policy_pending key)."""
        aud = {'seam_tears': {'status': 'passed'}}
        cells = {}
        for i, st in enumerate(['passed'] * 5 + ['hull_pending'] * 3 + ['failed'] * 2 + ['not_converted'] * 1 + ['empty'] * 2):
            k = '%d,%d' % (i % 5, i // 5)
            if st == 'empty':
                cells[k] = {'converted': True, 'empty': True, 'status': 'empty'}
            elif st == 'not_converted':
                cells[k] = {'converted': False, 'status': st, 'errors': [{'message': 'boom'}]}
            elif st == 'hull_pending':
                cells[k] = {'converted': True, 'status': st, 'audits': {'hull_bevels': {'status': 'not_measured', 'detail': 'hull policy pending'}}}
            else:
                cells[k] = {'converted': True, 'status': st, 'audits': aud}      # "failed" without any single failing audit
        cp.record_result(self.out, self.result(**cells))
        h = ingest(self.out)['headline']
        self.assertEqual((h['passed'], h['hull_policy_pending'], h['converted_failing'], h['not_converted'], h['empty_sea']),
                         (5, 3, 2, 1, 2))
        self.assertEqual(h['converted'], 10)         # passed + pending + failed-but-converted
        self.assertEqual(h['not_started'], 25 - 13)

    def test_bad_result_files_are_refused(self):
        for bad in ({'format': 'nope', 'build': 'b', 'cells': {}},
                    {'format': cp.RESULT_FORMAT, 'cells': {}},
                    self.result(**{'0,0': {'audits': {'made_up': {'status': 'passed'}}}}),
                    self.result(**{'0,0': {'audits': {'seam_tears': {'status': 'great'}}}}),
                    self.result(**{'x,y': {}})):
            with self.assertRaises(ValueError, msg=str(bad)):
                cp.record_result(self.out, bad)

    def test_export_csv_has_status_audits_and_every_numeric_stat(self):
        cp.record_result(self.out, self.result(**{'0,0': {'converted': True, 'stats': {'time': {'convert_s': 4.5}, 'custom': {'thing': 7}}}}))
        doc = ingest(self.out)
        text = cp.export_csv(doc)
        lines = text.splitlines()
        self.assertEqual(len(lines), 26)
        head = lines[0].split(',')
        for col in ('x', 'y', 'ring', 'chim_bucket', 'audit.seam_tears', 'stats.time.convert_s', 'stats.custom.thing', 'stats.records.refs_total'):
            self.assertIn(col, head)
        self.assertNotIn('\r', text)
        rows = [dict(zip(head, ln.split(','))) for ln in lines[1:]]
        mine = [r for r in rows if r['x'] == '0' and r['y'] == '0'][0]
        self.assertEqual(mine['chim_bucket'], 'converted_unmeasured')
        self.assertEqual(mine['stats.time.convert_s'], '4.5')
        self.assertEqual(mine['stats.custom.thing'], '7')


class InteriorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.cfg = self.out / 'config'
        write(self.cfg / 'scenes.json', {'scenes': [{'cell': 'Synthetic Hall', 'map': 'syhall', 'interior': True}]})

    def doc(self, **kw):
        bugs = [{'id': 'SYN-9', 'title': 'Light in Synthetic Cellar is dim', 'where': '', 'state': 'open', 'tags': []},
                {'id': 'SYN-8', 'title': 'syhall door sticks', 'where': '', 'state': 'open', 'tags': []}]
        pois = [{'name': 'Synthetic Hall', 'kind': 'interior', 'x': 2.5, 'y': 2.5, 'converted': True}]
        return ingest(self.out, bugs=bugs, cells_detail={'cells': {}, 'pois': pois}, config_dir=self.cfg, **kw)

    def test_door_destinations_make_a_tree_under_the_exterior_cell(self):
        doc = self.doc()
        trees = doc['cells']['2,2']['entrances']
        self.assertEqual(len(trees), 1)
        hall = trees[0]
        self.assertEqual((hall['id'], hall['ref'], hall['object'], hall['pos']), ('i0001', 77, 'door_a', [100, 200, 300]))
        self.assertEqual([c['id'] for c in hall['children']], ['i0002'])
        cellar = hall['children'][0]
        self.assertEqual(cellar['ref'], 11)
        self.assertEqual([c['id'] for c in cellar['children']], ['i0003'], 'the door back to the hall is not followed twice')
        self.assertEqual(cellar['children'][0]['children'], [])
        self.assertEqual([t['id'] for t in doc['cells']['0,0']['entrances']], ['i0003'])
        self.assertEqual(doc['cells']['4,4']['entrances'], [])

    def test_interior_records_carry_ids_map_status_stats_and_bugs(self):
        recs = {r['id']: r for r in self.doc()['interiors']}
        hall = recs['i0001']
        self.assertEqual((hall['name'], hall['our_map'], hall['set']), ('Synthetic Hall', 'syhall', 'vvardenfell'))
        self.assertEqual(hall['legacy'], {'converted': True, 'known': True})
        self.assertEqual(hall['chim']['status'], 'not_started')
        self.assertEqual(hall['contents']['refs_total'], 8)     # 5 statics + 3 lights; load doors are not counted
        self.assertEqual(hall['contents']['lights'], 3)
        self.assertEqual(hall['stats']['records']['by_type']['STAT'], 5)
        self.assertEqual(hall['stats']['meshes'], {'unique': 4})
        self.assertEqual(hall['stats']['legacy_estimate']['faces'], 50)
        self.assertEqual(hall['depth'], 1)
        self.assertEqual(hall['entrances'][0]['cell'], '2,2')
        self.assertEqual(hall['entrances'][0]['door_ref'], 77)
        self.assertEqual(hall['bugs'], ['SYN-8'])            # linked by its map name
        self.assertEqual(recs['i0002']['depth'], 2)
        self.assertEqual(recs['i0002']['entrances'][0]['via'], ['i0001'])
        self.assertEqual(recs['i0002']['bugs'], ['SYN-9'])    # linked by its name
        self.assertEqual(recs['i0002']['legacy'], {'converted': None, 'known': False})
        # Vault is reached directly from cell 0,0 (depth 1) and also through the cellar (depth 3): the shallowest wins
        self.assertEqual(recs['i0003']['depth'], 1)
        self.assertEqual({e['cell'] for e in recs['i0003']['entrances']}, {'0,0', '2,2'})

    def test_without_a_census_there_are_no_interior_links_and_nothing_is_invented(self):
        doc = cp.ingest(self.out, progress=progress_doc(), metrics=metrics_layer(), now=NOW)
        self.assertEqual(doc['interiors'], [])
        self.assertEqual(doc['cells']['2,2']['entrances'], [])

    def test_loops_and_depth_are_bounded(self):
        census = census_doc()
        names = ['n%d' % i for i in range(12)]
        census['interiors'] = {n: {'name': n, 'set': 'vvardenfell', 'counts': {}, 'placements': 0, 'unique_meshes': 0,
                                   'doors': [{'ref': i, 'object': 'd', 'pos': None, 'to': names[(i + 1) % 12]}]}
                               for i, n in enumerate(names)}
        census['cells']['2,2']['doors'] = [{'ref': 1, 'object': 'd', 'pos': None, 'to': 'n0'}]
        doc = ingest(self.out, census=census)
        depth, node = 0, doc['cells']['2,2']['entrances'][0]
        while node['children']:
            node = node['children'][0]
            depth += 1
        self.assertEqual(depth, cp.MAX_DEPTH - 1)


class ServeTests(unittest.TestCase):
    def test_progress_is_served_from_its_folder_and_read_again_on_every_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / 'cell-progress.json').write_text('{"generated": "one"}')
            (t / 'next.json').write_text('{"n": 1}')
            (t / 'secret.json').write_text('no')
            ts.Handler.data_dir, ts.Handler.maps_dir, ts.Handler.metrics = None, None, None
            ts.Handler.progress_dir = ts.progress_folder(t / 'cell-progress.json')     # a file path means its folder
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
                self.assertEqual(get('/data/cell-progress.json'), (200, b'{"generated": "one"}'))
                (t / 'cell-progress.json').write_text('{"generated": "two"}')          # a new ingest: no restart needed
                self.assertEqual(get('/data/cell-progress.json'), (200, b'{"generated": "two"}'))
                self.assertEqual(get('/data/cell-progress-next.json'), (200, b'{"n": 1}'))
                self.assertEqual(get('/data/cell-progress-curve.png')[0], 404)        # not written yet
                self.assertEqual(get('/data/secret.json')[0], 404)
                self.assertEqual(get('/amiwind-toolkit/chim-head.js')[0], 200)
                ts.Handler.progress_dir = None
                self.assertEqual(get('/data/cell-progress.json')[0], 404)             # no --progress: nothing served
            finally:
                ts.Handler.progress_dir = None
                server.shutdown()
                server.server_close()


class CompleteAndPageTests(unittest.TestCase):
    """Cell complete / terrain complete, the per-type table, the generated public page and its policy."""
    KIT = ROOT / 'amiwind-toolkit'
    AUD = {'seam_tears': {'status': 'passed'}}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    LIT = {'mode': 'baked', 'terrain_faces': 10, 'terrain_lit': 10, 'model_faces': 4, 'model_lit': 4}

    def stats(self, lighting=LIT, **types):
        return {'records_by_type': types, 'records': {'flora': 0}, 'lighting': lighting}

    def doc(self):
        ok = {'placed': 4, 'converted': 4, 'deferred': {}, 'failed': 0, 'skipped': {}}
        cells = {
            '0,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, CONT=ok)},                   # complete
            '1,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, NPC_={
                'placed': 2, 'converted': 0, 'deferred': {'resident conversion': 2}, 'failed': 0, 'skipped': {}})},   # terrain complete
            '2,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=dict(ok, converted=3, deferred={
                'other reason': 1}))},                                                                                # passed
            '3,0': {'converted': True, 'audits': self.AUD},                                                           # passed (no figures)
            '4,0': {'converted': True, 'status': 'hull_pending', 'stats': self.stats(STAT=ok),
                    'audits': {'hull_bevels': {'status': 'not_measured'}}},
            '0,1': {'converted': True, 'audits': {'seam_tears': {'status': 'failed', 'detail': 'tears'}}, 'stats': self.stats(STAT=ok)},
            '1,1': {'converted': False, 'status': 'not_converted', 'errors': ['boom']},
            '2,1': {'converted': True, 'empty': True, 'status': 'empty'},
            '3,1': {'converted': True, 'audits': self.AUD, 'stats': self.stats(
                STAT=dict(ok, skipped={'not in the frame': 1}))},                                                      # skipped: passed only
        }
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'syn-001', 'generated': NOW, 'cells': cells})
        return ingest(self.out)

    def test_status_precedence(self):
        d = self.doc()
        got = {k: d['cells'][k]['chim']['bucket'] for k in d['cells'] if k in ('0,0', '1,0', '2,0', '3,0', '4,0', '0,1', '1,1', '2,1', '3,1')}
        self.assertEqual(got, {'0,0': 'complete', '1,0': 'terrain_complete', '2,0': 'audits_passed', '3,0': 'audits_passed',
                               '4,0': 'hull_policy_pending', '0,1': 'converted_failing', '1,1': 'not_converted',
                               '2,1': 'empty_sea', '3,1': 'audits_passed'})
        self.assertLess(cp.BUCKETS.index('complete'), cp.BUCKETS.index('terrain_complete'))
        self.assertLess(cp.BUCKETS.index('terrain_complete'), cp.BUCKETS.index('audits_passed'))
        h = d['headline']
        self.assertEqual((h['complete'], h['terrain_complete'], h['audits_passed'], h['empty_sea']), (1, 1, 3, 1))
        self.assertEqual(h['done'], h['passed'] + h['empty_sea'])
        self.assertEqual(h['passed'], 5)
        self.assertTrue(d['cells']['0,0']['chim']['successful'])
        self.assertEqual(d['totals']['all']['complete'], 1)

    def test_by_type_ingest_and_markers(self):
        cats = cp.categorize({'DOOR': {'placed': 5, 'converted': 2, 'failed': 0,
                                       'deferred': {'nonvisual source marker': 3}, 'skipped': {}},
                              'CREA': {'placed': 1, 'converted': 0, 'failed': 0, 'deferred': {'creature simulation pending': 1},
                                       'skipped': {}}, 'MISC': {'placed': 2, 'converted': 2, 'failed': 0, 'deferred': {}, 'skipped': {}}})
        self.assertEqual((cats['doors']['placed'], cats['doors']['converted'], cats['markers']['placed']), (2, 2, 3))
        self.assertEqual(cats['creatures']['deferred'], {'creature simulation pending': 1})
        self.assertEqual(cats['items']['placed'], 2)
        d = self.doc()
        self.assertEqual(d['cells']['1,0']['categories']['npcs']['deferred'], {'resident conversion': 2})
        isl = d['totals']['islands'][0]['by_category']
        self.assertEqual(isl['npcs']['placed'], 2)
        self.assertIsNone(d['cells']['3,0']['categories'])

    def test_markers_never_block_completion_and_islands_are_reported_apart(self):
        ok = {'placed': 3, 'converted': 3, 'deferred': {}, 'failed': 0, 'skipped': {}}
        mk = {'placed': 2, 'converted': 0, 'deferred': {'nonvisual source marker': 2}, 'failed': 0, 'skipped': {}}
        self.assertFalse(cp.MARKERS_BLOCK_COMPLETE)
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'b', 'generated': NOW, 'cells': {
            '0,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, DOOR=mk)}}})
        d = ingest(self.out)
        self.assertEqual(d['cells']['0,0']['chim']['bucket'], 'complete')
        self.assertEqual(d['cells']['0,0']['categories']['markers']['placed'], 2)
        isl = d['headline']['islands']
        self.assertEqual(len(isl), 1)
        self.assertEqual((isl[0]['name'], isl[0]['cells'], isl[0]['done'], isl[0]['complete']), ('Vvardenfell', 25, 1, 1))
        md, doc, text = self.render()
        self.assertIn('not drawn, not required', text)

    def test_light_emitters_without_a_mesh_keep_blocking_and_not_converted_is_never_done(self):
        ok = {'placed': 3, 'converted': 3, 'deferred': {}, 'failed': 0, 'skipped': {}}
        lamp = {'placed': 5, 'converted': 3, 'deferred': {'nonvisual source marker': 2}, 'failed': 0, 'skipped': {}}
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'b', 'generated': NOW, 'cells': {
            '0,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, LIGH=lamp)},
            '1,0': {'converted': False, 'status': 'not_converted', 'errors': ['window mount across a cell edge']}}})
        d = ingest(self.out)
        self.assertEqual(d['cells']['0,0']['chim']['bucket'], 'audits_passed')       # blocked by the lights
        self.assertEqual(d['cells']['0,0']['categories']['lights']['deferred'], {'nonvisual source marker': 2})
        self.assertEqual(d['cells']['0,0']['categories']['markers']['placed'], 0)
        self.assertEqual(d['cells']['1,0']['chim']['bucket'], 'not_converted')
        h = d['headline']
        self.assertEqual((h['not_converted'], h['done']), (1, 1))                     # done = passed 1, not the failure state
        import cell_progress_md as md
        for r in d['cells'].values():
            r['island'] = 1
        self.assertIn('| Not converted | 1 |', md.render(d, 'now'))

    def test_lighting_is_required_for_both_completion_levels(self):
        ok = {'placed': 3, 'converted': 3, 'deferred': {}, 'failed': 0, 'skipped': {}}
        npc = {'placed': 1, 'converted': 0, 'deferred': {'resident conversion': 1}, 'failed': 0, 'skipped': {}}
        meshless = {'placed': 2, 'converted': 0, 'deferred': {
            'light without a mesh: no CHIM light path yet (CHIM-MESHLESS-LIGHTS-33)': 2}, 'failed': 0, 'skipped': {}}
        cen = census_doc()
        cen['cells']['0,0']['lights'] = {'placed': 2, 'by_class': {'pure_light': {'mesh': 0, 'meshless': 2}},
                                         'styles': {'0': 2}, 'animated': 0}
        cen['cells']['1,0']['lights'] = cen['cells']['0,0']['lights']
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'b', 'generated': NOW, 'cells': {
            '0,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, LIGH=meshless)},        # baked: complete
            '1,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(None, STAT=ok, LIGH=meshless)},  # today: unlit
            '2,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(STAT=ok, NPC_=npc)},             # terrain complete
            '3,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(dict(self.LIT, model_lit=2), STAT=ok, NPC_=npc)},
            '4,0': {'converted': True, 'audits': self.AUD, 'stats': self.stats(dict(self.LIT, mode='lamps'), STAT=ok)}}})
        d = ingest(self.out, census=cen)
        c = d['cells']
        self.assertEqual(c['0,0']['lighting']['status'], 'lit')
        self.assertEqual(c['0,0']['chim']['bucket'], 'complete')          # the light-path deferral is judged by the audit
        self.assertEqual(c['1,0']['lighting']['status'], 'unlit')
        self.assertTrue(c['1,0']['lighting']['assumed'])
        self.assertEqual(c['1,0']['lighting']['reach'], {'baked': 0, 'lamp_table': 0, 'none': 2})
        self.assertEqual(c['1,0']['chim']['bucket'], 'complete_unlit')    # everything but the lighting: awaiting lighting
        self.assertTrue(c['1,0']['chim']['blockers'][0].startswith('lighting unlit'))
        self.assertEqual(c['2,0']['chim']['bucket'], 'terrain_complete')
        self.assertEqual(c['3,0']['lighting']['status'], 'partial')      # half the model faces lit
        self.assertEqual(c['3,0']['chim']['bucket'], 'terrain_complete_unlit')
        self.assertEqual(c['4,0']['lighting']['status'], 'lit')          # no light sources, every surface lit
        lt = d['headline']['lighting']
        self.assertEqual((lt['status']['lit'], lt['status']['partial'], lt['status']['unlit']), (3, 1, 1))
        self.assertEqual(lt['lights']['pure_light'], {'mesh': 0, 'meshless': 4})
        self.assertEqual(d['headline']['islands'][0]['lighting']['status']['lit'], 3)
        self.assertIn('lighting', cp.export_csv(d).splitlines()[0].split(','))
        import cell_progress_md as md
        for r in c.values():
            r['island'] = 1
        text = md.render(d, 'now')
        self.assertIn('Lighting: lit 3, partial 1, unlit 1', text)
        self.assertIn('### Lighting', md.policy_section(text))
        for label in (cp.COMPLETE_UNLIT_LABEL, cp.TERRAIN_COMPLETE_UNLIT_LABEL):
            self.assertIn('- %s: 1' % label, text)
            self.assertIn('| %s | 1 |' % label, text)
            self.assertIn(label.lower(), md.policy_section(text))
        self.assertEqual(d['headline']['done'], 5)                        # both awaiting-lighting cells count as done
        self.assertEqual((d['headline']['complete_unlit'], d['headline']['terrain_complete_unlit']), (1, 1))
        self.assertEqual((d['headline']['eligible'], d['headline']['eligible_release']), (5, cp.ELIGIBLE_RELEASE))
        self.assertIn('**Eligible for %s: 5 of 25**' % cp.ELIGIBLE_RELEASE, text)
        self.assertIn('Eligible for %s = every done cell' % cp.ELIGIBLE_RELEASE, md.policy_section(text))
        self.assertIn('empty_sea', cp.ELIGIBLE)
        self.assertEqual(d['headline']['eligible'], d['headline']['done'])
        self.assertIn("if (f === 'eligible')", (self.KIT / 'world-map.html').read_text(encoding='utf-8'))

    def test_awaiting_lighting_precedence(self):
        order = ('complete', 'terrain_complete', 'complete_unlit', 'terrain_complete_unlit', 'audits_passed')
        self.assertEqual([b for b in cp.BUCKETS if b in order], list(order))
        self.assertTrue(all(b in cp.SUCCESS for b in order))
        rec = {'chim': {'converted': True}, 'lighting': {'status': 'unlit', 'reason': 'x'},
               'categories': cp.categorize({'STAT': {'placed': 1, 'converted': 1, 'deferred': {}, 'failed': 0, 'skipped': {}}})}
        self.assertEqual(cp.completion_level(rec), 'complete_unlit')
        rec['lighting']['status'] = 'lit'
        self.assertEqual(cp.completion_level(rec), 'complete')
        rec['categories']['statics']['deferred'] = {'other': 1}
        self.assertIsNone(cp.completion_level(rec))                     # something else missing: not awaiting lighting

    def test_zebra_only_for_the_awaiting_lighting_statuses(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        rows = re.findall(r"^  (\w+): \['(#[0-9a-f]{6})', '([^']*)'(, CHIM_ZEBRA)?\]", page, re.M)
        zebra = {k for k, _, _, z in rows if z}
        self.assertEqual(zebra, {'complete_unlit', 'terrain_complete_unlit'})
        self.assertIn('awaiting lighting', ' '.join(t for _, _, t, _ in rows))
        self.assertIn("c.chim.bucket === 'complete_unlit'", page)      # white border like Cell complete
        self.assertIn('<script src="zebra.js"></script>', page)
        head = (self.KIT / 'chim-head.js').read_text(encoding='utf-8')
        self.assertIn("['complete_unlit', 'cell complete, awaiting lighting'", head)
        # the shared tile is the inspector's markup-zone tile
        tile = (self.KIT / 'zebra.js').read_text(encoding='utf-8')
        insp = (self.KIT / 'map-inspector.html').read_text(encoding='utf-8')
        for part in ('tile.width=12;tile.height=12', 't.lineWidth=4', 't.moveTo(-3,12);t.lineTo(12,-3);t.moveTo(3,15);t.lineTo(15,3)', "'#444b53'"):
            self.assertIn(part, insp)
            self.assertIn(part, tile.replace(' ', ''))

    def test_kept_as_chain_passes(self):
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'b', 'generated': NOW, 'cells': {
            '0,0': {'converted': True, 'audits': {'hull_bevels': {'status': 'failed', 'outcome': cp.KEPT_CHAIN_OUTCOME}}}}})
        c = ingest(self.out)['cells']['0,0']
        self.assertEqual(c['audits']['hull_bevels']['status'], 'passed')
        self.assertEqual(c['audits']['hull_bevels']['outcome'], cp.KEPT_CHAIN_OUTCOME)
        self.assertEqual(c['chim']['bucket'], 'audits_passed')

    def render(self):
        import cell_progress_md as md
        d = self.doc()
        for r in d['cells'].values():       # the page counts island 1
            r['island'] = 1
        return md, d, md.render(d, '2026-10-09 06:00 +0300')

    def test_page_renders_from_a_fixture_and_is_deterministic(self):
        md, d, text = self.render()
        self.assertEqual(text, md.render(d, '2026-10-09 06:00 +0300'))
        self.assertTrue(text.startswith(md.HEADER))
        self.assertRegex(text, r'\*\*Done: \d+ of 25 \(')
        for needle in ('Cell complete: 1', 'Terrain complete: 1', 'Empty sea: 1', 'Hull policy pending', 'Per object type',
                       'Failures by mechanism class', 'Seam tears', 'Generated 2026-10-09 06:00 +0300', 'Tracker data generated'):
            self.assertIn(needle, text)
        self.assertEqual(text, '\n'.join(x.rstrip() for x in text.split('\n')))
        self.assertNotIn('\r', text)

    def test_policy_section_matches_the_constants(self):
        md, d, text = self.render()
        pol = md.policy_section(text)
        self.assertEqual(pol, '\n'.join(x.rstrip() for x in md.policy_lines()) + '\n')
        self.assertIn('depth of %d or more' % cp.HULL_CHAIN_DEPTH_LIMIT, pol)
        for label in cp.MECHANISMS.values():
            self.assertIn(label, pol)
        for label in (cp.COMPLETE_LABEL, cp.TERRAIN_COMPLETE_LABEL):
            self.assertIn(label, pol)
        for word in ('NPCs', 'Creatures', 'markers', 'Empty sea', 'count as done'):
            self.assertIn(word, pol)
        self.assertEqual(md.check(text), [])
        self.assertTrue(md.check(text.replace('Import policy', 'Import policies')))

    def test_page_has_no_private_content(self):
        md, d, text = self.render()
        self.assertEqual(md.private_hits(text), [])
        self.assertIsNone(re.search(r'\b[A-Za-z]:[\\/]|/vol\b', text))
        self.assertTrue(md.private_hits('see C' + ':' + chr(92) + 'x' + chr(92) + 'y'))
        self.assertTrue(md.private_hits('mounted at /vol/ws'))

    def test_committed_page_is_current_in_form(self):
        import cell_progress_md as md
        page = ROOT / 'docs' / 'chim' / 'CELL_TRACKER.md'
        if page.is_file():
            self.assertEqual(md.check(page.read_bytes().decode('utf-8')), [])

    def test_legend_and_outline_in_the_toolkit(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        head = (self.KIT / 'chim-head.js').read_text(encoding='utf-8')
        for needle in ("complete: ['#7dffa6', 'Cell complete", "terrain_complete: ['#7dffa6', 'Terrain complete"):
            self.assertIn(needle, page)
        self.assertIn("['complete', 'cell complete'", head)
        self.assertIn("['terrain_complete', 'terrain complete'", head)
        # the white outline is drawn around complete cells only; the legacy full-town border is dashed amber
        self.assertIn("function chimIsComplete(c) { return c.chim.bucket === 'complete' || c.chim.bucket === 'complete_unlit'; }", page)
        self.assertIn('groupOutline(g, chimCellList.filter(c => chimIsComplete(c) && chimVisible(c)));', page)
        self.assertIn("data.cells.filter(c => c.map === 'full'), 'dashed')", page)
        self.assertIn("legacy full town/area map (dashed amber border", page)
        self.assertNotIn('full town/area map (white border', page)


class ReleaseUiTests(unittest.TestCase):
    """The owner's release field, the legend filter, the reference file, and tracking your own build."""
    KIT = ROOT / 'amiwind-toolkit'

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / 'out'
        self.addCleanup(self._tmp.cleanup)

    def doc(self):
        ok = {'placed': 2, 'converted': 2, 'deferred': {}, 'failed': 0, 'skipped': {}}
        aud = {'seam_tears': {'status': 'passed'}}
        cells = {'0,0': {'converted': True, 'audits': aud, 'stats': {'records_by_type': {'STAT': ok}}},
                 '1,0': {'converted': True, 'audits': aud, 'stats': {'records_by_type': {'STAT': ok}}},
                 '2,0': {'converted': True, 'audits': {'seam_tears': {'status': 'failed'}}},
                 '3,0': {'converted': True, 'empty': True, 'status': 'empty'}}
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'syn-1', 'generated': NOW, 'cells': cells})
        return ingest(self.out)

    def release(self, *argv):
        return cp.main(['release', '--out', str(self.out), '--now', '2026-10-09T15:00:00+03:00'] + list(argv))

    def test_release_is_owner_set_dated_and_survives_ingest(self):
        d = self.doc()
        self.assertFalse((self.out / 'releases.json').exists())                 # results and ingest never create it
        self.assertTrue(all(c['release'] is None for c in d['cells'].values()))
        self.assertEqual(self.release('--version', 'v0.0.34', '--cells', '0,0 3,0'), 0)
        rel = json.loads((self.out / 'releases.json').read_text())
        self.assertEqual(rel['cells']['0,0'], {'release': 'v0.0.34', 'date': '2026-10-09', 'who': 'owner', 'shipped': False})
        hist = [json.loads(x) for x in (self.out / 'history.jsonl').read_text().splitlines()]
        last = [h for h in hist if h.get('type') == 'release'][-1]
        self.assertEqual((last['who'], last['date'], last['release']), ('owner', '2026-10-09T15:00:00+03:00', 'v0.0.34'))
        # new conversion results and a fresh ingest keep it; the release line does not confuse the count history
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'syn-2', 'generated': NOW, 'cells': {
            '0,0': {'converted': True, 'audits': {'seam_tears': {'status': 'failed'}}}}})
        d = ingest(self.out)
        self.assertEqual(d['cells']['0,0']['release']['name'], 'v0.0.34')
        self.assertEqual(d['cells']['0,0']['release']['who'], 'owner')
        self.assertEqual(json.loads((self.out / 'releases.json').read_text())['cells']['0,0']['release'], 'v0.0.34')
        self.assertTrue(d['history'])
        row = [r for r in d['releases'] if r['release'] == 'v0.0.34'][0]
        self.assertEqual((row['approved'], row['empty_sea'], row['failing']), (2, 1, 1))

    def test_bulk_selectors(self):
        d = self.doc()

        def keys(*spec):
            return cp.RL.resolve(d['cells'], list(spec), cp.ELIGIBLE_SELECT)
        self.assertEqual(keys('0,0', '1,0'), ['0,0', '1,0'])
        self.assertEqual(keys('eligible'), ['0,0', '1,0', '3,0'])                # passed cells and empty sea, not the failing one
        self.assertEqual(keys('status:converted_failing'), ['2,0'])
        self.assertEqual(keys('unassigned'), keys('all'))
        self.assertEqual(self.release('--version', 'v0.0.34', '--cells', 'eligible'), 0)
        self.assertEqual(self.release('--version', 'v0.0.34', '--cells', '3,0', '--clear'), 0)
        d = ingest(self.out)
        self.assertEqual(sorted(k for k, c in d['cells'].items() if c['release']), ['0,0', '1,0'])
        self.assertEqual(cp.RL.resolve(d['cells'], ['release:v0.0.34'], cp.ELIGIBLE_SELECT), ['0,0', '1,0'])
        with self.assertRaises(ValueError):
            keys('nonsense')
        self.assertEqual(self.release('--version', 'v0.0.34', '--cells', 'nonsense'), 2)
        self.assertEqual(self.release('--version', 'v0.0.33', '--cells', 'shipped-towns', '--shipped'), 2)   # no town cells in the fixture

    def test_shipped_towns_seed_is_the_frame_coverage(self):
        """v0.0.33 = every cell the shipped towns' CHIM frames cover, not only the cells that own placements."""
        run = self.out.parent / 'run'
        frame = {'cell': [2, 2], 'centre': [2 * 8192 + 4096.0, 2 * 8192 + 4096.0], 'grain': 256, 'low': [-3072.0, -3072.0],
                 'nx': 24, 'ny': 24}
        path = ch.frame_path(frame['cell'])
        write(run / 'chim-receipt.json', {'areas': ['balmora'], 'builder': 'chim', 'chim_version': '9.9.9', 'placements': 5,
                                          'models': 2, 'frames': [{'frame': frame, 'placements': 5}]})
        # a 24 x 24 chunk grid of 256 Quake units (4 per Morrowind unit) is 3 x 3 cells; only the middle cell owns placements
        per = [{'frame': path, 'cell': [i, j], 'owned': 1 if 8 <= i < 16 and 8 <= j < 16 else 0, 'terrain_faces': 10,
                'placed_faces': 20, 'bytes': 100} for i in range(24) for j in range(24)]
        write(run / 'chim-stats.json', {'chim_version': '9.9.9', 'world_format': '0.5', 'chunks': {'per_chunk': per}})
        d = ingest(self.out, ['syn=%s' % run])
        # the geometry, worked out here independently: x and y reach centre +- 12288 Morrowind units = cells 1, 2 and 3
        expected = sorted('%d,%d' % (x, y) for x in (1, 2, 3) for y in (1, 2, 3))
        self.assertEqual(d['area_cover']['balmora'], expected)
        self.assertEqual(d['area_cells']['balmora'], ['2,2'])                   # converted: owns placements
        self.assertEqual(self.release('--version', 'v0.0.33', '--cells', 'shipped-towns', '--shipped'), 0)
        d = ingest(self.out)
        shipped = sorted(k for k, c in d['cells'].items() if c['release'] and c['release']['shipped'])
        self.assertEqual(shipped, expected)                                    # the seed equals the frame coverage
        self.assertTrue(all(d['cells'][k]['release']['name'] == 'v0.0.33' for k in shipped))
        self.assertTrue([r for r in d['releases'] if r['release'] == 'v0.0.33'][0]['shipped'])

    def test_page_has_a_per_release_table(self):
        import cell_progress_md as md
        d = self.doc()
        for r in d['cells'].values():
            r['island'] = 1
        self.assertIn('No cells are assigned to a release yet.', md.render(d, 'now'))
        self.release('--version', 'v0.0.34', '--cells', 'eligible')
        d = ingest(self.out)
        for r in d['cells'].values():
            r['island'] = 1
        text = md.render(d, 'now')
        self.assertIn('## Releases', text)
        self.assertRegex(text, r'\| v0\.0\.34 \| open \| 3 \|')
        self.assertEqual(md.private_hits(text), [])

    def test_legend_filter_presets_and_releases_in_node(self):
        import shutil
        import subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable; the legend checks need an existing interpreter')
        r = subprocess.run([node, str(ROOT / 'tests' / 'test_cell_progress_legend.js'), str(self.KIT / 'chim-legend.js')],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('legend ok', r.stdout)

    def test_toolkit_header_is_unchanged_from_the_lighting_branch(self):
        # Owner rule (2026-10-09): the Toolkit's logo header (logo, "Toolkit", "Last updated with AmiWind ...", the World / Local /
        # 3D Inspector buttons, the browser note, then the headline line and chips) keeps its layout, logo, fonts and colours.
        # New controls go below it or into the legend panel. These fingerprints are those of the lighting branch
        # (v0.0.34-chim-light); change them only on purpose, together with the header.
        import hashlib
        index = (self.KIT / 'index.html').read_text(encoding='utf-8')
        header = re.search(r'<header\b.*?</header>', index, re.S).group(0)
        css = ''.join(re.findall(r'[^{}]*header[^{}]*\{[^}]*\}', index))
        sha = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest()
        self.assertEqual(sha(header), 'fac1cc24a87b581836ae2b6691de7f11bdc2f7856172a3cd6a573f07c311e294')
        self.assertEqual(sha(css), '209fa0e28e1aece0bf890cba4c38319d17648755f5f0386ba1b6d83c2d1c9a60')
        head = (self.KIT / 'chim-head.js').read_bytes()
        self.assertEqual(hashlib.sha256(head).hexdigest(), 'a60e9593cad3c01f99d4e2fc221907bbfbe43136a5308f5faaf92f2d8a46779c')

    def test_one_header_for_every_toolkit_page(self):
        # The shared header (header.js) is the logo block of index.html: same logo file, same version line. Pages opened on their
        # own mount it with their name as the subtitle; embedded pages show nothing (the index header is above them).
        header = (self.KIT / 'header.js').read_text(encoding='utf-8')
        index = (self.KIT / 'index.html').read_text(encoding='utf-8')
        logo = re.search(r'<img src="([^"]+)" alt="AmiWind">', index).group(1)
        version = re.search(r'<small id="toolkit-version"[^>]*>([^<]+)</small>', index).group(1)
        self.assertIn("const LOGO = '%s';" % logo, header)
        self.assertIn("const VERSION_TEXT = '%s';" % version, header)
        self.assertIn('Everything here runs in your browser.', header)
        world = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        self.assertIn('<script src="header.js"></script>', world)
        self.assertIn("AmiWindToolkitHeader.mount('World Map')", world)
        inspector = (self.KIT / 'map-inspector.html').read_text(encoding='utf-8')
        self.assertIn('<script src="header.js" data-subtitle="3D Map Inspector" data-hide="header h1"></script>', inspector)
        # the page's own script is still the first plain <script> (tests/test_polycount_markup.js evaluates it)
        self.assertNotRegex(inspector.split('<script>')[0], r'<script>')
        self.assertIn('root.parent !== root', header)                  # embedded pages stay as they are
        exporter = (ROOT / 'tools' / 'export_mesh_inspection.py').read_text(encoding='utf-8')
        self.assertIn('header.js', exporter)                           # the standalone export inlines it

    def test_status_strip_above_the_map(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        for needle in ('id="strip"', 'id="stdot"', 'id="stlabel"', 'Source: <span id="stsrc">', 'Last updated: <span id="stupd">', 'id="stago"',
                       'Auto-update: <label>', 'id="stauto"', 'function stripRender()', 'setInterval(stripRender, 1000)', 'stripError = true',
                       "stripError = !(await loadChim(true))", "'live build folder (file, no server)'", 'st.updated_epoch'):
            self.assertIn(needle, page, needle)
        self.assertEqual(page.count('id="chimlive"'), 1)             # one switch, in the strip
        self.assertLess(page.index('id="strip"'), page.index('<div id="controls">'))       # visible even with the controls folded
        import live_tracker as lt
        self.assertIn("updated_epoch=round(time.time(), 1)", (ROOT / 'tools' / 'live_tracker.py').read_text(encoding='utf-8'))
        self.assertTrue(lt.INTERVAL == 10)

    def test_map_fits_the_window_and_folds_its_controls(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        for needle in ('id="zoomfit"', 'id="zoomreset"', 'const MIN_ZOOM = 0.2', 'function fitCanvas(g)', 'window.innerHeight - docTop',
                       'function viewFit()', "'amiwind-map-view-1'", 'function viewRestore()', 'LABEL_MIN_PX = 16', 'cellPx(g) < LABEL_MIN_PX',
                       'id="ctltoggle"', 'id="controls"', "'amiwind-map-controls-1'", 'window.innerHeight >= 900'):
            self.assertIn(needle, page, needle)
        self.assertNotIn('view.z = Math.max(1, Math.min(16', page)        # the zoom floor is MIN_ZOOM, not 1
        # the header and its rows stay in the page: the controls are only wrapped
        self.assertEqual(page.count('<div id="controls">'), 1)

    def test_mesh_chart_does_not_draw_before_its_data_arrives(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        self.assertIn("const ser = chim && chimMeshSeries(); if (!ser || !ser.spiral.length) return;", page)
        self.assertIn('async function loadChimCurve()', page)
        self.assertIn("$('chimpanel').innerHTML = chimOverview();", page)            # redrawn when the curve lands
        # no canvas is written while there is no series
        self.assertIn("(ser ? '<div class=\"meshpanel\">", page)

    def test_map_page_wires_the_legend_controls(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        for needle in ('<script src="chim-legend.js">', 'id="chimpreset"', 'id="legall"', 'id="legnone"', 'id="chimrelease"',
                       'id="relsummary"', 'data-k="', 'Release: ', 'id="chimreffile"', "'compare'", 'legendSave', 'localStorage'):
            self.assertIn(needle, page, needle)
        self.assertIn('amiwind-toolkit/chim-legend.js', json.loads((ROOT / 'tools' / 'release-files.json').read_text()))

    def test_reference_file_has_only_the_allowed_content(self):
        import cell_progress_ref as ref
        d = self.doc()
        for r in d['cells'].values():
            r['island'] = 1
        d['headline']['islands'] = [{'name': 'Vvardenfell', 'cells': 4, 'done': 3}]
        built = ref.build(d)
        self.assertEqual(built['format'], ref.REFERENCE_FORMAT)
        self.assertEqual(set(built['cells']['0,0']) - set(ref.CELL_KEYS), set())
        self.assertEqual(ref.check(ref.dumps(built)), [])
        self.assertNotIn('detail', ref.dumps(built))
        bad = json.loads(ref.dumps(built))
        bad['cells']['0,0']['path'] = 'x'
        self.assertTrue(ref.check(json.dumps(bad)))
        for leak in ('C:' + chr(92) + 'x', '/vol/build', 'amiwind-example-001', 'someone@example.org'):
            bad = json.loads(ref.dumps(built))
            bad['cells']['0,0']['name'] = leak
            self.assertTrue(ref.check(json.dumps(bad, indent=1)), leak)
        self.assertEqual(ref.compare(d['cells'], built)['0,0'], 'same')
        built['cells']['0,0']['status'] = 'not_started'
        self.assertEqual(ref.compare(d['cells'], built)['0,0'], 'better')
        self.assertEqual(cp.main(['publish', '--out', str(self.out), '--file', str(self.out / 'ref.json')]), 0)
        self.assertEqual(cp.main(['check-reference', '--file', str(self.out / 'ref.json')]), 0)

    def test_committed_reference_file_is_clean(self):
        import cell_progress_ref as ref
        page = ROOT / ref.REFERENCE_PATH
        if page.is_file():
            self.assertEqual(ref.check(page.read_bytes().decode('utf-8')), [])
            self.assertIn(ref.REFERENCE_PATH, json.loads((ROOT / 'tools' / 'release-files.json').read_text()))

    def test_a_build_writes_its_own_progress_and_the_server_finds_it(self):
        import cell_progress_build as cb
        import toolkit_serve as srv
        build = Path(self._tmp.name) / 'build'
        chim_run(build / 'chim-world')
        written = cb.write(build / 'chim-world', build / 'toolkit', label='my build', now=NOW)
        self.assertEqual(written, build / 'toolkit' / 'cell-progress.json')
        doc = json.loads(written.read_text())
        self.assertEqual(doc['format'], cp.FORMAT)
        self.assertTrue(doc['cells']['2,2']['chim']['converted'])
        self.assertEqual(srv.build_folders(build)[0], (build / 'toolkit').resolve())
        # a tracker problem is a warning, never a failed build
        (build / 'blocked').write_text('a file where the folder should be')
        self.assertIsNone(cb.write(build / 'chim-world', build / 'blocked', now=NOW))

    def test_server_serves_the_reference_next_to_a_build(self):
        import toolkit_serve as srv
        build = Path(self._tmp.name) / 'build'
        (build / 'toolkit').mkdir(parents=True)
        (build / 'toolkit' / 'cell-progress.json').write_text('{}')
        ref = Path(self._tmp.name) / 'cell-progress-reference.json'
        ref.write_text('{"format": "aw-cell-reference-1", "cells": {}}')
        srv.Handler.reference, srv.Handler.progress_dir, srv.Handler.data_dir, srv.Handler.maps_dir, srv.Handler.metrics = (
            ref, build / 'toolkit', None, None, None)
        httpd = srv.ThreadingHTTPServer(('127.0.0.1', 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        base = 'http://127.0.0.1:%d' % httpd.server_address[1]
        self.assertEqual(json.loads(urllib.request.urlopen(base + '/data/cell-progress-reference.json').read())['format'],
                         'aw-cell-reference-1')
        self.assertEqual(json.loads(urllib.request.urlopen(base + '/data/cell-progress.json').read()), {})
        srv.Handler.reference = None
        for name in ('cell-progress-reference.json', 'live-status.json'):          # optional files: 204, never a 404 in the console
            answer = urllib.request.urlopen(base + '/data/' + name)
            self.assertEqual((answer.status, answer.read()), (204, b''))


class PageTests(unittest.TestCase):
    KIT = ROOT / 'amiwind-toolkit'

    def test_page_and_header_carry_the_tracker(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        index = (self.KIT / 'index.html').read_text(encoding='utf-8')
        for needle in ('CHIM Progress Tracker', 'id="chimbar"', 'id="chimsearch"', 'Import progress', "'../data/cell-progress.json",
                       'amiwind-chim-head', 'Interiors reached from this cell', 'Export CSV'):
            self.assertIn(needle, page, needle)
        self.assertIn('id="chimhead"', index)
        self.assertIn('amiwind-chim-pick', index)
        head = (self.KIT / 'chim-head.js').read_text(encoding='utf-8')
        self.assertIn('Done: ', head)
        self.assertIn('never counted as passed', head)

    def test_old_layers_are_still_there(self):
        page = (self.KIT / 'world-map.html').read_text(encoding='utf-8')
        for layer in ("id: 'metrics'", "id: 'density'", "id: 'content'", "id: 'full'", "id: 'poi'"):
            self.assertIn(layer, page)

    def test_files_ship_in_the_release(self):
        shipped = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for name in ('tools/cell_progress.py', 'tools/cell_progress_chim.py', 'tools/cell_progress_order.py',
                     'tools/cell_progress_md.py', 'docs/chim/CELL_TRACKER.md', 'tools/cell_progress_release.py',
                     'tools/cell_progress_ref.py', 'tools/cell_progress_build.py', 'amiwind-toolkit/chim-legend.js',
                     'tests/test_cell_progress_legend.js', 'amiwind-toolkit/header.js',
                     'amiwind-toolkit/chim-head.js', 'amiwind-toolkit/zebra.js', 'config/cell-progress-areas.json',
                     'tests/test_cell_progress.py'):
            self.assertIn(name, shipped)
            self.assertTrue((ROOT / name).is_file(), name)

    def test_no_private_paths_or_names_in_the_public_files(self):
        for name in ('tools/cell_progress.py', 'tools/cell_progress_chim.py', 'tools/cell_progress_order.py',
                     'amiwind-toolkit/chim-head.js', 'config/cell-progress-areas.json'):
            text = (ROOT / name).read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'C:[\\/]|/vol/', text, re.I), name)
            self.assertNotIn('\r', text, name)


if __name__ == '__main__':
    unittest.main()
