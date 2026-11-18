# SPDX-License-Identifier: GPL-3.0-only
"""CHIMport cell keys and the expansion layers (CHIMPORT-CELL-KEY-LAYERS-65): selecting the layers re-keys only the
cells whose frame they change (their own and neighbours' merged CELL/LAND records, the objects placed there), never
the whole island. Small synthetic masters: no game data."""
import contextlib
import io
import json
import os
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import chimport  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def tes3(*masters):
    out = [sub('HEDR', struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', 0))]
    for m in masters:
        out += [sub('MAST', m), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', *out)


def cell(x, y, *refs):
    return rec('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 2, x, y)), *refs)


def land(x, y):
    return rec('LAND', sub('INTV', struct.pack('<ii', x, y)), sub('DATA', struct.pack('<I', 0)))


def ref(number, ident):
    return sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident) + sub('DATA', struct.pack('<6f', *[0.0] * 6))


BASE = (tes3() + rec('STAT', sub('NAME', 'rock'), sub('MODL', 'rock.nif'))
        + rec('STAT', sub('NAME', 'boat'), sub('MODL', 'boat.nif'))
        + b''.join(cell(x, y, ref(10 * x + y + 100, 'rock')) + land(x, y) for x in range(0, 9) for y in range(0, 3)))
# Bloodmoon: one placement more in island cell (6,1), a changed boat record placed only in (2,1), its own cell
BLOODMOON = (tes3('Morrowind.esm') + rec('STAT', sub('NAME', 'boat'), sub('MODL', 'boat2.nif'))
             + cell(6, 1, ref(1, 'rock')) + cell(-20, 20, ref(2, 'rock')) + land(-20, 20))
BASE = BASE.replace(cell(2, 1, ref(121, 'rock')), cell(2, 1, ref(121, 'rock'), ref(999, 'boat')))


class LayerKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        data = Path(self.tmp.name) / 'Data Files'
        data.mkdir()
        (data / 'Morrowind.esm').write_bytes(BASE)
        (data / 'Bloodmoon.esm').write_bytes(BLOODMOON)
        self.palette = Path(self.tmp.name) / 'palette.lmp'
        self.palette.write_bytes(bytes(768))
        lock = Path(self.tmp.name) / 'lock.json'
        lock.write_text(json.dumps({'files': {str(data / 'Morrowind.esm'): {'sha256': 'a' * 64},
                                              str(data / 'Bloodmoon.esm'): {'sha256': 'b' * 64}}}))
        self.data = data
        self.env = {'AMIWIND_INPUTS_LOCK': str(lock)}
        chimport._TOUCH.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def keys(self, masters):
        env = dict(self.env, AMIWIND_MASTERS=masters)
        with mock.patch.dict(os.environ, env):
            out = {}
            for x in range(0, 9):
                for y in range(0, 3):
                    key, why = chimport.cell_key((x, y), self.data, self.palette)
                    self.assertIsNotNone(key, why)
                    out[(x, y)] = key
            return out

    def test_only_the_cells_a_layer_changes_are_re_keyed(self):
        alone = self.keys('Morrowind.esm')
        layered = self.keys('Morrowind.esm,Bloodmoon.esm')
        moved = {c for c in alone if alone[c] != layered[c]}
        # (6,1) and its 3 x 3 neighbours (its frame reads them); (2,1) places the boat Bloodmoon changes, and so do
        # the frames around it
        expected = {(x, y) for x in (5, 6, 7) for y in (0, 1, 2)} | {(x, y) for x in (1, 2, 3) for y in (0, 1, 2)}
        self.assertEqual(moved, expected)
        self.assertEqual(alone[(0, 0)], layered[(0, 0)])
        self.assertEqual(alone[(8, 2)], layered[(8, 2)])

    def test_no_layer_no_touch(self):
        self.assertIsNone(chimport.layer_touch((6, 1), self.data, ['Morrowind.esm']))
        self.assertIsNotNone(chimport.layer_touch((6, 1), self.data, ['Morrowind.esm', 'Bloodmoon.esm']))
        self.assertIsNone(chimport.layer_touch((0, 0), self.data, ['Morrowind.esm', 'Bloodmoon.esm']))


def tes3_counted(count):
    """A standalone master's header (no master list) that names COUNT records after it, as mwad.audit.load_esm wants."""
    return rec('TES3', sub('HEDR', struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', count)))


def land_heights(x, y):
    """A LAND with a 4232-byte VHGT (all heights 0), so the cell has land for every reader."""
    return rec('LAND', sub('INTV', struct.pack('<ii', x, y)), sub('DATA', struct.pack('<I', 1)),
               sub('VHGT', struct.pack('<f', 0.0) + bytes(4225) + bytes(3)))


def master(*records):
    return tes3_counted(len(records)) + b''.join(records)


def empty_bsa():
    """A TES3 archive (version 0x100) without entries."""
    return struct.pack('<III', 0x100, 0, 0)


class PlanCheck(unittest.TestCase):
    """CHIMPORT-LAYER-CELL-EMPTY-67: a cell whose build read less than the run's plan holds fails instead of counting
    as empty. The first live run of 8 Solstheim cells (17 November 2026) read the base game's file alone in the cells'
    terrain audit (src/mwad/audit.py) and built each as flat ground with nothing placed, status empty (done). Small
    synthetic masters: a base game file without the cell, a layer that adds it with land and two placements."""

    CELL = (-20, 20)

    def setUp(self):
        from mwad.masters import merge
        self.tmp = TemporaryDirectory()
        root = Path(self.tmp.name)
        stat = rec('STAT', sub('NAME', 'rock'), sub('MODL', 'rock.nif'))
        self.base = master(stat, cell(0, 0, ref(100, 'rock')), land_heights(0, 0))
        self.layer = (tes3('Morrowind.esm') + cell(*self.CELL, ref(1, 'rock'), ref(2, 'rock'))
                      + land_heights(*self.CELL))
        self.merged = merge([('Morrowind.esm', self.base), ('Bloodmoon.esm', self.layer)])
        self.plain = root / 'plain' / 'Data Files'                 # the game's own folder: base file and layer
        self.plain.mkdir(parents=True)
        (self.plain / 'Morrowind.esm').write_bytes(self.base)
        (self.plain / 'Bloodmoon.esm').write_bytes(self.layer)
        (self.plain / 'Morrowind.bsa').write_bytes(empty_bsa())
        self.layered = root / 'layered' / 'Data Files'             # the merged master under the base file's name
        self.layered.mkdir(parents=True)
        (self.layered / 'Morrowind.esm').write_bytes(self.merged)
        (self.layered / 'Morrowind.bsa').write_bytes(empty_bsa())
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def plan_row(self):
        from mwad.audit import load_esm
        path = self.root / 'merged.esm'
        path.write_bytes(self.merged)
        cells = chimport.census(load_esm(path))
        return dict(cells[self.CELL], x=self.CELL[0], y=self.CELL[1])

    def built(self, data, name):
        """The cell's source facts and records as convert_cell records them, from the cell's terrain audit of DATA."""
        from mwad.audit import audit
        work = self.root / name / 'work' / 'cm20_p20'
        with contextlib.redirect_stdout(io.StringIO()):
            audit(data, work / 'audit', self.CELL, 0, 4, missing_land='flat')
        return {'converted': True, 'errors': [], 'audits': {}, 'records': chimport.record_accounting(work, None, set()),
                'source': chimport.source_facts(work)}

    def test_the_plan_holds_the_layer_cell(self):
        row = self.plan_row()
        self.assertTrue(row['land'])
        self.assertEqual(row['refs'], 2)

    def test_a_cell_built_from_the_base_file_alone_fails(self):
        # today's case: the plan reads the merged masters, the cell's build read the base game's file
        row, res = self.plan_row(), self.built(self.plain, 'plain-run')
        self.assertEqual(res['records']['totals']['placed'], 0)
        self.assertTrue(res['source']['default_land'])
        problems = chimport.plan_mismatch(row, res)
        self.assertEqual(len(problems), 3, problems)
        self.assertIn('the build read none', problems[0])
        self.assertIn('the plan holds 2 placements in -20,20, the build read 0', problems[1])
        chimport.check_against_plan(row, res)
        self.assertEqual([e['mechanism'] for e in res['errors']], [chimport.PLAN_MISMATCH])
        self.assertEqual(chimport.cell_status(res), 'failed')         # never 'empty', which counts as done

    def test_a_cell_built_from_the_layered_folder_passes_the_check(self):
        # the layered data folder (tools/chim_layer_data.py's method): the merged master under the base file's name
        row, res = self.plan_row(), self.built(self.layered, 'layered-run')
        self.assertEqual(res['records']['totals']['placed'], 2)
        self.assertFalse(res['source']['default_land'])
        self.assertEqual(chimport.plan_mismatch(row, res), [])
        chimport.check_against_plan(row, res)
        self.assertEqual(res['errors'], [])

    def test_the_run_reads_the_presented_data_folder(self):
        # chimport.py run --presented-data DIR: the folder tools/presented_data.py makes from the plain folder; its
        # base-named master is the merged one, so the cell's build reads what the plan holds
        out = self.root / 'run' / 'data'
        with contextlib.redirect_stdout(io.StringIO()):
            folder, receipt = chimport.presented_data_folder(self.plain, out, ['Morrowind.esm', 'Bloodmoon.esm'])
        self.assertEqual(folder, out)
        self.assertEqual(receipt['masters'], ['Morrowind.esm', 'Bloodmoon.esm'])
        self.assertTrue((out / 'Morrowind.bsa').is_symlink())
        row, res = self.plan_row(), self.built(folder, 'presented-run')
        self.assertEqual(res['records']['totals']['placed'], 2)
        self.assertEqual(chimport.plan_mismatch(row, res), [])
        # the base game alone: no folder, the data folder itself
        with contextlib.redirect_stdout(io.StringIO()):
            alone, none = chimport.presented_data_folder(self.plain, self.root / 'run2' / 'data', ['Morrowind.esm'])
        self.assertIsNone(none)
        self.assertEqual(alone.resolve(), self.plain.resolve())
        self.assertFalse((self.root / 'run2').exists())

    def test_not_converted_and_empty_sea_cells_are_left_alone(self):
        sea = {'x': 1, 'y': 1, 'land': False, 'refs': 0}
        self.assertEqual(chimport.plan_mismatch(sea, {'converted': True, 'records': {'totals': {'placed': 0}},
                                                      'source': {'default_land': True}}), [])
        self.assertEqual(chimport.plan_mismatch(dict(sea, land=True, refs=3), {'converted': False}), [])

    def test_header_only_layers_give_the_presented_master_back(self):
        # the presented data folder (tools/presented_exterior.py): the presented master, itself a merge whose numbers
        # carry the layer's stride, under the base file's name, and the two layers as header-only files; selecting the
        # three masters merges it again, and every cell, reference number and position must come back unchanged
        from mwad.audit import load_esm
        from mwad.masters import ADDON_KEY_STRIDE, merge
        header_only = rec('TES3', sub('HEDR', struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', 0)))
        again = merge([('Morrowind.esm', self.merged), ('Tribunal.esm', header_only), ('Bloodmoon.esm', header_only)])
        paths = []
        for name, raw in (('presented.esm', self.merged), ('again.esm', again)):
            path = self.root / name
            path.write_bytes(raw)
            paths.append(path)
        first, second = (load_esm(p) for p in paths)
        numbers = sorted(r['number'] for r in first['cells'][self.CELL]['refs'])
        self.assertEqual(numbers, [2 * ADDON_KEY_STRIDE + 1, 2 * ADDON_KEY_STRIDE + 2])
        self.assertEqual(first['cells'], second['cells'])
        self.assertEqual(first['lands'], second['lands'])
        self.assertEqual(first['objects'], second['objects'])


class SearchPathTests(unittest.TestCase):
    """CHIMPORT-CLI-MWAD-SHADOW-66: after an import that puts tools/ first, the package src/mwad still wins over
    the command tools/mwad.py (the chimport-region route runs the command line on a fresh run folder)."""

    def test_src_before_tools_again(self):
        saved = list(sys.path)
        try:
            sys.path.insert(0, str(ROOT / 'tools'))
            chimport._own_search_path()
            self.assertEqual(sys.path[0], str(ROOT / 'src'))
            self.assertEqual(sys.path[1], str(ROOT / 'tools'))
            self.assertEqual(sys.path.count(str(ROOT / 'tools')), 1)
        finally:
            sys.path[:] = saved


if __name__ == '__main__':
    unittest.main()
