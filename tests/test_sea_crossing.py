# SPDX-License-Identifier: GPL-3.0-only
"""SOL-SEA-CROSSING-68 (CHIM-SEA-BETWEEN-ISLANDS-64, WORLDMAP-ONE-ISLAND-64, IMAGE-FRAME-HEAP-LAYER-STORES-UNCHECKED-68):
Solstheim and Vvardenfell in one open world, the sea between them built.

The tests that fail on the code before: the cell lists cover every cell of the map's box (no wall inside it), and a
crossing at every edge between two worlds finds a frame on the far side; the frame order and map names of the cells
built before stay; the recordless open sea is taken as open sea; the world map spans every exterior cell record; the
traversal memory check reads every store with its own index.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from chim import regions as R                       # noqa: E402
from chim import ocean_runtime as O                 # noqa: E402
from chim import sea_grid as G                      # noqa: E402

REFERENCE = ROOT / 'docs' / 'chim' / 'cell-progress-reference.json'
SOLSTHEIM = 2


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def rec(tag, data, flags=0):
    return tag.encode() + struct.pack('<III', len(data), 0, flags) + data


def cell_record(x, y, refs=(), interior=False):
    raw = sub('NAME', b'\0') + sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y))
    for n, ident, pos in refs:
        raw += sub('FRMR', struct.pack('<I', n)) + sub('NAME', ident.encode() + b'\0')
        raw += sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))
    return rec('CELL', raw)


def cells_of(path):
    return {tuple(c) for c in G.read_cells(ROOT / path)}


def worlds():
    """{cell: store} of every exterior cell the default build makes: the base world's list and recordless sea (store
    chim), Solstheim's cells of the tracker reference with its open-sea list (chimsol), and the recordless sea of the
    area Bloodmoon adds (chimsea)."""
    ref = json.loads(REFERENCE.read_text(encoding='utf-8'))['cells']
    solstheim = {tuple(int(v) for v in k.split(',')) for k, c in ref.items() if c.get('island') == SOLSTHEIM}
    out = {}
    for store, cells in (('chim', cells_of(G.BASE_CELLS) | cells_of(G.BASE_GRID)),
                         ('chimsol', solstheim | cells_of(G.MODULE_SEA)),
                         ('chimsea', cells_of(G.MODULE_GRID))):
        for c in cells:
            out.setdefault(c, store)
    return out


class TheMapsBoxIsOneWorld(unittest.TestCase):
    def test_the_cell_lists_cover_every_cell_of_the_box_once(self):
        # before: 982 cells of the box were in no list, so the edge of the world ran along each island
        base, base_grid = cells_of(G.BASE_CELLS), cells_of(G.BASE_GRID)
        module_sea, module_grid = cells_of(G.MODULE_SEA), cells_of(G.MODULE_GRID)
        self.assertTrue(base_grid and module_grid, 'the recordless open sea lists are missing')
        for a, b in ((base, base_grid), (base, module_grid), (base_grid, module_grid), (module_sea, module_grid),
                     (module_sea, base_grid)):
            self.assertFalse(a & b, 'a cell is in two lists: %s' % sorted(a & b)[:5])
        every = worlds()
        box = G.box(set(every))
        self.assertEqual(box, (-29, -19, 23, 28))
        missing = sorted(G.box_cells(box) - set(every))
        self.assertEqual(missing, [], 'cells of the map\'s box in no world (a wall inside the map): %s' % missing[:12])

    def test_the_split_follows_the_game_files(self):
        # the base game's box (Morrowind.esm, Tribunal.esm) holds the base world's recordless sea; the rest is the area
        # Bloodmoon adds (tools/chim/sea_grid.py; OpenMW globalmap.cpp: the box of every exterior CELL record)
        base_box = (-18, -19, 23, 27)
        self.assertTrue(all(G.inside(c, base_box) for c in cells_of(G.BASE_GRID)))
        self.assertFalse(any(G.inside(c, base_box) for c in cells_of(G.MODULE_GRID)))
        for path in (G.BASE_GRID, G.MODULE_GRID):
            self.assertTrue(json.loads((ROOT / path).read_text(encoding='utf-8'))['recordless'])

    def test_a_crossing_at_every_edge_between_two_worlds_finds_a_frame_beyond(self):
        # the engine's rule (aw_world.c AW_WorldDestination): past the core of the frame it stands in by 64 units, the
        # player is handed to the frame whose core holds the point, whatever store that frame is in
        every = worlds()
        rows = [(c, R.frame_row(c)) for c in every]
        edges = 0
        for c, store in every.items():
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                other = (c[0] + dx, c[1] + dy)
                if other not in every or every[other] == store:
                    continue
                edges += 1
                frame = R.frame_row(c)
                point = [frame['origin'][k] + (R.HALF + R.LEAVE_MARGIN + 8) * d for k, d in enumerate((dx, dy))]
                found = [cell for cell, f in rows
                         if all(f['origin'][k] + f['core'][0][k] <= point[k] < f['origin'][k] + f['core'][1][k]
                                for k in range(2))]
                self.assertEqual(found, [other], 'crossing %s -> %s found %s' % (c, other, found))
        # Solstheim's own coast meets its open sea and the base world's sea on every side but its own land
        self.assertGreater(edges, 100)


class OrderAndNames(unittest.TestCase):
    def test_appended_cells_come_after_and_survive_the_stage_text(self):
        kinds = {(0, 0): 'land', (5, 5): 'seabed', (-3, 2): 'ocean', (-9, -9): 'ocean'}
        before = R.ownership({c: k for c, k in kinds.items() if c not in {(-3, 2), (-9, -9)}})
        table = R.ownership(kinds, after={(-3, 2), (-9, -9)})
        self.assertEqual([f['cell'] for f in table['frames'][:2]], [f['cell'] for f in before['frames']])
        self.assertEqual([f['cell'] for f in table['frames'][2:]], [[-9, -9], [-3, 2]])
        self.assertEqual(R.check_table(table), [])
        text = R.encode_cells(R.table_kinds(table), after=R.table_after(table))
        self.assertIn(' | ', text)
        self.assertEqual(R.decode_cells(text), kinds)
        self.assertEqual(R.decode_after(text), {(-3, 2), (-9, -9)})
        again = R.ownership(R.decode_cells(text), after=R.decode_after(text))
        self.assertEqual(again['frames'], table['frames'])

    def test_without_appended_cells_everything_is_as_before(self):
        kinds = {(1, 1): 'land', (0, 0): 'ocean'}
        self.assertEqual(R.encode_cells(kinds), '0,0:o 1,1:l')
        self.assertNotIn('appended', R.ownership(kinds))
        self.assertEqual(R.decode_after('0,0:o 1,1:l'), set())

    def test_routing_rows_of_the_recordless_sea_come_after_the_earlier_ones(self):
        old = [dict(name='vf0000', cell=[0, 0], origin=[1024, 1024, 0], core=[[-1024, -1024], [1024, 1024]],
                    coverage=[[-1920, -1920], [1920, 1920]])]
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'Morrowind.esm').write_bytes(b'')
            rows, added = O.append_routing_rows(old, [(-6, 26), (-18, 15), (-30, 1)], t, after={(-30, 1)})
            self.assertEqual([r['cell'] for r in added], [[-18, 15], [-6, 26], [-30, 1]])
            self.assertEqual([r['name'] for r in added], ['vf0001', 'vf0002', 'vf0003'])

    def test_the_sea_store_numbers_its_frame_maps_on_after_solstheim(self):
        from chim import sol_test
        first = sol_test.directory_rows([R.frame_row((-20, 20)), R.frame_row((-21, 20))])
        both = sol_test.directory_rows([R.frame_row((-29, 0))], before=first)
        self.assertEqual(sol_test.rows_count(both), 3)
        self.assertEqual(both[8 + 2 * 52:8 + 2 * 52 + 6], b'sl0002')
        self.assertEqual(both[:8 + 2 * 52][8:], first[8:])
        self.assertEqual(sol_test.LANDS['chimsea']['after'], 'chimsol')
        self.assertEqual(sol_test.closed_frames([R.frame_row((-29, 0))], 'open'), set())

    def test_the_frame_holders_continue_the_numbering(self):
        from chim import layer_stores
        with tempfile.TemporaryDirectory() as t:
            values = []
            for store, cells in (('chimsol', [(-20, 20), (-21, 20)]), ('chimsea', [(-29, 0)])):
                world = Path(t) / store
                world.mkdir()
                (world / R.TABLE_FILE if hasattr(R, 'TABLE_FILE') else world / 'chim-regions.json').write_text(
                    json.dumps(R.ownership({c: 'ocean' for c in cells})), encoding='utf-8')
                values.append('%s=%s' % (store, world))
            holders = layer_stores.frame_holders(values)
            self.assertEqual(holders[(-29, 0)][0], 'sl0002')
            self.assertEqual(holders[(-21, 20)][0], 'sl0000')
            # the door check walks each store's world with its own {frame map: cell}: the far sea's frames keep the
            # names after Solstheim's whatever the order (the v0.0.68 release build traced 83 Solstheim doors in the
            # far sea's world: DOOR-CHECK-SEA-STORE-NAMES-68)
            import door_engine_check
            for order in (values, list(reversed(values))):
                walks = {str(folder): cells for folder, cells in door_engine_check.layer_frame_cells(order)}
                self.assertEqual(walks[str(Path(t) / 'chimsea')], {'sl0002': (-29, 0)})
                self.assertEqual(walks[str(Path(t) / 'chimsol')], {'sl0000': (-21, 20), 'sl0001': (-20, 20)})


class TheRecordlessRule(unittest.TestCase):
    def write(self, t, cells, recordless):
        path = Path(t) / ('grid.json' if recordless else 'plain.json')
        doc = {'format': R.CELLS_FORMAT, 'cells': ['%d,%d' % c for c in cells]}
        if recordless:
            doc['recordless'] = True
        path.write_text(json.dumps(doc), encoding='utf-8')
        status = Path(t) / 'status.json'
        status.write_text(json.dumps({'cells': {'0,0': {'status': 'terrain_complete', 'island': 1}}}),
                          encoding='utf-8')
        return path, status

    def test_a_recordless_cell_is_open_sea_without_a_tracker_status(self):
        with tempfile.TemporaryDirectory() as t:
            grid, status = self.write(t, [(1, 0), (-1, 0)], True)
            table, problems = R.plan(['@' + str(grid)], status)
            self.assertEqual(problems, [])
            self.assertEqual(R.table_kinds(table), {(1, 0): 'ocean', (-1, 0): 'ocean'})
            self.assertEqual(R.table_after(table), {(1, 0), (-1, 0)})
            self.assertEqual(table['selection']['recordless'], 2)

    def test_an_ordinary_list_still_needs_the_tracker(self):
        with tempfile.TemporaryDirectory() as t:
            plain, status = self.write(t, [(1, 0)], False)
            table, problems = R.plan(['@' + str(plain)], status)
            self.assertTrue(problems)

    def test_a_listed_cell_with_a_record_is_refused_in_seconds(self):
        with tempfile.TemporaryDirectory() as t:
            grid, status = self.write(t, [(1, 0), (4, 4)], True)
            data = Path(t) / 'data'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(cell_record(4, 4) + rec('LAND', sub('INTV', struct.pack('<ii', 9, 9))))
            table, problems = R.plan(['@' + str(grid)], status)
            found = R.recordless_problems(table, data)
            self.assertEqual(len(found), 1)
            self.assertIn('4,4', found[0])

    def test_the_cached_admission_is_the_full_read_admission(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            (p / 'Morrowind.esm').write_bytes(cell_record(2, 2) + cell_record(0, 0, interior=True))
            (p / 'Bloodmoon.esm').write_bytes(rec('LEVC', sub('NAME', b'horker\0'))
                                              + cell_record(-20, 15, [(33410, 'horker', [-163000, 127000, -1300])]))
            for c in ((-20, 15), (-25, -5)):
                self.assertEqual(O.admit_cell(p, c), O.admit_cell_full_read(p, c))


class TheWorldMap(unittest.TestCase):
    def test_the_map_spans_every_exterior_cell_record(self):
        import prepare_world_ui as W
        raw = cell_record(-29, 23) + cell_record(23, -19) + cell_record(99, 99, interior=True) + cell_record(0, 28)
        self.assertEqual(W.record_bounds(raw), (-29, -19, 24, 29))

    def test_the_terrain_picture_is_placed_in_the_larger_box(self):
        import prepare_world_ui as W
        from PIL import Image
        picture = Image.new('RGB', (64, 32), (200, 10, 10))            # 2 x 1 cells at 32 pixels a cell
        placed = W.map_picture(picture, (0, 0, 2, 1), (-1, -1, 3, 2))   # 4 x 3 cells
        self.assertEqual(placed.size, (128, 96))
        self.assertEqual(placed.getpixel((0, 0))[3], 0)                 # open sea outside the picture
        self.assertEqual(placed.getpixel((40, 40))[:3], (200, 10, 10))  # the picture one cell in, one cell down
        palette = bytes(range(256)) * 3
        raw = W.map_asset({'terrain_bounds': [0, 0, 2, 1], 'map_bounds': [-1, -1, 3, 2], 'areas': []}, placed,
                          palette)
        self.assertEqual(struct.unpack_from('<4i', raw, 8), (-8192, -8192, 3 * 8192, 2 * 8192))


class TheTraversalMemoryCheck(unittest.TestCase):
    def store(self, root, name, cells, peak):
        from chim import format as F
        world = Path(root) / name
        (world / 'chim').mkdir(parents=True)
        toc = F.INDEX_TOC.pack(0, 10 + 26 * len(cells), 0, 5, 0, 0, 7, 0)
        (world / 'chim' / 'world.cwi').write_bytes(F.HEADER.pack(b'CHIM', b'INDX', 0, 11, 32, 0, 0, 0, 0)
                                                   + b'\0' * F.SETTINGS.size + toc)
        rows = []
        for c in cells:
            rel = 'frames/x%+03d/y%+03d/frame.ccf' % c
            (world / 'chim' / rel).parent.mkdir(parents=True)
            (world / 'chim' / rel).write_bytes(F.HEADER.pack(b'CHIM', b'FRAM', 0, 11, 32, 0, 0, 0, 0)
                                               + F.FRAME_BLOCK.pack(c[0], c[1], 0, 0, 0, 0, 256, 15, 15, 3, 10))
            rows.append({'frame': rel, 'peak_bytes': peak, 'gated_ring': 'active', 'budget_bytes': 6242304,
                         'peak_breakdown': {}, 'largest_block_bytes': 1000, 'load_ring': {'peak_bytes': peak}})
        (world / 'chim-heap.json').write_text(json.dumps({'frames': rows}), encoding='utf-8')
        return world

    def test_every_store_and_every_store_edge_is_checked(self):
        from chim import traversal_heap as T
        with tempfile.TemporaryDirectory() as t:
            stores = {'chim': self.store(t, 'base', [(-19, 15)], 1000000),
                      'chimsol': self.store(t, 'sol', [(-20, 15)], 1000000)}
            report, problems = T.check(stores)
            self.assertEqual(problems, [])
            self.assertEqual(len(report['store_edges']), 1)
            self.assertEqual(set(report['stores']), {'chim', 'chimsol'})
            self.assertGreater(report['stores']['chimsol']['store_index'], 0)

    def test_an_overflow_names_its_store_and_cell(self):
        from chim import traversal_heap as T
        with tempfile.TemporaryDirectory() as t:
            stores = {'chim': self.store(t, 'base', [(-19, 15)], 1000000),
                      'chimsea': self.store(t, 'sea', [(-20, 15)], 9000000)}
            report, problems = T.check(stores)
            self.assertTrue(any('store chimsea (cell -20,15)' in p for p in problems), problems)
            self.assertTrue(any(p.startswith('store edge') for p in problems), problems)


class DiagnosticReports(unittest.TestCase):
    def test_the_mesh_method_set_reports_are_diagnostic(self):
        # CHIM-REBUILD-NOT-IDENTICAL-68: a module world rebuilt from its units differed only in these two reports
        import build_cache
        for name in ('mesh-method-set.json', 'mesh-method-set.jsonl', 'chim-stats.json', 'chim-timing.json'):
            self.assertTrue(build_cache.diagnostic('bloodmoon-solstheim/' + name), name)
        self.assertFalse(build_cache.diagnostic('bloodmoon-solstheim/chim-regions.json'))


if __name__ == '__main__':
    unittest.main()
