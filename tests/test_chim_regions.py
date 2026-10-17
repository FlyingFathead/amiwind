# SPDX-License-Identifier: GPL-3.0-only
"""CHIM regions (docs/chim/CHIM_REGIONS.md): exterior cells on CHIM inside the legacy open world.

Synthetic data only: a tracker file of a few cells, a one-row world region directory and a one-entity map.
Covers the selection formats, the preflight (status, open sea, towns, pockets; divided cells taken), the ownership
table, the stage-command cell form (the chim stage's key covers exactly the cells), the frame settings
(the stitcher's margin rule), adjacent frames sharing margin terrain but never their owned box, the in-place
replacement of an open-world map by its frame map, and the optimizer receipt's rebind of replaced maps.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import regions as R  # noqa: E402

DONE = 'complete_unlit'


def tracker(cells):
    """A tracker store (aw-cell-progress-1 shape) of {(x, y): (status, ring, region)}."""
    return {'format': 'aw-cell-progress-1', 'cells': {
        '%d,%d' % c: {'chim': {'status': s}, 'ring': ring, 'region': region, 'set': 'vvardenfell',
                      'legacy': {'maps': ['vf%04d' % i]}}
        for i, (c, (s, ring, region)) in enumerate(sorted(cells.items()))}}


def ring_statuses():
    """A 5 x 5 block: a ring of seabed cells around 3 x 3 finished land cells, one of them not finished."""
    cells = {}
    for x in range(5):
        for y in range(5):
            edge = x in (0, 4) or y in (0, 4)
            cells[(x, y)] = ('empty_sea', 0, 'Bitter Coast Region') if edge else (DONE, 1, 'Bitter Coast Region')
    cells[(2, 2)] = ('hull_policy_pending', 2, 'West Gash Region')
    return cells


class Selection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.status = self.dir / 'cell-progress.json'
        self.status.write_text(json.dumps(tracker(ring_statuses())), encoding='utf-8')
        self.statuses = R.load_status(self.status)

    def tearDown(self):
        self.tmp.cleanup()

    def test_named_sets_and_regions(self):
        seabed = R.named_cells('seabed', self.statuses)
        self.assertEqual(len(seabed), 16)
        coast = R.named_cells('coast', self.statuses)
        self.assertEqual(len(coast), 8)                       # ring 1 land cells; the pending one is ring 2
        self.assertEqual(R.named_cells('sea-ring', self.statuses), sorted(set(seabed) | set(coast)))
        cells, explicit, record = R.select(['bitter coast'], self.statuses)
        self.assertEqual(len(cells), 24)                      # finished cells of the region only
        self.assertEqual(explicit, [])
        with self.assertRaises(ValueError):
            R.select(['Nowhere'], self.statuses)

    def test_cell_files(self):
        csv_head = self.dir / 'cells.csv'
        csv_head.write_text('name,x,y,status\nA,0,0,ok\nB,1,0,ok\n', encoding='utf-8')
        csv_bare = self.dir / 'bare.csv'
        csv_bare.write_text('0,0\n1,0\n', encoding='utf-8')
        cells_json = self.dir / 'cells.json'
        cells_json.write_text(json.dumps({'format': R.CELLS_FORMAT, 'cells': [[0, 0], '1,0'], 'reason': 'test'}),
                              encoding='utf-8')
        state = self.dir / 'state.json'
        state.write_text(json.dumps({'selected_cells': [{'cell': '0,0'}, {'cell': [1, 0]}], 'zoom': 2}),
                         encoding='utf-8')
        for path in (csv_head, csv_bare, cells_json, state):
            cells, explicit, record = R.select(['@' + str(path)], self.statuses)
            self.assertEqual(cells, [(0, 0), (1, 0)], path.name)
            self.assertEqual(explicit, [(0, 0), (1, 0)])
            self.assertEqual(len(record['files'][0]['sha256']), 64)
        bad = self.dir / 'bad.json'
        bad.write_text(json.dumps({'format': R.CELLS_FORMAT, 'cells': [], 'extra': 1}), encoding='utf-8')
        with self.assertRaises(ValueError):
            R.select(['@' + str(bad)], self.statuses)

    def test_preflight_refusals(self):
        statuses = dict(self.statuses)
        statuses[(9, 9)] = dict(statuses[(0, 0)], status='ocean')
        statuses[(9, 8)] = dict(statuses[(0, 0)], legacy_maps=['vf0001', 'vf0002'])
        kept, problems, dropped = R.preflight([(2, 2), (9, 9), (9, 8), (0, 0)], {(2, 2), (9, 9), (9, 8), (0, 0)},
                                              statuses, {})
        # a cell the tracker lists with several legacy maps (a divided cell, or maps whose apron holds its objects)
        # is taken: its one frame owns the whole cell (CHIM-REGION-DIVIDED-CELLS-36)
        self.assertEqual(kept, [(9, 9), (9, 8), (0, 0)])
        text = '\n'.join(problems)
        self.assertIn('2,2: CHIMport status hull_policy_pending', text)
        self.assertNotIn('9,9', text)
        self.assertNotIn('9,8', text)
        # the earlier method (--chim-region-rows legacy) copies one legacy map: it still refuses such a cell
        kept, problems, dropped = R.preflight([(9, 8), (0, 0)], set(), statuses, {}, one_map_only=True)
        self.assertEqual(kept, [(0, 0)])
        self.assertIn('9,8: the tracker lists 2 legacy maps', problems[0])

    def test_coast2_takes_rings_1_and_2_and_names_every_cell_left_out(self):
        # maintainer 2026-10-11: the entire coastline, all of ring 1 and every possible cell of ring 2, as CHIM
        statuses = dict(self.statuses)
        statuses[(9, 9)] = dict(statuses[(1, 1)], status='hull_policy_pending', ring=2)
        statuses[(9, 8)] = dict(statuses[(1, 1)], status='complete_unlit', ring=3)
        statuses[(2, 2)] = dict(statuses[(1, 1)])              # finished: no legacy pocket in the middle
        cells = R.named_cells('coast2', statuses)
        self.assertIn((9, 9), cells)
        self.assertNotIn((9, 8), cells)
        self.assertEqual(sorted(c for c in cells if statuses[c]['ring'] not in (1, 2)), [])
        kept, problems, dropped = R.preflight(cells, set(), statuses, {})
        self.assertEqual(problems, [])
        self.assertIn((1, 1), kept)
        self.assertEqual({tuple(d['cell']) for d in dropped}, {(9, 9)})
        self.assertIn('hull_policy_pending', dropped[0]['reason'])
        # the same cell named explicitly (a cell file) is refused, as before
        kept, problems, dropped = R.preflight([(9, 9)], {(9, 9)}, statuses, {})
        self.assertIn('9,9: CHIMport status hull_policy_pending', problems[0])

    def test_towns_win(self):
        box = R.cell_box((0, 0))
        kept, problems, dropped = R.preflight([(0, 0), (1, 0)], set(), self.statuses, {'seyda': box})
        self.assertEqual(kept, [(1, 0)])
        self.assertEqual(dropped[0]['cell'], [0, 0])
        self.assertEqual(problems, [])
        # a cell listed by name inside a town frame is dropped too, recorded as listed (towns win: the whole-city
        # Vivec frame takes 16 cells of the coast lists, project decision 2026-10-11 09:55)
        kept, problems, dropped = R.preflight([(0, 0), (1, 0)], {(0, 0)}, self.statuses, {'seyda': box})
        self.assertEqual((kept, problems), ([(1, 0)], []))
        self.assertIn('inside the frame of seyda', dropped[0]['reason'])
        self.assertIn('listed by name', dropped[0]['reason'])

    def test_pockets(self):
        ring = [c for c in self.statuses if c != (2, 2)]
        self.assertEqual(R.holes(ring), [[(2, 2)]])
        # a pocket open only at a corner is enclosed (leaving it crosses a selected cell)
        corner = [(0, 1), (1, 0), (1, 2), (2, 1)]
        self.assertEqual(R.holes(corner), [[(1, 1)]])
        # a large enclosed area (an island inside a sea ring) is legacy territory, not a pocket
        big = [(x, y) for x in range(6) for y in range(6) if x in (0, 5) or y in (0, 5)]
        self.assertEqual(R.holes(big), [])
        self.assertEqual(R.components(big), 1)
        table, problems = R.plan(['sea-ring'], self.status)
        self.assertEqual(table['counts']['cells'], 24)
        self.assertTrue(any('legacy pocket' in p for p in problems))

    def test_table_and_stage_cells(self):
        table, problems = R.plan(['seabed'], self.status)
        self.assertEqual(problems, [])
        self.assertEqual(R.check_table(table), [])
        self.assertEqual(table['counts']['seabed'], 16)
        kinds = R.table_kinds(table)
        text = R.encode_cells(kinds)
        self.assertEqual(R.decode_cells(text), kinds)
        self.assertEqual(R.encode_cells(R.decode_cells(text)), text)          # stable: the stage key
        with self.assertRaises(ValueError):
            R.decode_cells('1,2:x')
        broken = json.loads(json.dumps(table))
        broken['frames'][1]['cells'] = broken['frames'][0]['cells']
        self.assertTrue(R.check_table(broken))

    def test_frame_ids(self):
        self.assertEqual(R.frame_id((-7, 2)), 'rcm7_p2')
        self.assertEqual(R.frame_id((0, -12)), 'rcp0_m12')


class FrameSettings(unittest.TestCase):
    def test_subcell_union_keeps_apron_without_expanding_logical_core(self):
        from town_regions import regions, audit_coverage, select_references
        s = R.frame_settings(R.frame_row((0, 0)))
        def ref(n, x, y):
            p = [(v + s['centre'][i] * s['scale']) / s['scale'] for i, v in enumerate((x, y))]
            return {'number': n, 'bounds': [p, p]}
        index = {'references': [ref(1, 0, 0), ref(2, -1900, -1900),
                                ref(3, 1900, 1900), ref(4, 2000, 2000)]}
        rows = regions(s)
        self.assertEqual(audit_coverage(index, rows, s)['covered_references'], 3)
        self.assertEqual(set().union(*(set(select_references(index, e, s)) for e in rows)), {1, 2, 3})
        self.assertEqual(min(e['core'][0][0] for e in rows), -1024)
        self.assertEqual(max(e['core'][1][0] for e in rows), 1024)
        baseline = regions(dict(s, reference_margin=0))
        self.assertEqual([e['core'] for e in rows], [e['core'] for e in baseline])
        self.assertEqual(audit_coverage(index, baseline, dict(s, reference_margin=0))['covered_references'], 1)
        with self.assertRaisesRegex(ValueError, 'apron must fit'):
            regions(dict(s, reference_margin=897))

    def test_heightless_apron_does_not_admit_a_missing_owned_land_cell(self):
        s = R.frame_settings(R.frame_row((0, 0)))
        area = {'center': [0, 0], 'radius_cells': 1,
                'cells': [{'x': 0, 'y': 0}, {'x': 0, 'y': 1}],
                'default_land_cells': [[0, 1]]}
        R.check_source_land(s, {'area': area})
        area['default_land_cells'].append([0, 0])
        with self.assertRaisesRegex(ValueError, 'owned cell has no original LAND'):
            R.check_source_land(s, {'area': area})
        ocean = R.frame_settings(dict(R.frame_row((0, 0)), kind='ocean'))
        R.check_source_land(ocean, {'area': area})
        area['center'] = [1, 1]
        with self.assertRaisesRegex(ValueError, 'different owned cell or scope'):
            R.check_source_land(ocean, {'area': area})

    def test_neighboring_static_footprint_survives_source_and_frame_selection(self):
        # Empty cell next to a town: the neighbor owns the rock, while this
        # frame needs its overhang and a second object just past the core.
        import import_town
        from town_grid import audit_radius, reference_ownership
        from town_regions import town_references
        s = R.frame_settings(R.frame_row((0, 0)))
        audit_radius(s)
        self.assertGreaterEqual(s['source_radius'], 1)
        self.assertEqual(s['owned_cells'], [[0, 0], [1, 1]])
        def ref(n, x, lo, hi):
            return {'number': n, 'position': [x, 4096, 0], 'cell': [1, 0],
                    'bounds': [[lo, 4000, -32], [hi, 4200, 32]]}
        refs = [ref(1, 8256, 8000, 8512), ref(2, 8448, 8400, 8512),
                ref(3, 12288, 12200, 12400)]
        self.assertTrue(import_town.footprint_in_frame(refs[0], s))
        self.assertTrue(import_town.footprint_in_frame(refs[1], s))
        self.assertFalse(import_town.footprint_in_frame(refs[2], s))
        self.assertEqual(town_references({'references': refs}, s), [1, 2])
        own = reference_ownership(refs[:2], s)
        self.assertEqual(own['owned_references'], [])
        self.assertEqual([x['reference'] for x in own['dependency_references']], [1, 2])
        self.assertGreaterEqual(s['reference_margin'], s['draw_distance'] + R.LEAVE_MARGIN)
        self.assertEqual(s['handoff_core'], [[-1024, -1024], [1024, 1024]])

    def test_margin_rule_and_sectors(self):
        import town_config
        frame = R.frame_row((-7, 2))
        settings = R.frame_settings(frame)
        town_config.validate_town(settings['town'], settings)
        low, high = town_config.frame_ground_bounds(settings)
        self.assertEqual((low, high), ([-1920, -1920], [1920, 1920]))         # the legacy map's own coverage
        self.assertEqual(town_config.handoff_core(settings), [[-1024, -1024], [1024, 1024]])
        chunks = (high[0] - low[0]) // 256
        self.assertEqual(chunks % 3, 0)                                        # the world's sector size divides it
        self.assertGreaterEqual(R.TERRAIN_MARGIN, settings['draw_distance'] + 32)

    def test_adjacent_frames_share_margins_not_owned_boxes(self):
        import town_config
        from chim.areas import area_problems
        from chim.world import frame_box
        ids = town_config.register_generated([R.frame_settings(R.frame_row(c)) for c in ((-7, 2), (-6, 2))])
        self.assertEqual(area_problems(ids), [])
        a, b = (R.frame_row(c) for c in ((-7, 2), (-6, 2)))

        def frame(row):
            s = R.frame_settings(row)
            low, high = town_config.frame_ground_bounds(s)
            return {'centre': s['centre'], 'low': low, 'span': (high[0] - low[0], high[1] - low[1]),
                    'owned': s['bounds']}
        fa, fb = frame(a), frame(b)
        ga = frame_box({k: v for k, v in fa.items() if k != 'owned'})
        gb = frame_box({k: v for k, v in fb.items() if k != 'owned'})
        self.assertTrue(ga[0] < gb[2] and gb[0] < ga[2])                    # the ground margins overlap
        oa, ob = frame_box(fa), frame_box(fb)
        self.assertEqual(oa[2], ob[0])                                         # the owned boxes only touch


def awr(rows):
    """world/regions.awr (AWR2) of [(origin, core, cover)]."""
    out = bytearray(b'AWR2' + struct.pack('<I', len(rows)) + bytes(56))
    for i, (origin, core, cover) in enumerate(rows):
        out += ('vf%04d' % i).encode() + b'\0\0' + struct.pack('<11f', *origin, *core, *cover)
    return bytes(out)


class InPlace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.id1 = Path(self.tmp.name) / 'id1'
        (self.id1 / 'maps').mkdir(parents=True)
        (self.id1 / 'world').mkdir()
        self.frame = R.frame_row((-7, 2))
        origin = list(self.frame['origin'][:2]) + [-384.0]
        (self.id1 / 'world/regions.awr').write_bytes(awr([
            (origin, (-1024, -1024, 1024, 1024), (-1920, -1920, 1920, 1920))]))

    def tearDown(self):
        self.tmp.cleanup()

    def legacy_map(self, extra=()):
        from chim import frame_map as FM
        from chim import format as F
        rows = [{'classname': 'worldspawn', 'message': 'Vvardenfell', 'aw_hull': 'tes3-humanoid-v1'},
                {'classname': 'info_player_start', 'origin': '0 0 400', 'angle': '0'},
                {'classname': 'aw_flora', 'origin': '10 20 400', 'model': 'progs/f.spr', 'aw_ref': '77'},
                {'classname': 'aw_flora', 'origin': '1500 20 400', 'model': 'progs/f.spr', 'aw_ref': '78'},
                {'classname': 'func_wall', 'model': '*1', 'origin': '5 5 0', 'aw_ref': '42'}] + list(extra)
        lumps = FM.empty_world((-1920, -1920, -100), (1920, 1920, 900))
        lumps[0] = FM.entity_text(rows)
        (self.id1 / 'maps/vf0000.bsp').write_bytes(F.brush_image(lumps)[0])
        (self.id1 / 'harvest-vf0000.txt').write_text('AWH4 0\n', encoding='ascii')

    def patch(self, placed):
        from unittest import mock
        from chim import frame_map as FM
        return [mock.patch.object(FM, 'chim_placements', lambda world_dir, cell=None, world=None: placed),
                mock.patch.object(FM, 'frame_bounds', lambda world, cell=None: (cell, (-1920, -1920, -200),
                                                                               (1920, 1920, 900))),
                mock.patch.object(FM, 'activated_entities', lambda id1, names: ([], [])),
                mock.patch.object(FM, 'stream_enabled', lambda: False)]

    def test_replaces_the_map_in_place(self):
        from chim import frame_map as FM
        self.legacy_map()
        patches = self.patch({42: (5.0, 5.0, -384.0)})
        for p in patches:
            p.start()
        try:
            record = FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world')
        finally:
            for p in patches:
                p.stop()
        # the frame map keeps the cell's map name with the frame-map extension (tools/map_files.py)
        self.assertEqual(record['map'], 'maps/vf0000.chim')
        self.assertFalse((self.id1 / 'maps/vf0000.bsp').exists())
        self.assertEqual([r['file'] for r in record['replaced']], ['maps/vf0000.bsp', 'harvest-vf0000.txt'])
        self.assertFalse((self.id1 / 'harvest-vf0000.txt').exists())
        rows = FM.entities((self.id1 / 'maps/vf0000.chim').read_bytes())
        self.assertEqual(rows[0][FM.FRAME_KEY], '-7 2')
        self.assertEqual(rows[0]['message'], 'Vvardenfell')
        flora = [r for r in rows if r['classname'] == 'aw_flora']
        self.assertEqual([r['origin'] for r in flora], ['10 20 16'])             # z moved by the old origin; the
        self.assertEqual(record['statics'], {'legacy': 1, 'in_chim': 1, 'missing': 0})   # coverage copy left out
        self.assertEqual(FM.world_directory(self.id1)[0][1][2], 0.0)            # the row's origin z is now 0
        self.assertEqual(record['legacy_origin_z'], -384.0)

    def test_the_harvest_steps_frame_catalogue_stays(self):
        # HARVEST-CHIM-REGION-LOSS-41: the catalogue the harvest step wrote for the frame map (frame origin,
        # AWH4 proxies) stays with it; the CHIM world leaves these plants out, so removing it lost them.
        import hashlib
        from chim import frame_map as FM
        self.legacy_map()
        sha = hashlib.sha256((self.id1 / 'harvest-vf0000.txt').read_bytes()).hexdigest()
        patches = self.patch({42: (5.0, 5.0, -384.0)})
        for p in patches:
            p.start()
        try:
            record = FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world',
                                     keep_catalogues={'vf0000': sha})
        finally:
            for p in patches:
                p.stop()
        self.assertEqual([r['file'] for r in record['replaced']], ['maps/vf0000.bsp'])
        self.assertEqual(record['harvest_catalogue'], {'file': 'harvest-vf0000.txt', 'bytes': 7, 'sha256': sha})
        self.assertTrue((self.id1 / 'harvest-vf0000.txt').is_file())

    def test_a_changed_frame_catalogue_is_refused(self):
        from chim import frame_map as FM
        self.legacy_map()
        patches = self.patch({42: (5.0, 5.0, -384.0)})
        for p in patches:
            p.start()
        try:
            with self.assertRaisesRegex(ValueError, 'vf0000 .*harvest catalogue the harvest step wrote for it'):
                FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world',
                                keep_catalogues={'vf0000': '0' * 64})
        finally:
            for p in patches:
                p.stop()

    def test_the_earlier_form_replaces_the_bsp_under_its_own_name(self):
        # --chim-frame-ext bsp (DON'T DELETE ANY METHOD): the frame map takes maps/vf0000.bsp itself
        from unittest import mock
        from chim import frame_map as FM
        from map_files import FRAME_EXT_VARIABLE, is_chim_frame
        self.legacy_map()
        patches = self.patch({42: (5.0, 5.0, -384.0)}) + [mock.patch.dict('os.environ', {FRAME_EXT_VARIABLE: 'bsp'})]
        for p in patches:
            p.start()
        try:
            record = FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world')
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(record['map'], 'maps/vf0000.bsp')
        self.assertFalse((self.id1 / 'maps/vf0000.chim').exists())
        self.assertTrue(is_chim_frame(self.id1 / 'maps/vf0000.bsp'))

    def test_refuses_what_it_cannot_carry(self):
        from chim import frame_map as FM
        self.legacy_map([{'classname': 'trigger_once', 'model': '*2', 'origin': '0 0 0'}])
        patches = self.patch({})
        for p in patches:
            p.start()
        try:
            with self.assertRaisesRegex(ValueError, 'not CHIM placements|cannot be carried'):
                FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world')
        finally:
            for p in patches:
                p.stop()
        self.assertTrue((self.id1 / 'harvest-vf0000.txt').exists())             # nothing written on refusal

    def test_refuses_a_divided_cell(self):
        from chim import frame_map as FM
        origin = list(self.frame['origin'][:2]) + [0.0]
        (self.id1 / 'world/regions.awr').write_bytes(awr([
            ([origin[0] - 512, origin[1], 0.0], (-512, -1024, 512, 1024), (-1408, -1920, 1408, 1920)),
            ([origin[0] + 512, origin[1], 0.0], (-512, -1024, 512, 1024), (-1408, -1920, 1408, 1920))]))
        with self.assertRaisesRegex(ValueError, 'is 2 open-world maps'):
            FM.build_region(self.id1, self.frame, Path(self.tmp.name) / 'world')


class ManyRegions(unittest.TestCase):
    """build_regions (BUILD-IMAGE-CHIM-MAPS-SERIAL-36): the region frame maps made on the shared worker pool
    and written in table order give the same image, by SHA-256 of every file, with one worker or several, and
    with or without the pass cache; an unchanged map is taken from the cache, a changed legacy map is made again."""
    CELLS = [(-7, 2), (-6, 2), (-5, 2)]

    def stage(self, root):
        from chim import frame_map as FM
        from chim import format as F
        id1 = Path(root) / 'id1'
        (id1 / 'maps').mkdir(parents=True)
        (id1 / 'world').mkdir()
        frames = [R.frame_row(c) for c in self.CELLS]
        (id1 / 'world/regions.awr').write_bytes(awr([
            (list(f['origin'][:2]) + [-384.0 + 8 * i], (-1024, -1024, 1024, 1024), (-1920, -1920, 1920, 1920))
            for i, f in enumerate(frames)]))
        for i in range(len(frames)):
            rows = [{'classname': 'worldspawn', 'message': 'Vvardenfell'},
                    {'classname': 'info_player_start', 'origin': '0 0 400', 'angle': '0'},
                    {'classname': 'aw_flora', 'origin': '%d 20 400' % (10 + i), 'model': 'progs/f.spr', 'aw_ref': '77'},
                    {'classname': 'func_wall', 'model': '*1', 'origin': '5 5 0', 'aw_ref': '42'}]
            lumps = FM.empty_world((-1920, -1920, -100), (1920, 1920, 900))
            lumps[0] = FM.entity_text(rows)
            (id1 / ('maps/vf%04d.bsp' % i)).write_bytes(F.brush_image(lumps)[0])
        (id1 / 'harvest-vf0001.txt').write_text('AWH4 0\n', encoding='ascii')
        return id1, frames

    def run_regions(self, jobs, cache=None, change=False):
        from unittest import mock
        from chim import frame_map as FM
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            id1, frames = self.stage(tmp)
            if change:
                raw = bytearray((id1 / 'maps/vf0002.bsp').read_bytes())
                (id1 / 'maps/vf0002.bsp').write_bytes(bytes(raw).replace(b'"12 20 400"', b'"13 20 400"'))
            patches = [mock.patch.object(FM, 'chim_placements', lambda world_dir, cell=None, world=None: {42: None}),
                       mock.patch.object(FM, 'frame_bounds', lambda world_dir, cell=None: (cell, (-1920, -1920, -200),
                                                                                         (1920, 1920, 900))),
                       mock.patch.object(FM, 'stream_enabled', lambda: False)]
            for p in patches:
                p.start()
            try:
                seen = []
                records, reused = FM.build_regions(id1, frames, Path(tmp) / 'world', jobs=jobs, cache=cache,
                                                   progress=lambda record, hit: seen.append((record['map'], hit)))
            finally:
                for p in patches:
                    p.stop()
            files = {p.relative_to(id1).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(id1.rglob('*')) if p.is_file()}
            return files, records, reused, seen

    def test_one_worker_or_several_same_bytes(self):
        one, records, reused, seen = self.run_regions(1)
        many, records2, _, _ = self.run_regions(3)
        self.assertEqual(one, many)
        self.assertEqual(records, records2)
        self.assertEqual(reused, 0)
        self.assertEqual([m for m, _ in seen], ['maps/vf0000.chim', 'maps/vf0001.chim', 'maps/vf0002.chim'])
        self.assertNotIn('harvest-vf0001.txt', one)
        self.assertEqual([r['file'] for r in records[1]['replaced']], ['maps/vf0001.bsp', 'harvest-vf0001.txt'])

    def test_pass_cache_reuses_unchanged_maps_only(self):
        from pass_cache import PassCache
        with tempfile.TemporaryDirectory() as store:
            cache = PassCache('chim-region-frame', {}, 'sources', root=store)
            plain, plain_records, _, _ = self.run_regions(2)
            first, records, reused, _ = self.run_regions(2, cache=cache)
            self.assertEqual((first, records, reused), (plain, plain_records, 0))
            again, records2, reused2, seen = self.run_regions(2, cache=cache)
            self.assertEqual((again, records2, reused2), (plain, plain_records, 3))
            self.assertTrue(all(hit for _, hit in seen))
            changed, _, reused3, seen3 = self.run_regions(2, cache=cache, change=True)
            self.assertEqual(reused3, 2)
            self.assertEqual([hit for _, hit in seen3], [True, True, False])
            self.assertNotEqual(changed['maps/vf0002.chim'], plain['maps/vf0002.chim'])
            other = PassCache('chim-region-frame', {}, 'other sources', root=store)   # the pass's own code changed
            _, _, reused4, _ = self.run_regions(2, cache=other)
            self.assertEqual(reused4, 0)


class GameDataRows(unittest.TestCase):
    """Region frame maps from the game data (docs/BUILD_MANIFEST.md step 2, --chim-region-rows game-data): the
    open-world worldspawn and the start on the frame's own ground, no legacy map read. A/B with the legacy method:
    on legacy maps that carry what the image passes leave (that worldspawn, the start on the ground), both methods
    give the same bytes; with no legacy map at all the game-data method still writes every frame map."""
    CELLS = [(-7, 2), (-6, 2), (-5, 2)]
    FIELDS = {'aw_hand_idle': '2.5', 'aw_hand_draw': '0.5', 'aw_hand_lower': '0.25', 'aw_hand_punch': '1.0',
              'aw_eye_height': '16.4'}
    GROUND = -512.0

    def world(self, frames):
        from chim.terrain import TERRAIN_CEILING
        self.hi_z = float(TERRAIN_CEILING)
        return {'frames': [('f%d' % i, {'cell': list(f['cell']), 'grain': 256, 'low': [-1920, -1920], 'nx': 15,
                                        'ny': 15}, [{'cx': 0, 'cy': 0, 'index': 0, 'zmin': 56.0}])
                           for i, f in enumerate(frames)], 'models': []}

    def run(self, rows, jobs=1, legacy=True):
        from unittest import mock
        from chim import frame_map as FM
        from chim import format as F
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'world').mkdir()
            frames = [R.frame_row(c) for c in self.CELLS]
            origins = [-384.0 + 8 * i for i in range(len(frames))]
            (id1 / 'world/regions.awr').write_bytes(awr([
                (list(f['origin'][:2]) + [z], (-1024, -1024, 1024, 1024), (-1920, -1920, 1920, 1920))
                for f, z in zip(frames, origins)]))
            world = self.world(frames)
            if legacy:
                for i, (frame, z) in enumerate(zip(frames, origins)):
                    start = self.GROUND + FM.START_HEIGHT - frame['origin'][2] - z
                    lumps = FM.empty_world((-1920, -1920, -100), (1920, 1920, 900))
                    lumps[0] = FM.entity_text([FM.open_world_worldspawn(self.FIELDS),
                                               {'angle': '90', 'classname': 'info_player_start',
                                                'origin': '0 0 %g' % start}])
                    (id1 / ('maps/vf%04d.bsp' % i)).write_bytes(F.brush_image(lumps)[0])
            patches = [mock.patch.object(FM, 'chim_placements', lambda world_dir, cell=None, world=None: {}),
                       mock.patch.object(FM, 'frame_bounds', lambda world_dir, cell=None: (
                           cell, (-1920, -1920, 56.0 - FM.FLOOR_MARGIN), (1920, 1920, self.hi_z))),
                       mock.patch.object(FM, 'frame_ground', lambda world, cell, *a, **k: self.GROUND),
                       mock.patch.object(FM, 'stream_enabled', lambda: False)]
            for p in patches:
                p.start()
            try:
                if rows == 'legacy':
                    records, _ = FM.build_regions(id1, frames, Path(tmp) / 'world', jobs=jobs, rows='legacy')
                else:
                    records, _ = FM.build_regions(id1, frames, Path(tmp) / 'world', world=world, jobs=jobs,
                                                  rows='game-data', hand_fields=self.FIELDS)
            finally:
                for p in patches:
                    p.stop()
            maps = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((id1 / 'maps').iterdir())}
            return maps, records

    def test_game_data_and_legacy_give_the_same_bytes(self):
        legacy, _ = self.run('legacy')
        game, records = self.run('game-data')
        self.assertEqual(legacy, game)
        self.assertEqual(sorted(game), ['vf0000.chim', 'vf0001.chim', 'vf0002.chim'])
        self.assertEqual([r['replaced'][0]['reason'] for r in records],
                         ['legacy map of a CHIM region cell (the frame map is made from the game data)'] * 3)

    def test_no_legacy_map_needed(self):
        with_maps, _ = self.run('game-data')
        without, records = self.run('game-data', jobs=3, legacy=False)
        self.assertEqual(with_maps, without)                 # one worker or three, legacy map present or not
        self.assertEqual([r['replaced'] for r in records], [[], [], []])

    def test_default_without_hand_fields_is_the_legacy_method(self):
        from chim import frame_map as FM
        self.assertEqual(FM.region_rows_mode(), 'game-data')
        self.assertEqual(FM.region_rows_mode('legacy'), 'legacy')
        with self.assertRaises(ValueError):
            FM.region_rows_mode('other')


class DividedCells(unittest.TestCase):
    """CHIM-REGION-DIVIDED-CELLS-36: a cell whose legacy open world is 2 x 2 (or 4 x 4) maps goes on CHIM as ONE
    frame. The legacy layout's map cores never cross a cell border, so no legacy map of another cell holds any of
    the CHIM cell's own ground (only its 896-unit apron reaches in, as for one-map cells); the world terrain stage
    makes none of the cell's maps and widens the first map's directory row to the whole cell, the others become
    aliases; the engine's lookup (the first row whose core holds a point) then finds the frame map's name
    everywhere in the cell and the neighbours' names outside it; the image installs one frame map."""
    CHIM = (-7, 2)
    LAYOUT = {(-8, 2): 1, (-7, 2): 2, (-6, 2): 1, (-7, 3): 2, (-7, 1): 1}   # cell: divisions

    def entries(self):
        from prepare_world_regions import plan, layout_refinements
        cells = [dict(cell=list(c), screen=dict(candidate=n), unresolved_placements=0, name='', region='Test')
                 for c, n in sorted(self.LAYOUT.items())]
        report = dict(format='AmiWind world survey 1', terrain=dict(height_seams=[]),
                      settings=dict(overlap_runtime=896,
                                    source_triangle_limit=layout_refinements()['survey_source_triangle_limit']),
                      cells=cells)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'world-survey.json').write_text(json.dumps(report), encoding='utf-8')
            _, entries = plan(Path(tmp))
        for e in entries:
            e['origin'][2] = -128.0 - int(e['name'][2:])       # as map_text sets it (any value per map)
        return entries

    def directory(self, entries):
        """The terrain stage's rows for CHIM cell CHIM (prepare_world_regions.prepare, without compiling)."""
        from prepare_world_regions import chim_region, merge_chim_rows
        cells = {self.CHIM}
        skipped = [dict(e, converted=None, chim_region=True) for e in entries if chim_region(e, cells)]
        rows = {e['name']: e for e in entries}
        for r in merge_chim_rows(skipped):
            rows[r['name']] = r
        return [rows[e['name']] for e in entries], [e for e in entries if not chim_region(e, cells)]

    @staticmethod
    def destination(rows, gx, gy):
        """aw_world.c AW_WorldDestination / AW_WorldMapTarget: the first row whose core holds the point."""
        for r in rows:
            (x0, y0), (x1, y1) = r['core']
            if x0 <= gx - r['origin'][0] < x1 and y0 <= gy - r['origin'][1] < y1:
                return r['name']
        return None

    def test_no_legacy_map_of_the_cell_and_no_other_map_owns_its_ground(self):
        entries = self.entries()
        mine = [e for e in entries if tuple(e['cell']) == self.CHIM]
        self.assertEqual(len(mine), 4)
        rows, compiled = self.directory(entries)
        self.assertFalse({e['name'] for e in compiled} & {e['name'] for e in mine})   # none of them is made
        x0, y0 = self.CHIM[0] * 2048, self.CHIM[1] * 2048
        for e in compiled:                      # every legacy map that is made: its core stays out of the cell
            (a0, b0), (a1, b1) = e['core']
            ox, oy = e['origin'][0], e['origin'][1]
            self.assertFalse(a0 + ox < x0 + 2048 and x0 < a1 + ox and b0 + oy < y0 + 2048 and y0 < b1 + oy, e['name'])

    def test_one_row_owns_the_cell_and_the_engine_finds_it(self):
        entries = self.entries()
        rows, _ = self.directory(entries)
        mine = sorted((r for r in rows if tuple(r['cell']) == self.CHIM), key=lambda r: r['name'])
        owner, aliases = mine[0], mine[1:]
        self.assertEqual(owner['core'], [[-1024, -1024], [1024, 1024]])
        self.assertEqual(owner['origin'][:2], [self.CHIM[0] * 2048 + 1024, self.CHIM[1] * 2048 + 1024])
        self.assertEqual(owner['chim_region_maps'], [r['name'] for r in mine])
        for a in aliases:
            self.assertEqual((a['origin'], a['core'], a['coverage']), (owner['origin'], owner['core'], owner['coverage']))
            self.assertEqual(a['chim_region_alias'], owner['name'])
        for r in rows:                          # the engine's row checks (aw_world.c load_directory)
            for k in range(2):
                self.assertLess(r['core'][0][k], r['core'][1][k])
                self.assertLessEqual(r['coverage'][0][k], r['core'][0][k] - 896)
                self.assertGreaterEqual(r['coverage'][1][k], r['core'][1][k] + 896)
        neighbour = {tuple(e['cell']): [e['name'] for e in entries if e['cell'] == list(c)]
                     for c in self.LAYOUT for e in entries if e['cell'] == list(c)}
        for i in range(0, 2048, 64):
            for j in range(0, 2048, 64):
                gx, gy = self.CHIM[0] * 2048 + i + 0.5, self.CHIM[1] * 2048 + j + 0.5
                self.assertEqual(self.destination(rows, gx, gy), owner['name'])
                for dx, dy in ((-2048, 0), (2048, 0), (0, 2048), (0, -2048)):
                    cell = (self.CHIM[0] + dx // 2048, self.CHIM[1] + dy // 2048)
                    self.assertIn(self.destination(rows, gx + dx, gy + dy), neighbour[cell])

    def test_rows_that_do_not_tile_the_cell_are_refused(self):
        from prepare_world_regions import merge_chim_rows
        rows, _ = self.directory(self.entries())
        mine = [dict(e) for e in self.entries() if tuple(e['cell']) == self.CHIM]
        with self.assertRaisesRegex(ValueError, 'do not tile the cell'):
            merge_chim_rows(mine[:3])
        with self.assertRaisesRegex(ValueError, 'more than one cell'):
            merge_chim_rows(mine[:1] + [e for e in self.entries() if tuple(e['cell']) == (-8, 2)])

    def build(self, merged=True, rows='game-data'):
        """(records, map files, directory) of build_regions over a directory whose cell CHIM is 4 maps."""
        from unittest import mock
        from chim import frame_map as FM
        entries = self.entries()
        directory, _ = self.directory(entries) if merged else (entries, None)
        frame = R.frame_row(self.CHIM)
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'world').mkdir()
            (id1 / 'world/regions.awr').write_bytes(awr([
                ([r['origin'][0] * 1.0, r['origin'][1] * 1.0, r['origin'][2]],
                 (r['core'][0][0], r['core'][0][1], r['core'][1][0], r['core'][1][1]),
                 (r['coverage'][0][0], r['coverage'][0][1], r['coverage'][1][0], r['coverage'][1][1]))
                for r in directory]))
            (id1 / 'harvest-vf0005.txt').write_text('AWH4 0\n', encoding='ascii')
            world = {'frames': [('f0', {'cell': list(self.CHIM), 'grain': 256, 'low': [-1920, -1920], 'nx': 15,
                                        'ny': 15}, [{'cx': 0, 'cy': 0, 'index': 0, 'zmin': 56.0}])], 'models': []}
            patches = [mock.patch.object(FM, 'chim_placements', lambda world_dir, cell=None, world=None: {}),
                       mock.patch.object(FM, 'frame_ground', lambda world, cell, *a, **k: -512.0),
                       mock.patch.object(FM, 'stream_enabled', lambda: False)]
            for p in patches:
                p.start()
            try:
                records, _ = FM.build_regions(id1, [frame], Path(tmp) / 'world', world=world, rows=rows,
                                              hand_fields=GameDataRows.FIELDS)
            finally:
                for p in patches:
                    p.stop()
            names = sorted(p.name for p in (id1 / 'maps').iterdir())
            table = Path(tmp) / 'world'
            table.mkdir()
            (table / R.TABLE_FILE).write_text(R.dumps(R.ownership({self.CHIM: 'land'})), encoding='utf-8')
            owned = (FM.region_map_names(id1, table), FM.region_map_names(id1, table, primary_only=True))
            return records, names, FM.world_directory(id1), owned, sorted(p.name for p in id1.iterdir())

    def test_the_image_installs_one_frame_map_for_the_cell(self):
        records, names, directory, (owned, primary), files = self.build()
        mine = sorted(e['name'] for e in self.entries() if tuple(e['cell']) == self.CHIM)
        self.assertEqual(len(mine), 4)
        self.assertEqual(names, [mine[0] + '.chim'])                     # one frame map, under the first name
        self.assertEqual(records[0]['aliases'], mine[1:])
        self.assertEqual(sorted(owned), mine)                             # every row of the cell is owned
        self.assertEqual(sorted(primary), mine[:1])                       # counted once
        for name, origin, core in directory:
            if name in mine:
                self.assertEqual(origin[2], 0.0)                         # every row of the cell: the frame's z
                self.assertEqual(core, (-1024.0, -1024.0, 1024.0, 1024.0))
        self.assertNotIn('harvest-vf0005.txt', files)                    # an alias's catalogue left, recorded
        self.assertIn('harvest-vf0005.txt', [r['file'] for r in records[0]['replaced']])

    def test_alias_rows_are_found_from_the_directory_bytes(self):
        # the save fingerprint binds every row's map except an alias's (first build: FileNotFoundError vf0227)
        from chim import frame_map as FM
        rows, _ = self.directory(self.entries())
        raw = awr([([r['origin'][0] * 1.0, r['origin'][1] * 1.0, r['origin'][2]],
                    (r['core'][0][0], r['core'][0][1], r['core'][1][0], r['core'][1][1]),
                    (r['coverage'][0][0], r['coverage'][0][1], r['coverage'][1][0], r['coverage'][1][1]))
                   for r in rows])
        mine = sorted(e['name'] for e in self.entries() if tuple(e['cell']) == self.CHIM)
        self.assertEqual(FM.alias_rows(raw), {n: mine[0] for n in mine[1:]})
        import inspect
        import build_aga
        self.assertIn('alias_rows(raw)', inspect.getsource(build_aga.write_content_fingerprint))
        import world_volumes          # second build: the volume packer stopped on the same alias row
        self.assertIn('alias_rows(raw)', inspect.getsource(world_volumes.pack))

    def test_unwidened_rows_and_the_earlier_method_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'do not each cover the cell'):
            self.build(merged=False)
        with self.assertRaisesRegex(ValueError, 'earlier region method'):
            self.build(rows='legacy')


class Rebind(unittest.TestCase):
    def rebind(self, frame_name):
        '''The optimizer receipt after a region frame replaced vf0001.bsp as FRAME_NAME (vf0001.chim, or
        vf0001.bsp with chim_frame_ext bsp); a frame map is told by its key, not its name.'''
        import optimize_world_maps as O
        from chim_fixture import frame_header_bytes
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp) / 'maps'
            maps.mkdir()
            for name in ('vf0000.bsp', 'vf0001.bsp'):
                (maps / name).write_bytes(b'x' * 200)
            report = {'maps': [{'map': n, 'input_sha256': 'a', 'output_sha256': 'b', 'input_bytes': 1,
                                'output_bytes': 1, 'file_bytes_saved': 0, 'changed': False}
                               for n in ('vf0000.bsp', 'vf0001.bsp')], 'committed_maps': []}
            from unittest import mock
            with mock.patch.object(O, 'verify_optimized_maps', lambda *a, **k: None), \
                    mock.patch.object(O, 'write_report', lambda *a, **k: None):
                if frame_name != 'vf0001.bsp':
                    with self.assertRaises(ValueError):                          # the frame map is not there yet
                        O.rebind_chim_maps(maps, json.loads(json.dumps(report)), Path(tmp) / 'r.json',
                                           ['maps/vf0001.bsp'], replaced=[frame_name])
                (maps / 'vf0001.bsp').unlink()
                (maps / frame_name).write_bytes(frame_header_bytes((-7, 2)))
                out = O.rebind_chim_maps(maps, json.loads(json.dumps(report)), Path(tmp) / 'r.json',
                                         ['maps/vf0001.bsp'], replaced=[frame_name])
                row = next(r for r in out['maps'] if r['map'] == frame_name)
                self.assertEqual(row['not_optimized'], 'CHIM region frame map')
                self.assertEqual(out['chim_rebind']['replaced_by_region_frames'], [frame_name])
                self.assertEqual([r['map'] for r in out['maps']], sorted(['vf0000.bsp', frame_name]))
                (maps / frame_name).write_bytes(b'x' * 200)                      # not a frame map (no key)
                with self.assertRaises(ValueError):
                    O.rebind_chim_maps(maps, json.loads(json.dumps(report)), Path(tmp) / 'r.json',
                                       ['maps/vf0001.bsp'], replaced=[frame_name])

    def test_replaced_maps_rejoin_as_frame_maps(self):
        self.rebind('vf0001.chim')

    def test_replaced_maps_rejoin_as_frame_maps_under_the_legacy_name(self):
        self.rebind('vf0001.bsp')


class Builder(unittest.TestCase):
    def test_off_by_default(self):
        import build
        args = build.parser().parse_args(['--dry-run'])
        self.assertEqual(args.chim_regions, [])
        self.assertIsNone(build.resolve_chim_regions(args))
        self.assertNotIn('--chim-regions-cells', build.chim_stage_options(args))

    def test_needs_chim_builder_and_status(self):
        import build
        args = SimpleNamespace(chim_regions=['seabed'], chim_regions_status=None, miniwind=False)
        with self.assertRaisesRegex(ValueError, 'CHIM builder'):
            build.resolve_chim_regions(args, {'builder': 'legacy', 'chim_areas': []})
        with self.assertRaisesRegex(ValueError, 'chim-regions-status'):
            build.resolve_chim_regions(args, {'builder': 'chim', 'chim_areas': []})

    def test_cells_reach_the_chim_stage(self):
        import build
        with tempfile.TemporaryDirectory() as tmp:
            status = Path(tmp) / 'cell-progress.json'
            status.write_text(json.dumps(tracker({(5, 5): ('empty_sea', 0, 'Bitter Coast Region'),
                                                  (6, 5): (DONE, 1, 'Bitter Coast Region')})), encoding='utf-8')
            args = SimpleNamespace(chim_regions=['sea-ring'], chim_regions_status=status, miniwind=False)
            record = build.resolve_chim_regions(args, {'builder': 'chim', 'chim_areas': []})
            self.assertEqual(record['counts']['cells'], 2)
            self.assertEqual(args.chim_regions_cells, '5,5:s 6,5:l')
            options = build.chim_stage_options(args)
            self.assertEqual(options[-2:], ['--chim-regions-cells', '5,5:s 6,5:l'])



class StaleAuditRefusal(unittest.TestCase):
    """CHIMPORT-STATUS-STALE-41: a cell refused on recorded audits names them, when and with what they were
    measured, and the one command that measures them again with the current builder."""

    def status(self, audited):
        return {(17, 4): {'status': 'converted_failing', 'failing': ['memory_fit'], 'audited': audited,
                          'name': 'Sadrith Mora', 'file_generated': '2026-10-15T17:59:12+00:00'}}

    def test_refusal_names_audits_time_versions_and_command(self):
        _, problems, _ = R.preflight([(17, 4)], {(17, 4)}, self.status(
            {'run': 'chimport-x', 'at': '2026-10-11T08:00:00+00:00', 'amiwind_version': '0.0.36',
             'chim_version': '0.2.0', 'converter_sha256': 'f' * 64}), {})
        self.assertIn('Sadrith Mora: CHIMport audits failing: memory_fit (measured 2026-10-11T08:00:00+00:00 by run '
                      'chimport-x with AmiWind 0.0.36, CHIM 0.2.0;', problems[0])
        self.assertIn('older converter', problems[0])
        self.assertIn('tools/chimport.py run --out RUN --cells "17,4"', problems[1])

    def test_unrecorded_time_falls_back_to_the_status_file_creation(self):
        _, problems, _ = R.preflight([(17, 4)], {(17, 4)}, self.status({}), {})
        self.assertIn('before 2026-10-15T17:59:12+00:00 (when the status file was created)', problems[0])
        self.assertIn('converter not recorded', problems[0])

    def test_same_converter_is_said_so(self):
        from chimport import code_identity
        self.assertEqual(R.converter_note(code_identity()), 'the same converter as this build')



class OceanLandPreflight(unittest.TestCase):
    """CHIMPORT-OCEAN-LAND-41: a cell taken as open ocean with a LAND record is refused in the preflight."""

    def test_ocean_cell_with_land_is_named(self):
        from unittest import mock
        with mock.patch('chim.ocean_runtime.land_cells', return_value={(5, 5)}):
            problems = R.ocean_land_problems({(5, 5): 'ocean', (6, 5): 'ocean', (7, 5): 'land'}, '/data')
        self.assertEqual(len(problems), 1)
        self.assertIn('1 cell(s) the status file calls open ocean have LAND', problems[0])
        self.assertIn('--cells "5,5"', problems[0])

    def test_no_ocean_cells_reads_nothing(self):
        self.assertEqual(R.ocean_land_problems({(1, 1): 'land'}, '/nowhere'), [])


if __name__ == '__main__':
    unittest.main()
