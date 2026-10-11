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


if __name__ == '__main__':
    unittest.main()
