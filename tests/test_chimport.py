# SPDX-License-Identifier: GPL-3.0-only
"""tools/chimport.py (docs/chim/CHIMPORT.md): the ring order from the sea inwards, resume from the state file,
a failing or crashing cell never stops the run, the stop file, the per-cell result and tracker schemas, the
one-cell frame settings, and flat default land for cells without a LAND record (src/mwad/audit.py)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import chimport as C  # noqa: E402


def grid(w, h, sea=()):
    """A w x h block of land cells plus sea-only cells with content."""
    cells = {(x, y): {'land': True, 'refs': 1} for x in range(w) for y in range(h)}
    for c in sea:
        cells[c] = {'land': False, 'refs': 3}
    return cells


# A stand-in for one cell process: writes a result, fails, or crashes, by cell number.
FAKE_CELL = r'''
import json, sys
from pathlib import Path
args = sys.argv[1:]
cell = args[args.index('--cell') + 1]
out = Path(args[args.index('--out') + 1])
x, y = (int(v) for v in cell.split(','))
if x == 1 and y == 1:
    raise SystemExit('crash in cell')
mech = ('format_validation', 'sky_bank_texels', 'seam_tears', 'far_terrain', 'stair_walk', 'memory_fit',
        'hull_bevels', 'hidden_faces', 'sprite_shape', 'actor_grounding', 'door_links', 'vis')
ok = not (x == 2 and y == 0)
res = {'format': 'aw-chimport-cell-1', 'cell': [x, y], 'key': cell, 'converted': ok, 'started': 't', 'finished': 'f',
       'errors': [] if ok else [{'stage': 'build', 'mechanism': 'missing-terrain', 'message': 'x'}],
       'records': {'by_type': {'STAT': {'placed': 2, 'converted': 2 if ok else 0, 'deferred': {}, 'failed': 0,
                                        'skipped': {}}},
                   'totals': {'placed': 2, 'converted': 2 if ok else 0, 'deferred': 0, 'failed': 0, 'skipped': 0}},
       'audits': {m: {'status': 'passed' if ok else 'not_measured', 'detail': '', 'numbers': {}} for m in mech},
       'stats': {'meshes': {'new': 1, 'reused': 1, 'unique_in_cell': 2}, 'disk': {'chim_bytes': 10, 'chunks': 64},
                 'faces': {'source_triangles': 5, 'placed': 9, 'terrain': 4, 'stored': 7}},
       'wall_s': 0.1, 'cpu_s': 0.1}
out.mkdir(parents=True, exist_ok=True)
(out / 'result.json').write_text(json.dumps(res))
'''


class Order(unittest.TestCase):
    def test_rings_peel_from_the_coast_inwards(self):
        r = C.rings(set(grid(5, 5)))
        self.assertEqual(r[(0, 0)], 1)
        self.assertEqual(r[(1, 1)], 2)
        self.assertEqual(r[(2, 2)], 3)
        self.assertEqual(sorted(set(r.values())), [1, 2, 3])

    def test_order_starts_at_sea_then_outer_ring_and_visits_each_cell_once(self):
        cells = grid(5, 5, sea=[(-2, 2), (7, 2)])
        order = C.order_cells(cells)
        self.assertEqual({c for c, _ in order[:2]}, {(-2, 2), (7, 2)})
        self.assertEqual({k for _, k in order[:2]}, {0})
        self.assertEqual(len(order), len(cells))
        self.assertEqual(len({c for c, _ in order}), len(cells))
        rings = [k for _, k in order]
        self.assertEqual(rings, sorted(rings))      # never back outwards

    def test_a_ring_walk_is_contiguous(self):
        order = [c for c, k in C.order_cells(grid(6, 6)) if k == 1]
        for a, b in zip(order, order[1:]):
            self.assertLessEqual(max(abs(a[0] - b[0]), abs(a[1] - b[1])), 1)

    def test_order_is_deterministic(self):
        self.assertEqual(C.order_cells(grid(7, 4, sea=[(9, 9)])), C.order_cells(grid(7, 4, sea=[(9, 9)])))

    def test_select_limits_rings_and_cells(self):
        plan = {'cells': [dict(x=c[0], y=c[1], ring=k, order=i) for i, (c, k) in enumerate(C.order_cells(grid(5, 5)), 1)]}
        self.assertTrue(all(r['ring'] < 2 for r in C.select(plan, 2)))
        self.assertEqual([(r['x'], r['y']) for r in C.select(plan, None, [(2, 2), (0, 0)])], [(0, 0), (2, 2)])


class CellSettings(unittest.TestCase):
    def test_one_cell_frame_is_a_valid_town_frame(self):
        from town_config import validate_town
        from town_regions import regions
        s = C.cell_settings((-3, 25))
        validate_town(s['town'], s)
        self.assertEqual(s['centre'], [-3 * 8192 + 4096, 25 * 8192 + 4096])
        self.assertEqual(s['bounds'], [[-1024, -1024], [1024, 1024]])
        self.assertTrue(all(isinstance(v, int) for p in s['bounds'] for v in p))
        self.assertEqual(len(regions(s)), 4)
        self.assertEqual(2048 // C.FRAME_SETTINGS['grain'] % C.FRAME_SETTINGS['sector_chunks'], 0)

    def test_cell_area_serves_the_settings_and_restores_the_loader(self):
        import town_config
        from chim.units import UnitCache
        s = C.cell_settings((1, 2))
        before = town_config.load_settings, UnitCache.put
        with C.cell_area(s) as ident:
            self.assertIs(town_config.load_settings(ident), s)
            with tempfile.TemporaryDirectory() as d:
                cache = UnitCache(d)
                cache.put('mesh', 'ab' * 8, {'v': 1})
                self.assertEqual(cache.get('mesh', 'ab' * 8), {'v': 1})
                self.assertEqual(list(Path(d).rglob('*.tmp')), [])
        self.assertEqual((town_config.load_settings, UnitCache.put), before)

    def test_cell_command_passes_negative_cells_safely(self):
        args = SimpleNamespace(data_files=Path('/d'), palette=Path('/p'), out=Path('/r'), jobs=1, qbsp=None)
        cmd = C.cell_command(args, {'x': -6, 'y': 25})
        self.assertIn('--cell=-6,25', cmd)
        with patch.object(C, 'convert_cell', lambda *a, **k: {'key': '-6,25', 'converted': True, 'errors': [],
                                                                'audits': {}, 'wall_s': 0}), patch('sys.stdout'):
            self.assertEqual(C.main(cmd[2:]), 0)    # the parser takes the negative cell

    def test_hull_audit_reads_kept_chains_as_their_own_outcome(self):
        hulls = [{'name': 'x/rock_wg_12@s1', 'clipnodes': 300, 'depth': 300, 'over': True},
                 {'name': 'x/ex_house@s1', 'clipnodes': 900, 'depth': 280, 'over': True},
                 {'name': 'x/small@s1', 'clipnodes': 10, 'depth': 10, 'over': False}]
        rec = {'by_type': {}, 'totals': {}}
        a = C.audits_of(None, None, None, hulls, None, rec, {'hull_fallback': {'kept_chain': ['meshes/x/rock_wg_12.nif']}})
        h = a['hull_bevels']
        self.assertEqual(h['status'], 'failed')
        self.assertEqual(h['numbers']['over_limit'], 1)
        self.assertEqual(h['numbers']['kept_as_chain_for_memory'], ['rock_wg_12'])
        a = C.audits_of(None, None, None, hulls[:1] + hulls[2:], None, rec,
                        {'hull_fallback': {'kept_chain': ['meshes/x/rock_wg_12.nif']}})
        self.assertEqual(a['hull_bevels']['status'], 'passed')
        self.assertEqual(a['hull_bevels']['outcome'], 'kept_as_chain')
        res = {'converted': True, 'errors': [], 'audits': a, 'stats': {},
               'records': {'by_type': {}, 'totals': {'placed': 1, 'converted': 1, 'deferred': 0, 'failed': 0, 'skipped': 0}}}
        self.assertEqual(C.tracker_cell(res, {})['audits']['hull_bevels']['outcome'], 'kept_as_chain')

    def test_hull_rule_uses_the_shared_check_when_the_builder_has_it(self):
        import hull_chain_audit
        if hasattr(hull_chain_audit, 'over_limit'):
            self.assertFalse(C.hull_over_limit(1800, 5000))        # routed: reach > depth
            self.assertTrue(C.hull_over_limit(300, 300))
        else:
            self.assertTrue(C.hull_over_limit(256, 256))
            self.assertFalse(C.hull_over_limit(255, 255))

    def test_meshless_lights_are_lights_not_markers(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            (work / 'audit').mkdir()
            (work / 'audit/placements.json').write_text(json.dumps([
                {'number': 1, 'type': 'LIGH', 'id': 'light_fire'}, {'number': 2, 'type': 'STAT', 'model': 'x.nif'},
                {'number': 3, 'type': 'STAT', 'model': 'marker_x.nif'}]))
            (work / 'source-catalogue.json').write_text(json.dumps({'deferred': [
                {'number': 1, 'status': 'nonvisual source marker'}, {'number': 3, 'status': 'nonvisual source marker'}]}))
            acc = C.record_accounting(work, None, {2})
        self.assertEqual(acc['by_type']['LIGH']['deferred'], {C.MESHLESS_LIGHT_REASON: 1})
        self.assertEqual(acc['by_type']['STAT']['deferred'], {'nonvisual source marker': 1})

    def test_errors_are_classed_by_mechanism(self):
        self.assertEqual(C.classify('ValueError: Selected square has missing terrain; choose'), 'missing-terrain')
        self.assertEqual(C.classify('ValueError: Stair walkability gate failed on the CHIM world'), 'stair-walk')
        self.assertEqual(C.classify('ValueError: CHIM heap gate failed: x'), 'heap-ring')
        self.assertEqual(C.classify('something new'), 'other')
        self.assertEqual(C.classify('cell process exited 2 without a result: usage: chimport.py cell [-h] --qbsp'),
                         'runner-usage')
        self.assertEqual(C.classify('ValueError: max() iterable argument is empty'), 'measure-empty-world')


class DefaultLand(unittest.TestCase):
    def test_flat_default_land_packs_as_terrain(self):
        if not hasattr(sys.modules.get('mwad'), '__path__'):   # tools/mwad.py imported by another test module
            sys.modules.pop('mwad', None)
            sys.path.insert(0, str(ROOT / 'src'))
        from mwad.audit import DEFAULT_LAND_HEIGHT, default_land, terrain_packet
        land = default_land()
        self.assertEqual(len(land['heights']), 65)
        self.assertTrue(all(v == DEFAULT_LAND_HEIGHT for row in land['heights'] for v in row))
        self.assertEqual(len(terrain_packet(land, 0, 0, 0, 0, 2)) % 32, 0)


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name) / 'run'
        self.run_dir.mkdir()
        cells = grid(3, 3)
        plan = {'format': C.PLAN_FORMAT, 'cells': [dict(x=c[0], y=c[1], ring=k, order=i, land=True, refs=1, name='',
                                                        region='r', categories={'statics': 1})
                                                   for i, (c, k) in enumerate(C.order_cells(cells), 1)]}
        C.write_json(self.run_dir / 'plan.json', plan)
        fake = Path(self.tmp.name) / 'fake_cell.py'
        fake.write_text(FAKE_CELL)
        self.fake = fake

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, **kw):
        a = dict(out=self.run_dir, data_files=Path('/none'), palette=Path('/none'), qbsp=None, sdk=None, workers=3,
                 jobs=1, rings=None, cells=None, retry_failed=False, timeout=60, dry_run=False,
                 no_world=True, world_timeout=60, world_every=1, tracker=None, tracker_tool=None, tracker_ingest='', feed_every=0)
        a.update(kw)
        return SimpleNamespace(**a)

    def go(self, **kw):
        fake = self.fake

        def command(args, row):
            return [sys.executable, str(fake), '--cell', '%d,%d' % (row['x'], row['y']),
                    '--out', str(args.out / 'cells' / C.cell_dir((row['x'], row['y'])))]
        with patch.object(C, 'cell_command', command), patch.object(C, 'inputs_lock', lambda *a: None),                 patch('sys.stdout'):
            return C.run(self.args(**kw))

    def test_failures_never_stop_the_run_and_are_classed(self):
        self.go()
        state = C.read_json(self.run_dir / 'state.json')
        self.assertEqual(len(state['cells']), 9)
        st = {k: v['status'] for k, v in state['cells'].items()}
        self.assertEqual(st['1,1'], 'failed')                  # crashed: no result
        self.assertEqual(st['2,0'], 'failed')                  # converter error
        self.assertEqual(sum(v == 'done' for v in st.values()), 7)
        crash = C.read_json(self.run_dir / 'cells' / C.cell_dir((1, 1)) / 'result.json')
        self.assertEqual(crash['errors'][0]['stage'], 'process')
        summary = C.read_json(self.run_dir / 'summary.json')
        self.assertEqual(summary['total']['cells'], 9)
        self.assertIn('missing-terrain (build)', summary['error_classes'])
        self.assertEqual(summary['total']['done'], summary['total']['passed'] + summary['total']['empty'])
        self.assertEqual(summary['total']['failed'], 2)                # failed includes not_converted ...
        self.assertEqual(summary['total']['not_converted'], 2)         # ... which is also counted apart
        lines = (self.run_dir / 'progress.jsonl').read_text().splitlines()
        self.assertEqual(len(lines), 9)
        self.assertTrue(all(json.loads(x)['stage'] == 'chimport-cell' for x in lines))

    def test_resume_skips_done_cells_and_retry_runs_failed_ones(self):
        self.go(cells='0,0 0,1')
        first = C.read_json(self.run_dir / 'state.json')
        self.assertEqual(set(first['cells']), {'0,0', '0,1'})
        self.go()
        state = C.read_json(self.run_dir / 'state.json')
        self.assertEqual(state['cells']['0,0']['attempts'], 1)       # not run again
        self.assertEqual(len(state['cells']), 9)
        self.go(retry_failed=True)
        state = C.read_json(self.run_dir / 'state.json')
        self.assertEqual(state['cells']['1,1']['attempts'], 2)
        self.assertEqual(state['cells']['0,0']['attempts'], 1)

    def test_stop_file_starts_nothing_new(self):
        (self.run_dir / 'STOP').write_text('')
        self.go()
        self.assertEqual((C.read_json(self.run_dir / 'state.json') or {'cells': {}})['cells'], {})

    def test_rings_limit_and_dry_run(self):
        self.go(dry_run=True)
        self.assertFalse((self.run_dir / 'state.json').exists())
        self.go(rings=2)
        state = C.read_json(self.run_dir / 'state.json')
        self.assertEqual(len(state['cells']), 8)                     # the centre cell is ring 2

    def test_empty_cells_are_counted_apart_from_passed(self):
        res = {'converted': True, 'errors': [], 'audits': {'x': {'status': 'passed'}},
               'records': {'totals': {'placed': 0}}}
        self.assertEqual(C.cell_status(res), 'empty')
        res['records']['totals']['placed'] = 3
        self.assertEqual(C.cell_status(res), 'passed')
        res['audits']['x']['status'] = 'failed'
        self.assertEqual(C.cell_status(res), 'failed')
        self.assertEqual(C.cell_status({'converted': False}), 'not_converted')
        hull = {'converted': True, 'errors': [], 'records': {'by_type': {}, 'totals': {'placed': 3, 'converted': 3, 'deferred': 0, 'failed': 0, 'skipped': 0}},
                'audits': {'hull_bevels': {'status': 'failed', 'detail': 'x'}, 'stair_walk': {'status': 'passed'}}}
        self.assertEqual(C.cell_status(hull), 'hull_pending')
        cell = C.tracker_cell(dict(hull, stats={}), {})
        self.assertEqual(cell['status'], 'hull_pending')
        self.assertFalse(cell['eligible'])
        self.assertEqual(cell['audits']['hull_bevels']['status'], 'not_measured')
        hull['audits']['stair_walk']['status'] = 'failed'
        self.assertEqual(C.cell_status(hull), 'failed')

    def test_a_finished_ring_builds_the_growing_world(self):
        made = []

        def world(args, ring):
            made.append(ring)
            return [sys.executable, '-c', 'pass']
        with patch.object(C, 'world_command', world):
            self.go(no_world=False)
        self.assertEqual(sorted(made), [1, 2])

    def test_world_every_n_rings_and_after_the_last(self):
        made = []

        def world(args, ring):
            made.append(ring)
            return [sys.executable, '-c', 'pass']
        with patch.object(C, 'world_command', world):
            self.go(no_world=False, world_every=5)
        self.assertEqual(made, [2])

    def test_finished_cells_are_fed_to_the_tracker_automatically(self):
        tool = Path(self.tmp.name) / 'fake_tracker.py'
        log = Path(self.tmp.name) / 'tracker.log'
        tool.write_text('import sys\nopen(%r, "a").write(" ".join(sys.argv[1:3]) + chr(10))\n' % str(log))
        self.go(tracker=Path(self.tmp.name) / 'trk', tracker_tool=tool, tracker_ingest='--png')
        calls = log.read_text().splitlines()
        self.assertIn('result --out', calls)
        self.assertIn('ingest --out', calls)
        fed = C.read_json(self.run_dir / 'tracker' / 'fed.json')
        self.assertEqual(len(fed), 9)                                 # every finished cell, no manual step

    def test_feed_writes_tracker_results_once(self):
        self.go()
        path = C.feed(self.run_dir)
        doc = C.read_json(path)
        self.assertEqual(doc['format'], 'aw-cell-result-1')
        self.assertEqual(len(doc['cells']), 9)
        for k, v in doc['cells'].items():
            self.assertTrue(set(v['audits']) <= set(C.TRACKER_MECHANISMS))
            self.assertTrue(all(a['status'] in ('passed', 'failed', 'accepted', 'not_measured')
                                for a in v['audits'].values()))
            self.assertIsInstance(v['stats'], dict)
            self.assertIn(v['converted'], (True, False))
        good = doc['cells']['0,0']['stats']
        self.assertEqual(good['faces']['before'], 5)
        self.assertEqual(good['faces']['chim_placed'], 5)
        self.assertEqual(good['meshes'], {'new': 1, 'reused': 1, 'unique': 2})
        self.assertIsNone(C.feed(self.run_dir))                       # nothing new
        rows = C.export_rows(self.run_dir)
        self.assertEqual(len(rows), 9)
        self.assertEqual(set(rows[0]), set(C.EXPORT_FIELDS))


if __name__ == '__main__':
    unittest.main()
