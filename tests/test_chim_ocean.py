# SPDX-License-Identifier: GPL-3.0-only
"""The shared ocean chunk (tools/chim/ocean.py) and CHIMport's open-sea cells (chimport.py ocean, K-OCEAN): one chunk
stored once and read back, seamless when tiled, refused by format 0.5 world readers; the open-sea plan over the island
rectangle and its margin; the seam check where real seabed meets the default floor; the 'ocean' cell status, the
tracker feed and the storage pool (stored once, linked after). Synthetic data only."""
import contextlib
import io
import json
import os
import struct
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
import storage_pool  # noqa: E402
from chim import format as F  # noqa: E402
from chim import ocean as O  # noqa: E402

LINKS = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0


def mip(name, w=16, h=16, value=5):
    levels = [bytes([value]) * ((w >> i) * (h >> i)) for i in range(4)]
    offsets = [40]
    for raw in levels[:-1]:
        offsets.append(offsets[-1] + len(raw))
    return struct.pack('<16s6I', name.encode(), w, h, *offsets) + b''.join(levels)


GROUND = {'g0': mip('g0'), '*water': mip('*water', value=9)}


def land(height=-2048.0):
    return [[float(height)] * 65 for _ in range(65)]


class Chunk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.info = O.build_ocean(GROUND)

    def test_the_chunk_reads_back_and_passes_every_check(self):
        fails, fig = O.validate_ocean(self.data)
        self.assertEqual(fails, [])
        self.assertEqual((fig['seabed'], fig['seabed_mw'], fig['water'], fig['grain']), (-512.0, -2048.0, 0.0, 256))
        self.assertEqual(fig['ground_area'], 256.0 * 256.0)
        self.assertEqual(fig['water_area'], 256.0 * 256.0)
        o = O.read_ocean(self.data)
        self.assertEqual(len(o['textures']), 2)
        self.assertEqual(o['chunk']['owned'], [])
        self.assertEqual(self.info['textures'], ['g0', '*water'])
        self.assertLess(self.info['hull_chain_max'], C.LEGACY_CHAIN_DEPTH)

    def test_the_default_floor_is_openmws_and_the_legacy_maps(self):
        from mwad.audit import DEFAULT_LAND_HEIGHT
        from import_town import TERRAIN_FLOOR
        self.assertEqual(O.DEFAULT_LAND_HEIGHT, DEFAULT_LAND_HEIGHT)
        self.assertEqual(O.DEFAULT_LAND_HEIGHT, -2048)
        self.assertEqual(O.FLOOR, TERRAIN_FLOOR)
        self.assertEqual(O.seabed_local(), -512.0)                  # the legacy region maps' -512 local units
        self.assertEqual((O.GRAIN, O.STEP), (C.FRAME_SETTINGS['grain'], C.cell_settings((0, 0))['terrain_step']))

    def test_a_format_05_world_reader_refuses_it_loudly(self):
        with self.assertRaises(ValueError):
            F.read_header(self.data)
        with self.assertRaises(ValueError):
            F.read_sector(self.data)

    def test_damage_is_found(self):
        bad = bytearray(self.data)
        bad[-1] ^= 0xFF
        fails, _ = O.validate_ocean(bytes(bad))
        self.assertTrue(fails)
        fails, _ = O.validate_ocean(self.data[:-4])
        self.assertTrue(fails)

    def test_the_chunk_is_byte_reproducible_and_keyed_by_its_inputs(self):
        again, _ = O.build_ocean(GROUND)
        self.assertEqual(again, self.data)
        task = O.ocean_task()
        key = O.ocean_key(task, GROUND)
        self.assertEqual(key, O.ocean_key(O.ocean_task(), dict(GROUND)))
        self.assertNotEqual(key, O.ocean_key(task, dict(GROUND, g0=mip('g0', value=6))))
        self.assertNotEqual(key, O.ocean_key(O.ocean_task(seabed=-500.0), GROUND))
        self.assertNotEqual(key, O.ocean_key(task, GROUND, bytes(768)))
        self.assertEqual(key, O.ocean_key(task, dict(GROUND, g7=mip('g7'))))    # a texture it never uses: same key

    def test_bad_tasks_are_refused(self):
        with self.assertRaises(ValueError):
            O.ocean_task(grain=200)
        with self.assertRaises(ValueError):
            O.ocean_task(seabed=10.0)
        with self.assertRaises(ValueError):
            O.build_ocean({'g0': GROUND['g0']})                    # no water texture


class Seam(unittest.TestCase):
    def test_a_default_floor_edge_has_no_step(self):
        s = O.seam_steps((0, 0), {(1, 0): land()})
        self.assertEqual([e['side'] for e in s['edges']], ['e'])
        self.assertEqual((s['max_step'], s['over']), (0.0, []))

    def test_each_side_reads_the_neighbours_facing_edge(self):
        for side, nb, mark in (('e', (1, 0), lambda h: [r.__setitem__(0, -1500.0) for r in h]),
                               ('w', (-1, 0), lambda h: [r.__setitem__(64, -1500.0) for r in h]),
                               ('n', (0, 1), lambda h: h.__setitem__(0, [-1500.0] * 65)),
                               ('s', (0, -1), lambda h: h.__setitem__(64, [-1500.0] * 65))):
            h = land()
            mark(h)
            s = O.seam_steps((0, 0), {nb: h})
            self.assertEqual(s['edges'][0]['side'], side)
            self.assertEqual(s['edges'][0]['max_step'], 548.0)
            self.assertEqual(s['over'], [side])
            far = land()
            mark(far)
            far[32][32] = -2048.0
            self.assertEqual(O.seam_steps((5, 5), {nb: h})['edges'], [])   # not a neighbour

    def test_a_step_within_one_height_unit_passes_and_corners_count(self):
        h = land(-2048 + O.SEAM_TOLERANCE)
        self.assertEqual(O.seam_steps((0, 0), {(0, 1): h})['over'], [])
        corner = land()
        corner[0][0] = -1000.0          # south-west corner of the north-east neighbour
        s = O.seam_steps((0, 0), {(1, 1): corner})
        self.assertEqual((s['edges'], s['max_step']), ([], 1048.0))
        self.assertEqual(s['over'], ['corner 1,1'])


class Plan(unittest.TestCase):
    def lands(self):
        return {(x, y): land() for x in range(3) for y in range(2)}

    def test_the_rectangle_and_its_margin_minus_land_records_and_plan(self):
        lands = self.lands()
        cells = {(1, 2): {'name': '', 'region': 'Sea', 'refs': 0}, (-1, 0): {'name': 'Wreck', 'region': '', 'refs': 3},
                 (9, 9): {'name': '', 'region': 'Far Sea', 'refs': 0}}
        doc = C.plan_ocean(lands, {(3, 1)}, cells, None, 1, planned={(2, 2)})
        self.assertEqual(doc['rect'], [0, 2, 0, 1])
        self.assertEqual(doc['map_cells'], 5 * 4)
        got = {(r['x'], r['y']) for r in doc['cells']}
        self.assertEqual(len(got), 20 - 6 - 1 - 1 - 1 + 1)  # land, other master's land, records, planned; + 9,9
        self.assertIn((9, 9), got)                          # a base-master cell record beyond the margin
        for c in [(3, 1), (-1, 0), (2, 2)] + list(lands):
            self.assertNotIn(c, got)
        self.assertEqual(doc['left_out'], {'land': 6, 'other_master_land': 1, 'records_without_land': 1, 'planned': 1})
        row = {(r['x'], r['y']): r for r in doc['cells']}[(1, 2)]
        self.assertEqual((row['region'], row['margin'], row['record']), ('Sea', True, True))
        self.assertEqual([e['side'] for e in row['seam']['edges']], ['s'])
        self.assertEqual(doc['counts']['inside_rect'], 0)
        self.assertEqual((doc['counts']['margin'], doc['counts']['beyond']), (11, 1))
        self.assertEqual({(r['x'], r['y']): r for r in doc['cells']}[(9, 9)]['where'], 'record')

    def test_a_named_rectangle_and_no_margin(self):
        doc = C.plan_ocean(self.lands(), (), {}, C.parse_rect('-1,3,0,1'), 0)
        self.assertEqual(sorted((r['x'], r['y']) for r in doc['cells']), [(-1, 0), (-1, 1), (3, 0), (3, 1)])
        self.assertTrue(all(not r['margin'] for r in doc['cells']))
        with self.assertRaises(ValueError):
            C.parse_rect('3,1,0,0')
        with self.assertRaises(ValueError):
            C.plan_ocean({}, (), {}, None, 1)


class Cells(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {k: v for k, v in os.environ.items() if k != storage_pool.ENV}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        for here, dirs, names in os.walk(self.root):
            for name in dirs + names:
                path = Path(here) / name
                if not path.is_symlink():
                    os.chmod(path, 0o755)
        self.temp.cleanup()

    def args(self, run, pool=None, **kw):
        palette = self.root / 'palette.lmp'
        if not palette.exists():
            palette.write_bytes(bytes(range(256)) * 3)
        a = dict(data_files=self.root, palette=palette, out=run, rect=None, margin=1, dry_run=False, tracker=None,
                 tracker_tool=None, tracker_ingest='', storage_pool='on' if pool else 'off', storage_pool_dir=pool,
                 reuse_mode='pool' if pool else 'copy', workspace=None)
        a.update(kw)
        return SimpleNamespace(**a)

    def run_ocean(self, args, lands):
        with patch.object(C, 'master_lands', return_value=(lands, set(), {}, 'sha')), \
                patch.object(C, 'ocean_ground_textures', return_value=dict(GROUND)), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            rc = C.ocean(args)
        return rc, out.getvalue()

    def test_open_sea_cells_are_references_with_their_own_status_and_feed_the_tracker(self):
        run = self.root / 'run'
        lands = {(0, 0): land(), (1, 0): land()}
        lands[(1, 0)][0] = [-1800.0] * 65              # south edge of 1,0 above the default floor: a seam step
        rc, out = self.run_ocean(self.args(run), lands)
        self.assertEqual(rc, 0, out)
        doc = json.loads((run / 'ocean' / 'plan.json').read_text())
        self.assertEqual(len(doc['cells']), 3 * 4 - 2)
        ref = json.loads((run / 'cells' / C.cell_dir((0, 1)) / 'ocean.json').read_text())
        self.assertEqual(ref['format'], O.REF_FORMAT)
        chunk = next((run / 'ocean').glob('ocean-*.cco'))
        self.assertEqual(ref['chunk']['bytes'], chunk.stat().st_size)
        res = json.loads((run / 'cells' / C.cell_dir((0, 1)) / 'result.json').read_text())
        self.assertEqual(res['status'], 'ocean')
        self.assertEqual(res['audits']['seam_tears']['status'], 'passed')
        stepped = json.loads((run / 'cells' / C.cell_dir((1, -1)) / 'result.json').read_text())
        self.assertEqual(stepped['status'], 'failed')                   # a real step is a seam failure, not hidden
        self.assertEqual(stepped['audits']['seam_tears']['numbers']['max_step'], 248.0)
        path = C.feed(run)
        fed = json.loads(path.read_text())
        cell = fed['cells']['0,1']
        self.assertTrue(cell['ocean'] and cell['eligible'])
        self.assertEqual(cell['status'], 'ocean')
        self.assertFalse(fed['cells']['1,-1'].get('ocean'))
        self.assertEqual(C.summarise(run)['total']['cells'], 0)          # the island plan is untouched

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_the_chunk_is_stored_once_in_the_pool_and_linked_after(self):
        pool = self.root / 'pool'
        lands = {(0, 0): land()}
        rc, _ = self.run_ocean(self.args(self.root / 'a', pool), lands)
        self.assertEqual(rc, 0)
        first = json.loads((self.root / 'a' / 'ocean' / 'summary.json').read_text())['pool']
        self.assertEqual((first['chunk'], first['stored_files']), ('computed', 1 + 8))
        rc, _ = self.run_ocean(self.args(self.root / 'b', pool), lands)
        second = json.loads((self.root / 'b' / 'ocean' / 'summary.json').read_text())['pool']
        self.assertEqual((second['chunk'], second['linked_files']), ('reused', 1))
        a = next((self.root / 'a' / 'ocean').glob('ocean-*.cco'))
        b = next((self.root / 'b' / 'ocean').glob('ocean-*.cco'))
        self.assertEqual(second['stored_bytes'], first['stored_bytes'] - a.stat().st_size)   # the references only
        self.assertEqual(os.stat(a).st_ino, os.stat(b).st_ino)           # one inode: stored once
        self.assertLess(second['stored_bytes'], a.stat().st_size)        # only the small references are new

    def test_a_second_writer_is_refused(self):
        run = self.root / 'run'
        with C.RunLock(run):
            rc, _ = self.run_ocean(self.args(run), {(0, 0): land()})
        self.assertEqual(rc, 3)

    def test_a_dry_run_writes_nothing(self):
        run = self.root / 'run'
        run.mkdir()
        rc, out = self.run_ocean(self.args(run, dry_run=True), {(0, 0): land()})
        self.assertEqual(rc, 0)
        self.assertIn('8 open-sea cells', out)
        self.assertEqual(list(run.iterdir()), [])

    def run_with_records(self, args, lands, holders, listed=frozenset()):
        with patch.object(C, 'ocean_record_masters', return_value=holders), \
                patch.object(C, 'ocean_base_world_cells', return_value=listed):
            return self.run_ocean(args, lands)

    def test_each_cells_set_comes_from_the_master_that_holds_its_record(self):
        """TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68: every open-sea cell was fed as Vvardenfell's, so a cell whose only
        record is in Bloodmoon.esm (Solstheim's open sea, -29,23 and -28,24) got Vvardenfell's island."""
        run = self.root / 'run'
        holders = {(0, 1): ('Bloodmoon.esm',), (1, 1): ('Morrowind.esm', 'Bloodmoon.esm'), (-1, 0): ('Bloodmoon.esm',)}
        rc, out = self.run_with_records(self.args(run), {(0, 0): land()}, holders, frozenset({(-1, 0)}))
        self.assertEqual(rc, 0, out)
        fed = json.loads(C.feed(run).read_text())['cells']
        self.assertEqual(fed['0,1']['set'], 'bloodmoon')         # a record in Bloodmoon.esm only: Solstheim's sea
        self.assertEqual(fed['1,1']['set'], 'vvardenfell')       # the base master holds it too: Vvardenfell's
        self.assertEqual(fed['-1,0']['set'], 'vvardenfell')      # a frame of the base world's cell list stays its own
        self.assertIn('set', fed['1,-1'])                        # no record in any master: no set hint, said so
        self.assertIsNone(fed['1,-1']['set'])
        res = json.loads((run / 'cells' / C.cell_dir((0, 1)) / 'result.json').read_text())
        self.assertEqual((res['set'], res['record_masters']), ('bloodmoon', ['Bloodmoon.esm']))
        self.assertIn('bloodmoon 1, none 5, vvardenfell 2', out)
        # a result written before the rule carries no set and the feed names none (the tracker keeps what it had)
        res.pop('set')
        self.assertNotIn('set', C.tracker_cell(res, {}))

    def test_named_cells_only_and_a_cell_that_is_not_open_sea_is_refused(self):
        run = self.root / 'run'
        lands = {(0, 0): land()}
        rc, out = self.run_with_records(self.args(run, cells='0,1 1,1'), lands, {(1, 1): ('Bloodmoon.esm',)})
        self.assertEqual(rc, 0, out)
        doc = json.loads((run / 'ocean' / 'plan.json').read_text())
        self.assertEqual([(r['x'], r['y']) for r in doc['cells']], [(0, 1), (1, 1)])
        self.assertEqual(doc['selection'], {'cells': ['0,1', '1,1'], 'of': 8})
        self.assertEqual(sorted(json.loads(C.feed(run).read_text())['cells']), ['0,1', '1,1'])
        self.assertIn('1,1: set bloodmoon; CELL record in Bloodmoon.esm', out)
        self.assertIn('0,1: set none (the nearest island); CELL record in no master', out)
        other = self.root / 'other'
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc, _ = self.run_with_records(self.args(other, cells='0,1 0,0 5,5'), lands, {})
        self.assertEqual(rc, 2)
        self.assertIn('2 of the 3 named cells are not open sea', err.getvalue())
        self.assertIn('0,0: it has a LAND record', err.getvalue())
        self.assertIn('5,5: it lies outside the open-sea plan', err.getvalue())
        self.assertFalse((other / 'ocean').exists())             # refused before anything is written

    def test_the_presented_folder_is_planned_from_its_base_file_and_the_records_from_the_game_files(self):
        run = self.root / 'run'
        folder = self.root / 'presented'
        seen = {}

        def lands(data_files, masters=None):
            seen['lands'] = (data_files, masters)
            return {(0, 0): land()}, set(), {}, 'sha'

        def records(data_files, masters=None):
            seen['records'] = data_files
            return {}

        with patch.object(C, 'presented_data_folder',
                          return_value=(folder, {'masters': ['Morrowind.esm', 'Bloodmoon.esm']})), \
                patch.object(C, 'master_lands', side_effect=lands), \
                patch.object(C, 'ocean_record_masters', side_effect=records), \
                patch.object(C, 'ocean_ground_textures', return_value=dict(GROUND)), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = C.ocean(self.args(run, presented_data=folder, dry_run=True))
        self.assertEqual(rc, 0)
        self.assertEqual(seen['lands'], (folder, ('Morrowind.esm',)))   # its Morrowind.esm is the merged master
        self.assertEqual(seen['records'], self.root)                   # where each record comes from: the game's files


def raw_record(tag, subs, flags=0):
    payload = b''.join(struct.pack('<4sI', t, len(d)) + d for t, d in subs)
    return struct.pack('<4sIII', tag, len(payload), 0, flags) + payload


def raw_cell(x, y, bits=0, flags=0, refs=False):
    subs = [(b'NAME', b'\0'), (b'DATA', struct.pack('<Iii', bits, x, y))]
    if refs:
        subs += [(b'FRMR', struct.pack('<I', 1)), (b'NAME', b'kelp\0'), (b'DATA', bytes(24))]
    return raw_record(b'CELL', subs, flags)


class TheSetRule(unittest.TestCase):
    """TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68: an open-sea cell's set from the master that holds its CELL record."""

    def test_the_first_master_in_load_order_listed_cells_and_no_record(self):
        self.assertEqual(C.ocean_set((0, 1), ('Bloodmoon.esm',)), 'bloodmoon')
        self.assertEqual(C.ocean_set((0, 1), ('Bloodmoon.esm', 'Morrowind.esm')), 'vvardenfell')   # load order
        self.assertEqual(C.ocean_set((0, 1), ('bloodmoon.ESM',)), 'bloodmoon')
        self.assertEqual(C.ocean_set((0, 1), ('Tribunal.esm',)), 'tribunal')
        self.assertEqual(C.ocean_set((-19, 14), ('Bloodmoon.esm',), {(-19, 14)}), 'vvardenfell')   # the base world's
        self.assertEqual(C.ocean_set((-6, 26), (), {(-6, 26)}), 'vvardenfell')
        self.assertIsNone(C.ocean_set((-20, 14), ()))

    def test_the_base_worlds_list_holds_its_three_open_sea_frames_of_bloodmoon_or_no_record(self):
        listed = C.ocean_base_world_cells()
        self.assertTrue({(-19, 14), (-19, 15), (-6, 26)} <= listed)
        self.assertFalse({(-29, 23), (-28, 24), (-20, 14)} & listed)

    def test_the_masters_that_hold_a_cells_record_are_read_from_their_own_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Morrowind.esm').write_bytes(raw_cell(1, 1) + raw_cell(2, 2, refs=True) + raw_cell(5, 5, bits=1)
                                                 + raw_cell(3, 3, flags=0x20))
            (root / 'Morrowind.bsa').write_bytes(b'')
            (root / 'Bloodmoon.esm').write_bytes(raw_cell(0, 1) + raw_cell(1, 1, refs=True))
            got = C.ocean_record_masters(root, ('Morrowind.esm', 'Bloodmoon.esm'))
            self.assertEqual(got, {(1, 1): ('Morrowind.esm', 'Bloodmoon.esm'), (2, 2): ('Morrowind.esm',),
                                   (0, 1): ('Bloodmoon.esm',)})     # no interior, no deleted cell
            # a selected master missing from the folder is left out
            self.assertEqual(C.ocean_record_masters(root, ('Morrowind.esm', 'Tribunal.esm')),
                             {(1, 1): ('Morrowind.esm',), (2, 2): ('Morrowind.esm',)})


if __name__ == '__main__':
    unittest.main()
