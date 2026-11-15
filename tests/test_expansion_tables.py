# SPDX-License-Identifier: GPL-3.0-only
"""EXPANSION-DATA-ALL-TABLES-66: every table the builder makes from the game data reads the SELECTED masters (the base
game with Tribunal and/or Bloodmoon, both by default) through the merging reader (src/mwad/masters.py), and the base
game alone gives exactly what it gave before.

1. A scan of tools/ and src/: a direct read of the base game file alone (child_ci(..., 'Morrowind.esm'), or a module
   name bound to that literal) is refused outside ALLOWED, which names each reader that stays base-only and why
   (docs/EXPANSION_TABLES.md is the table of every table).
2. Synthetic-layer tests for the tables fixed in round 2 (prepare_travel, prepare_magic, the focus reference table,
   dialogue_choices): with the layers selected they read the layer's records; with the base game alone they read
   only the base file, even when the expansion files are present.
"""
import ast
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

BASE = 'Morrowind.esm'
# file -> why it may read the base game file alone (docs/EXPANSION_TABLES.md "Base-only by design")
ALLOWED = {
    'tools/chim_build.py': 'the CHIM base world (Vvardenfell); the layers are built by tools/chim_layer_data.py',
    'tools/chim_layer_data.py': 'the layer step reads the base file to tell the layer\'s own records from it',
    'tools/chim/sol_test.py': 'a test fixture of the Solstheim layer (reads the base beside the layer)',
    'tools/chim/flames.py': 'a presence check only: the light records are read from mwad.masters.master_path',
    'src/mwad/paths.py': 'the game input check: the base file must be in the data folder',
    'src/mwad/doctor.py': 'the input inventory (file sizes of the base file and archive), no table',
    'src/mwad/audit.py': 'the base terrain audit of a square of Vvardenfell around a centre cell (a debugging '
                         'survey, no shipped table)',
}
FIND = ('child_ci', 'joinpath')


def _base_names(tree):
    """Module-level names bound to the base game file's literal."""
    out = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value == BASE:
            out.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return out


def _is_base(node, names):
    return (isinstance(node, ast.Constant) and node.value == BASE) or (isinstance(node, ast.Name) and node.id in names)


def base_reads(path):
    """[(line, what)] of the direct base-file reads in PATH."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    names = _base_names(tree)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
            if func in FIND and any(_is_base(a, names) for a in node.args[1 if func == 'child_ci' else 0:]):
                found.append((node.lineno, func))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and _is_base(node.right, names):
            found.append((node.lineno, '/'))
    return found


class BaseReadScan(unittest.TestCase):
    def test_no_base_only_reader_outside_the_allow_list(self):
        bad = []
        for folder in ('tools', 'src'):
            for path in sorted((ROOT / folder).rglob('*.py')):
                rel = path.relative_to(ROOT).as_posix()
                if rel in ALLOWED or '/retired' in rel:
                    continue
                bad += ['%s:%d (%s)' % (rel, line, what) for line, what in base_reads(path)]
        self.assertEqual(bad, [], 'a table reads Morrowind.esm alone: read the selected masters '
                                  '(mwad.masters.master_path / selected_masters) or add the file to ALLOWED with '
                                  'its reason and to docs/EXPANSION_TABLES.md')

    def test_allow_list_is_current(self):
        for rel in ALLOWED:
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertTrue(base_reads(ROOT / rel), '%s no longer reads the base file alone: take it off ALLOWED' % rel)

    def test_the_table_of_tables_names_every_allowed_reader(self):
        doc = (ROOT / 'docs' / 'EXPANSION_TABLES.md').read_text(encoding='utf-8')
        for rel in ALLOWED:
            self.assertIn(rel, doc)

    def test_scan_finds_a_base_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'x.py'
            p.write_text("M = 'Morrowind.esm'\ndef f(d):\n    return child_ci(d, M), d / 'Morrowind.esm'\n",
                         encoding='utf-8')
            self.assertEqual([w for _, w in base_reads(p)], ['child_ci', '/'])


# ---- synthetic masters ----------------------------------------------------------------------------------------------

def _sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def _rec(tag, *subs):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, 0) + payload


def _z(text):
    return text.encode('cp1252') + b'\0'


def _master(*recs, masters=()):
    hedr = struct.pack('<fI', 1.3, 0) + bytes(32) + bytes(256) + struct.pack('<I', len(recs))
    head = [_sub('HEDR', hedr)]
    for m in masters:
        head += [_sub('MAST', _z(m)), _sub('DATA', struct.pack('<Q', 0))]
    return _rec('TES3', *head) + b''.join(recs)


def _gmst(name, value):
    return _rec('GMST', _sub('NAME', _z(name)), _sub('FLTV', struct.pack('<f', value)))


def _traveller(ident, x):
    return _rec('NPC_', _sub('NAME', _z(ident)), _sub('FNAM', _z(ident.title())),
                _sub('DODT', struct.pack('<6f', x, 0, 0, 0, 0, 0)))


def _mgef(index):
    return _rec('MGEF', _sub('INDX', struct.pack('<i', index)), _sub('MEDT', struct.pack('<ifiiii', 0, 1.0, 0, 1, 2, 3)))


class _Data:
    """A data folder with a base file and both expansions."""

    def __init__(self, base, tribunal, bloodmoon):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        (self.path / 'Morrowind.esm').write_bytes(base)
        (self.path / 'Tribunal.esm').write_bytes(tribunal)
        (self.path / 'Bloodmoon.esm').write_bytes(bloodmoon)

    def close(self):
        self.tmp.cleanup()


class _Selection:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.old = os.environ.get('AMIWIND_MASTERS')
        if self.value is None:
            os.environ.pop('AMIWIND_MASTERS', None)
        else:
            os.environ['AMIWIND_MASTERS'] = self.value

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop('AMIWIND_MASTERS', None)
        else:
            os.environ['AMIWIND_MASTERS'] = self.old


ALL = 'Morrowind.esm,Tribunal.esm,Bloodmoon.esm'


class TravelLayers(unittest.TestCase):
    def setUp(self):
        self.data = _Data(_master(_gmst('fTravelMult', 4000.0), _traveller('base_guide', 1.0)),
                          _master(_traveller('trib_guide', 2.0), masters=('Morrowind.esm',)),
                          _master(_traveller('bm_guide', 3.0), _gmst('fTravelMult', 5000.0),
                                  masters=('Morrowind.esm', 'Tribunal.esm')))

    def tearDown(self):
        self.data.close()

    def test_selected_layers_are_read(self):
        import prepare_travel as T
        with _Selection(ALL):
            providers, settings, _cells, _regions, found = T.read_masters(self.data.path)
        self.assertEqual(sorted(providers), ['base_guide', 'bm_guide', 'trib_guide'])
        self.assertEqual(providers['bm_guide']['master'], 'Bloodmoon.esm')
        self.assertEqual(settings['ftravelmult'], 5000.0)
        self.assertEqual(found, ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'])

    def test_base_alone_reads_the_base_file_only(self):
        import prepare_travel as T
        with _Selection(None):
            providers, settings, _cells, _regions, found = T.read_masters(self.data.path)
        self.assertEqual(sorted(providers), ['base_guide'])
        self.assertEqual(settings['ftravelmult'], 4000.0)
        self.assertEqual(found, ['Morrowind.esm'])


class MagicLayers(unittest.TestCase):
    def setUp(self):
        self.data = _Data(_master(_mgef(1)), _master(_mgef(2), masters=('Morrowind.esm',)),
                          _master(_mgef(3), masters=('Morrowind.esm', 'Tribunal.esm')))

    def tearDown(self):
        self.data.close()

    def test_selection(self):
        import prepare_magic as M
        with _Selection(ALL):
            self.assertEqual(sorted(M.read_records(self.data.path)[0]), [1, 2, 3])
        with _Selection('Morrowind.esm,Bloodmoon.esm'):
            self.assertEqual(sorted(M.read_records(self.data.path)[0]), [1, 3])
        with _Selection(None):
            self.assertEqual(sorted(M.read_records(self.data.path)[0]), [1])


class FocusReferenceFiles(unittest.TestCase):
    """The AWI1 file list names every content file whose references the merged master holds."""

    def _files(self, payload):
        n, at, out = payload[4], 5, []
        for _ in range(n):
            index, length = payload[at], payload[at + 1]
            name = payload[at + 2:at + 2 + length].decode('ascii')
            refs = struct.unpack_from('<I', payload, at + 2 + length)[0]
            out.append((index, name, refs, payload[at + 6 + length:at + 14 + length].hex()))
            at += 14 + length
        return out

    def test_base_alone_is_one_entry(self):
        import prepare_focus as F
        from unittest import mock
        with mock.patch.object(F, 'cells_of', return_value=[('c', True, (0, 0), '', [
                {'number': 5, 'NAME': b'a\0'}, {'number': 9, 'NAME': b'b\0'}])]), \
                mock.patch.object(F, 'reference_flags', return_value={}), \
                mock.patch.object(F, 'respawn_settings', return_value=(4, 72.0, 72.0)):
            raw, rows, _ = F.reference_table(b'', 'ab' * 32, hashes={'Morrowind.esm': 'ab' * 32, 'Tribunal.esm': 'cd' * 32})
        self.assertEqual(rows, 2)
        self.assertEqual(self._files(raw), [(0, 'Morrowind.esm', 2, 'ab' * 8)])
        self.assertEqual(raw[:5 + 2 + 13 + 4 + 8],
                         b'AWI1' + struct.pack('<BBB', 1, 0, 13) + b'Morrowind.esm' + struct.pack('<I', 2) +
                         bytes.fromhex('ab' * 8))

    def test_merged_numbers_name_their_files(self):
        import prepare_focus as F
        from unittest import mock
        stride = 1 << 22
        refs = [{'number': 5, 'NAME': b'a\0'}, {'number': 2 * stride + 7, 'NAME': b'b\0'},
                {'number': 2 * stride + 8, 'NAME': b'c\0'}]
        with mock.patch.object(F, 'cells_of', return_value=[('c', True, (0, 0), '', refs)]), \
                mock.patch.object(F, 'reference_flags', return_value={}), \
                mock.patch.object(F, 'respawn_settings', return_value=(4, 72.0, 72.0)):
            raw, rows, _ = F.reference_table(b'', 'ab' * 32, hashes={'Morrowind.esm': 'ab' * 32,
                                                                       'Bloodmoon.esm': 'ef' * 32})
        self.assertEqual(rows, 3)
        self.assertEqual(self._files(raw), [(0, 'Morrowind.esm', 1, 'ab' * 8), (2, 'Bloodmoon.esm', 2, 'ef' * 8)])


class DialogueChoicesTable(unittest.TestCase):
    def test_the_default_selection_is_every_master(self):
        import dialogue_choices as C
        self.assertEqual(C.DEFAULT_SELECTION, C.MASTERS)
        self.assertEqual(C.DEFAULT_SELECTION[0], C.TABLE_MASTER)


if __name__ == '__main__':
    unittest.main()
