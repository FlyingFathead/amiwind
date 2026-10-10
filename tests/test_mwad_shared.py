# SPDX-License-Identifier: GPL-3.0-only
"""The shared Morrowind data helpers (src/mwad/esm.py) and the readers that use them.

Synthetic records only; no game data. MWAD-SHARED-HELPERS-35: one string helper,
one deleted-record test, one subrecord walk, sorted input walks, and master
lists that agree between the path rules, the input check and the known inputs.
"""
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mwad import esm, input_check, paths  # noqa: E402
from mwad.audit import FormatError, load_esm  # noqa: E402
from mwad.interior import original_doors  # noqa: E402
import content_closure  # noqa: E402
import known_inputs as ki  # noqa: E402


def sub(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def record(tag, subs, flags=0):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, flags) + body


def tes3(count, masters=()):
    hedr = struct.pack('<fI', 1.3, 1) + b'author'.ljust(32, b'\0') + b'desc'.ljust(256, b'\0') + struct.pack('<I', count)
    return record('TES3', [sub('HEDR', hedr)] + [sub('MAST', m.encode() + b'\0') for m in masters])


class StringTests(unittest.TestCase):
    def test_cuts_at_the_first_nul(self):
        self.assertEqual(esm.string(b'abc\0\0junk'), 'abc')
        self.assertEqual(esm.string(b'abc\0'), 'abc')
        self.assertEqual(esm.string(b''), '')

    def test_decodes_cp1252(self):
        self.assertEqual(esm.string('Café –'.encode('cp1252') + b'\0'), 'Café –')

    def test_undecodable_byte_is_a_format_error_naming_the_field(self):
        with self.assertRaises(FormatError) as ctx:
            esm.string(b'ab\x81cd\0', 'NPC_ FNAM')
        self.assertIn('NPC_ FNAM', str(ctx.exception))
        self.assertIn('0x81', str(ctx.exception))
        self.assertEqual(esm.string(b'ab\x81cd\0', errors='replace'), 'ab�cd')

    def test_readers_use_the_one_helper(self):
        self.assertIs(content_closure.esm.string, esm.string)
        from mwad import audit, npc
        self.assertIs(audit.string, esm.string)
        self.assertIs(npc.text, esm.text)
        self.assertIs(npc.first, esm.first)
        self.assertIs(input_check.digest, esm.sha256_file)
        self.assertIs(ki.sha256_file, esm.sha256_file)

    def test_closure_stays_tolerant(self):
        self.assertEqual(content_closure.string(b'ab\x81cd\0'), 'ab�cd')

    def test_bad_tag_is_a_format_error(self):
        bad = b'\xff\xfe\xfd\xfc' + struct.pack('<I', 0)
        with self.assertRaises(FormatError):
            list(esm.subrecords(bad))
        with self.assertRaises(FormatError):
            list(esm.records(b'\xff\xfe\xfd\xfc' + struct.pack('<III', 0, 0, 0)))

    def test_unpack_names_the_field(self):
        with self.assertRaises(FormatError) as ctx:
            esm.unpack('<I', b'\0\0', 'NPC_ FLAG')
        self.assertIn('NPC_ FLAG', str(ctx.exception))
        with self.assertRaises(FormatError):
            esm.unpack('<I', b'\0\0\0\0\0', 'X', exact=True)
        self.assertEqual(esm.unpack('<H', b'\1\0\2\0', 'X', offset=2), (2,))


class DeletedTests(unittest.TestCase):
    def test_flag_or_dele(self):
        self.assertTrue(esm.is_deleted(0x20, []))
        self.assertTrue(esm.is_deleted(0, [('NAME', b'x'), ('DELE', b'\0\0\0\0')]))
        self.assertTrue(esm.is_deleted(0, {'DELE': b''}))
        self.assertFalse(esm.is_deleted(0x400, [('NAME', b'x')]))
        self.assertFalse(esm.is_deleted(0, {'NAME': b'x'}))

    def test_empty_dele_subrecord_counts(self):
        # npc.load_master used first(fields, 'DELE') truthiness: an empty DELE was missed.
        self.assertTrue(esm.is_deleted(0, [('DELE', b'')]))

    def test_cell_header_only(self):
        subs = [('NAME', b'c'), ('DATA', b'd'), ('FRMR', b'1234'), ('DELE', b'\0\0\0\0')]
        self.assertFalse(esm.is_deleted(0, subs, header_only=True))
        self.assertTrue(esm.is_deleted(0, subs))
        self.assertTrue(esm.is_deleted(0, [('NAME', b'c'), ('DELE', b'')] + subs[2:], header_only=True))

    def test_flagged_base_records_are_dropped_everywhere(self):
        stat = lambda name, flags: record('STAT', [sub('NAME', name + b'\0'), sub('MODL', b'a.nif\0')], flags)
        master = tes3(2) + stat(b'live', 0) + stat(b'gone', 0x20)
        master = master.replace(struct.pack('<I', 2), struct.pack('<I', 2), 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'm.esm'
            path.write_bytes(master)
            objects = load_esm(path)['objects']
        self.assertEqual(sorted(objects), ['live'])

    def test_closure_drops_flagged_and_dele_objects(self):
        stat = lambda name, flags, extra=(): record('STAT', [sub('NAME', name + b'\0'), sub('MODL', b'a.nif\0'), *extra], flags)
        m = content_closure.Master()
        m.read(stat(b'live', 0) + stat(b'flagged', 0x20) + stat(b'dele', 0, [sub('DELE', b'\0\0\0\0')]))
        self.assertEqual(sorted(m.objects), ['live'])


def door_cell(frmrs):
    subs = [sub('NAME', b'Room\0'), sub('DATA', struct.pack('<Iii', 1, 0, 0))]
    for number in frmrs:
        subs += [sub('FRMR', struct.pack('<I', number)), sub('NAME', b'door\0')]
    return record('CELL', subs)


class InteriorTests(unittest.TestCase):
    def test_duplicate_original_reference_number_is_refused(self):
        door = record('DOOR', [sub('NAME', b'door\0'), sub('MODL', b'd.nif\0')])
        original_doors(door + door_cell([5, 6]))
        with self.assertRaises(FormatError) as ctx:
            original_doors(door + door_cell([5, 5]))
        self.assertIn('Duplicate', str(ctx.exception))

    def test_deleted_door_and_cell_are_skipped(self):
        door = record('DOOR', [sub('NAME', b'door\0'), sub('MODL', b'd.nif\0')], 0x20)
        self.assertEqual(original_doors(door + door_cell([1])), [])


class MasterHeaderTests(unittest.TestCase):
    def write(self, tmp, data):
        path = Path(tmp) / 'Morrowind.esm'
        path.write_bytes(data)
        return path

    def test_reads_masters_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            info = ki.tes3_master_info(self.write(tmp, tes3(0, ['Morrowind.esm'])))
        self.assertTrue(info['valid'])
        self.assertEqual((info['masters'], info['author'], info['description']), (['Morrowind.esm'], 'author', 'desc'))

    def test_overrun_raises_instead_of_truncating(self):
        data = tes3(0)
        # Grow the header record and end it in a subrecord that claims more bytes than the record holds.
        body = data[16:] + b'MAST' + struct.pack('<I', 99) + b'x\0'
        broken = b'TES3' + struct.pack('<III', len(body), 0, 0) + body
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, broken)
            with self.assertRaises(FormatError):
                ki.tes3_master_info(path)
            verdict = ki.identify('tes3-master', path)
        self.assertFalse(verdict['valid'])
        self.assertIn('overruns', verdict['reason'])

    def test_truncated_subrecord_header_raises(self):
        body = tes3(0)[16:] + b'MAS'
        broken = b'TES3' + struct.pack('<III', len(body), 0, 0) + body
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FormatError):
                ki.tes3_master_info(self.write(tmp, broken))


class MasterListTests(unittest.TestCase):
    def test_one_list_everywhere(self):
        self.assertEqual(content_closure.MASTERS, ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'))
        self.assertEqual(tuple(name for name, kind, _ in ki.GAME_FILES if kind == 'tes3-master'), content_closure.MASTERS)
        self.assertEqual(tuple(name for name, kind, _ in ki.GAME_FILES if kind == 'tes3-archive'), esm.GAME_ARCHIVES)
        self.assertEqual([required for _, _, required in ki.GAME_FILES], [True, True, False, False, False, False])
        self.assertEqual(ki.CORE_NAMES, frozenset(esm.GAME_CONTAINERS))

    def test_expansions_are_game_inputs(self):
        for name in ('Morrowind.esm', 'Tribunal.bsa', 'bloodmoon.ESM'):
            self.assertTrue(paths.is_game_input(name), name)
        self.assertFalse(paths.is_game_input('Morrowind.exe'))
        self.assertFalse(paths.is_game_input('datafiles.zip'))
        self.assertEqual(input_check.REQUIRED_CORE, ('morrowind.esm', 'morrowind.bsa'))


class LockKeyTests(unittest.TestCase):
    def test_equivalent_spellings_share_a_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'a' / 'f.bin'
            target.parent.mkdir()
            target.write_bytes(b'x')
            other = os.path.join(tmp, 'a', '..', 'a', 'f.bin')
            self.assertEqual(ki.lock_key(target), ki.lock_key(other))
            self.assertEqual(ki.lock_key(target), os.path.normcase(os.path.realpath(target)))

    def test_game_files_use_the_ambiguity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / 'Morrowind.esm').write_bytes(tes3(0))
            (data / 'MORROWIND.ESM').write_bytes(tes3(0))
            if len(list(data.iterdir())) < 2:
                self.skipTest('case-insensitive filesystem')
            lock = ki.InputLock(None, mode='off', table={'schema': ki.TABLE_SCHEMA, 'revision': 1, 'entries': [], 'editions': []})
            with self.assertRaises(ValueError) as ctx:
                ki.check_game_data(data, lock)
            self.assertIn('case', str(ctx.exception))


class SortedWalkTests(unittest.TestCase):
    """The input report must not depend on directory listing order."""

    def build(self, root):
        data = Path(root) / 'Data Files'
        for name, body in (('Morrowind.esm', b'x'), ('Morrowind.bsa', b'y')):
            (data).mkdir(exist_ok=True)
            (data / name).write_bytes(body)
        for folder, names in (('Music/Explore', ['b.mp3', 'a.mp3']), ('Sound/Vo', ['z.wav', 'm.wav']),
                              ('Fonts', ['f.fnt']), ('Textures', ['t.dds'])):
            (data / folder).mkdir(parents=True, exist_ok=True)
            for n in names:
                (data / folder / n).write_bytes(b'1')
        return data

    def test_report_is_identical_for_reversed_listings(self):
        real_walk = os.walk

        def reversed_walk(*args, **kwargs):
            for parent, dirs, files in real_walk(*args, **kwargs):
                dirs.reverse()
                files.reverse()
                yield parent, dirs, files

        with tempfile.TemporaryDirectory() as tmp:
            data = self.build(tmp)
            plain = input_check.inspect(data, stage='terrain', allow_differences=True)
            with patch.object(input_check.os, 'walk', reversed_walk):
                flipped = input_check.inspect(data, stage='terrain', allow_differences=True)
        self.assertEqual(json.dumps(plain, sort_keys=False), json.dumps(flipped, sort_keys=False))


class WorkspaceWriterTests(unittest.TestCase):
    def test_workspace_json_is_lf_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'ws'
            paths.init_workspace(work)
            raw = (work / 'workspace.json').read_bytes()
        self.assertNotIn(b'\r', raw)
        self.assertTrue(raw.endswith(b'}\n'))


if __name__ == '__main__':
    unittest.main()
