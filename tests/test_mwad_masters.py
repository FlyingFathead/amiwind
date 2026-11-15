# SPDX-License-Identifier: GPL-3.0-only
"""The merging reader (src/mwad/masters.py) on small synthetic masters: no game data."""
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad import masters as M  # noqa: E402
from mwad.esm import records, subrecords, string  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs, flags=0):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, flags) + payload


def tes3(*masters):
    hedr = struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', 0)
    out = [sub('HEDR', hedr)]
    for m in masters:
        out += [sub('MAST', m), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', *out)


def cell_ext(x, y, *refs, name='', region=None):
    head = [sub('NAME', name), sub('DATA', struct.pack('<Iii', 2, x, y))]
    if region:
        head.append(sub('RGNN', region))
    return rec('CELL', *head, *refs)


def cell_int(name, *refs):
    return rec('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iii', 1, 0, 0)), *refs)


def ref(number, ident, deleted=False):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident) + sub('DATA', struct.pack('<6f', *[0.0] * 6))
    return out + (sub('DELE', b'\0\0\0\0') if deleted else b'')


def info(ident, prev, nxt, text):
    return rec('INFO', sub('INAM', ident), sub('PNAM', prev), sub('NNAM', nxt), sub('NAME', text))


BASE = (tes3()
        + rec('STAT', sub('NAME', 'rock'), sub('MODL', 'base_rock.nif'))
        + rec('STAT', sub('NAME', 'tree'), sub('MODL', 'tree.nif'))
        + rec('DIAL', sub('NAME', 'Greeting'), sub('DATA', b'\x02'))
        + info('1', '', '2', 'first') + info('2', '1', '', 'second')
        + cell_ext(0, 0, ref(1, 'rock'), ref(2, 'tree'), region='ascadian isles region')
        + cell_int('Room', ref(3, 'rock')))

ADDON = (tes3('Morrowind.esm')
         + rec('STAT', sub('NAME', 'Rock'), sub('MODL', 'addon_rock.nif'))       # replaces (ids fold case)
         + rec('STAT', sub('NAME', 'tree'), sub('DELE', b'\0\0\0\0'))           # deletes
         + rec('STAT', sub('NAME', 'bush'), sub('MODL', 'bush.nif'))            # new
         + rec('DIAL', sub('NAME', 'greeting'), sub('DATA', b'\x02'))
         + info('9', '1', '2', 'inserted')                                      # after 1
         + info('2', '1', '', 'second replaced?')                               # same id + same prev: in place
         + cell_ext(0, 0, ref(1 | 1 << 24, 'rock', deleted=True), ref(5, 'bush'), name='Newname')
         + cell_int('Room', ref(3 | 1 << 24, 'bush'))
         + cell_int('New Room', ref(6, 'bush')))


def parsed(raw):
    out = []
    for tag, flags, payload in records(raw):
        out.append((tag, list(subrecords(payload))))
    return out


def field(subs, tag):
    return next(d for t, d in subs if t == tag)


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.out = parsed(M.merge([('Morrowind.esm', BASE), ('Tribunal.esm', ADDON)]))

    def stats(self):
        return {string(field(s, 'NAME')): string(field(s, 'MODL')) for t, s in self.out if t == 'STAT'}

    def test_replaced_deleted_and_new_records(self):
        self.assertEqual(self.stats(), {'Rock': 'addon_rock.nif', 'bush': 'bush.nif'})
        self.assertEqual([t for t, _ in self.out][:3], ['TES3', 'STAT', 'DIAL'])   # the replacement kept its place

    def test_header_count_and_no_masters(self):
        tag, subs = self.out[0]
        self.assertNotIn('MAST', [t for t, _ in subs])
        self.assertEqual(struct.unpack_from('<I', field(subs, 'HEDR'), 296)[0], len(self.out) - 1)

    def test_info_inserted_by_prev_link(self):
        infos = [(string(field(s, 'INAM')), string(field(s, 'PNAM')), string(field(s, 'NNAM')),
                  string(field(s, 'NAME'))) for t, s in self.out if t == 'INFO']
        self.assertEqual(infos, [('1', '', '9', 'first'), ('9', '1', '2', 'inserted'),
                                 ('2', '9', '', 'second replaced?')])
        self.assertEqual(sum(1 for t, _ in self.out if t == 'DIAL'), 1)

    def test_info_same_prev_replaces_in_place(self):
        raw = M.merge([('Morrowind.esm', BASE), ('Tribunal.esm', tes3('Morrowind.esm')
                       + rec('DIAL', sub('NAME', 'Greeting'), sub('DATA', b'\x02')) + info('2', '1', '', 'new'))])
        infos = [string(field(s, 'NAME')) for t, s in parsed(raw) if t == 'INFO']
        self.assertEqual(infos, ['first', 'new'])

    def cells(self):
        out = {}
        for t, s in self.out:
            if t != 'CELL':
                continue
            bits, x, y = struct.unpack('<Iii', field(s, 'DATA'))
            key = string(field(s, 'NAME')) if bits & 1 else (x, y)
            refs = [struct.unpack('<I', d)[0] for tt, d in s if tt == 'FRMR']
            names = [string(d) for i, (tt, d) in enumerate(s) if tt == 'NAME' and i and s[i - 1][0] == 'FRMR']
            out[key] = (string(field(s, 'NAME')), dict(s).get('RGNN'), list(zip(refs, names)))
        return out

    def test_merged_cell_with_added_references(self):
        cells = self.cells()
        name, region, refs = cells[(0, 0)]
        self.assertEqual(name, 'Newname')                          # the later header field replaces
        self.assertEqual(string(region), 'ascadian isles region')  # an absent one is kept
        self.assertEqual(refs, [(2, 'tree'), (1 * M.ADDON_KEY_STRIDE + 5, 'bush')])   # 1 deleted, 5 added
        self.assertEqual(cells['Room'][2], [(3, 'bush')])          # the base reference 3 replaced
        self.assertEqual(cells['New Room'][2], [(M.ADDON_KEY_STRIDE + 6, 'bush')])
        self.assertEqual(len(cells), 3)

    def test_moved_reference(self):
        moved = (sub('MVRF', struct.pack('<I', 1 | 1 << 24)) + sub('CNDT', struct.pack('<ii', 1, 0))
                 + ref(1 | 1 << 24, 'rock'))
        raw = M.merge([('Morrowind.esm', BASE), ('Bloodmoon.esm', tes3('Morrowind.esm') + cell_ext(0, 0, moved))])
        self.out = parsed(raw)
        cells = self.cells()
        self.assertEqual([r for r, _ in cells[(0, 0)][2]], [2])
        self.assertEqual([r for r, _ in cells[(1, 0)][2]], [1])

    def test_ltex_numbered_after_earlier_files(self):
        def land(v):
            return rec('LAND', sub('INTV', struct.pack('<ii', 0, 0)), sub('VTEX', struct.pack('<256H', *[v] * 256)))
        base = tes3() + rec('LTEX', sub('NAME', 'a'), sub('INTV', struct.pack('<I', 4)), sub('DATA', 'a.dds'))
        addon = (tes3('Morrowind.esm') + rec('LTEX', sub('NAME', 'b'), sub('INTV', struct.pack('<I', 0)),
                                              sub('DATA', 'b.dds')) + land(1))
        out = parsed(M.merge([('Morrowind.esm', base), ('Bloodmoon.esm', addon)]))
        numbers = [struct.unpack('<I', field(s, 'INTV'))[0] for t, s in out if t == 'LTEX']
        self.assertEqual(numbers, [4, 5])
        vtex = struct.unpack('<256H', field(next(s for t, s in out if t == 'LAND'), 'VTEX'))
        self.assertEqual(set(vtex), {6})        # 1-based index 1 of the add-on = its LTEX 0 = merged 5, + 1

    def test_base_alone_is_the_base_file(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / 'morrowind.esm').write_bytes(BASE)
            self.assertEqual(M.master_bytes(tmp, ['Morrowind.esm']), BASE)
            self.assertEqual(M.master_path(tmp, ['Morrowind.esm']).read_bytes(), BASE)

    def test_merged_path_cached(self):
        with TemporaryDirectory() as tmp:
            (Path(tmp) / 'Morrowind.esm').write_bytes(BASE)
            (Path(tmp) / 'Tribunal.esm').write_bytes(ADDON)
            out = Path(tmp) / 'merged'
            path = M.master_path(tmp, 'Morrowind.esm,Tribunal.esm', merged_dir=out)
            self.assertEqual(path.name, 'Morrowind.esm')
            self.assertEqual(path.read_bytes(), M.master_bytes(tmp, ['Morrowind.esm', 'Tribunal.esm']))
            self.assertEqual(M.master_path(tmp, 'Morrowind.esm,Tribunal.esm', merged_dir=out), path)

    def test_masters_from_the_environment(self):
        import os
        old = os.environ.get(M.MASTERS_ENV)
        try:
            os.environ[M.MASTERS_ENV] = 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm'
            self.assertEqual(M.selected_masters(), ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'))
            del os.environ[M.MASTERS_ENV]
            self.assertEqual(M.selected_masters(), ('Morrowind.esm',))
        finally:
            if old is not None:
                os.environ[M.MASTERS_ENV] = old

    def test_selected_masters(self):
        self.assertEqual(M.selected_masters(''), ('Morrowind.esm',))
        self.assertEqual(M.selected_masters('morrowind.esm, bloodmoon.esm'), ('Morrowind.esm', 'Bloodmoon.esm'))
        with self.assertRaises(M.FormatError):
            M.selected_masters('Tribunal.esm')
        with self.assertRaises(M.FormatError):
            M.selected_masters('Morrowind.esm,Other.esp')


if __name__ == '__main__':
    unittest.main()
