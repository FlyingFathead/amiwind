# SPDX-License-Identifier: GPL-3.0-only
"""The hinged door table (AW-20260928-12): tools/prepare_door_audio.py writes id1/hinged-doors.txt (AWHD1) for the
engine's ordinary hinged doors (engine/aga/src/aw_hinged_door.c). Synthetic master records only."""
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

from prepare_door_audio import (HINGED_BASES, HINGED_NAME, HINGED_ROWS, HINGED_SOUNDS, hinged_catalogue,  # noqa: E402
                                hinged_text, sample_name)


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


def record(tag, data):
    return tag.encode() + struct.pack('<III', len(data), 0, 0) + data


def z(text):
    return text.encode() + b'\0'


def door(identifier, name, open_sound='', close_sound='', script=''):
    data = sub('NAME', z(identifier)) + sub('MODL', z('d\\x.nif')) + sub('FNAM', z(name))
    if script:
        data += sub('SCRI', z(script))
    if open_sound:
        data += sub('SNAM', z(open_sound))
    if close_sound:
        data += sub('ANAM', z(close_sound))
    return record('DOOR', data)


def sound(identifier, source, volume=255):
    return record('SOUN', sub('NAME', z(identifier)) + sub('FNAM', z(source)) + sub('DATA', bytes((volume, 0, 255))))


def ref(number, identifier, *extra):
    data = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(identifier)) + sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 1.5))
    for tag, value in extra:
        data += sub(tag, value)
    return data


def cell(name, *refs):
    return record('CELL', sub('NAME', z(name)) + sub('DATA', struct.pack('<Iii', 1, 0, 0)) + b''.join(refs))


def master():
    raw = door('in_door', 'Door', 'Door Open', 'Door Close') + door('gate', 'Old Gate', 'Gate Open', '', script='gateScript')
    raw += door('load_door', 'Load', 'Door Open', 'Door Close') + door('unused', 'Unused', 'Missing Sound')
    raw += sound('Door Open', 'Fx\\door_open.wav', 204) + sound('Door Close', 'Fx\\door_close.wav', 102)
    raw += sound('Gate Open', 'Fx\\gate.wav') + sound('LockedDoor', 'Fx\\trans\\lockeddoor.wav')
    raw += cell('Town, Room',
                ref(30, 'in_door'),
                ref(10, 'in_door', ('FLTV', struct.pack('<i', 50))),
                ref(20, 'in_door', ('KNAM', z('key_room')), ('FLTV', struct.pack('<i', 0))),
                ref(40, 'gate', ('TNAM', z('poison'))),
                ref(50, 'load_door', ('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0)), ('DNAM', z('Town'))),
                ref(60, 'in_door', ('DELE', struct.pack('<i', 0))),
                ref(70, 'some_static'))
    return raw


class HingedDoorTable(unittest.TestCase):
    def test_doors_without_destination_with_lock_key_trap_and_script(self):
        bases, rows, sounds = hinged_catalogue(master())
        self.assertEqual([r['reference'] for r in rows], [10, 20, 30, 40])	# load door, deleted, static: out
        self.assertEqual(sorted(bases), ['gate', 'in_door'])			# the unused record's sound is never asked
        by = {r['reference']: r for r in rows}
        self.assertEqual((by[10]['lock'], by[10]['key']), (50, ''))
        self.assertEqual((by[20]['lock'], by[20]['key']), (0, 'key_room'))
        self.assertEqual(by[40]['trap'], 'poison')
        self.assertEqual(by[30]['cell'], 'Town, Room')

    def test_table_text_follows_the_engine_format(self):
        bases, rows, sounds = hinged_catalogue(master())
        asked = []
        text = hinged_text(bases, rows, sounds, lambda source: (asked.append(source) or sample_name(source), 0.75))
        lines = text.splitlines()
        self.assertEqual(lines[0], 'AWHD1')
        self.assertTrue(text.endswith('\n') and '\r' not in text)
        samples = [l for l in lines if l.startswith('W ')]
        records = [l for l in lines if l.startswith('B ')]
        placed = [l for l in lines if l.startswith('D ')]
        # one sample per sound record, converted through the shared namer (door-sounds.txt uses the same names)
        self.assertEqual(sorted(asked), sorted(['Fx\\door_open.wav', 'Fx\\door_close.wav', 'Fx\\gate.wav',
                                                'Fx\\trans\\lockeddoor.wav']))
        for line in samples:
            path, volume, seconds = line.split()[1:]
            self.assertRegex(path, r'^doors/d[0-9a-f]{16}\.wav$')
            self.assertTrue(0 <= float(volume) <= 1 and float(seconds) == .75)
        self.assertIn('W %s 0.800000 0.750000' % sample_name('Fx\\door_open.wav'), lines)
        self.assertIn('W %s 0.400000 0.750000' % sample_name('Fx\\door_close.wav'), lines)
        # records in name order: gate (open only, no close), in_door
        self.assertEqual(records, ['B 0 -1 Old Gate', 'B 1 2 Door'])
        # placed doors ascending: base, lock level, flags (1 locked, 2 key, 4 trap, 8 script)
        self.assertEqual(placed, ['D 10 1 50 1', 'D 20 1 0 3', 'D 30 1 0 0', 'D 40 0 0 12'])
        self.assertEqual(lines[-1], 'L 3')
        # every index a row names exists before it (the engine drops the table otherwise)
        for line in records:
            for value in map(int, line.split()[1:3]):
                self.assertTrue(-1 <= value < len(samples))

    def test_bounds_and_name_length_are_the_engines(self):
        source = (ROOT / 'engine/aga/src/aw_hinged_door.c').read_text(encoding='utf-8')
        defines = dict(re.findall(r'#define (HD_\w+) (\d+)', source))
        self.assertEqual((int(defines['HD_ROWS']), int(defines['HD_BASES']), int(defines['HD_SOUNDS']),
                          int(defines['HD_NAME']) - 1), (HINGED_ROWS, HINGED_BASES, HINGED_SOUNDS, HINGED_NAME))
        raw = door('d', 'A' * 80 + '\x01', 'Door Open') + sound('Door Open', 'a.wav') + cell('Room', ref(1, 'd'))
        bases, rows, sounds = hinged_catalogue(raw)
        line = [l for l in hinged_text(bases, rows, sounds, lambda s: (sample_name(s), 1)).splitlines()
                if l.startswith('B ')][0]
        self.assertEqual(line, 'B 0 -1 ' + 'A' * HINGED_NAME)

    def test_a_missing_authored_sound_stops_the_build(self):
        raw = door('d', 'Door', 'Nowhere') + cell('Room', ref(1, 'd'))
        with self.assertRaises(ValueError):
            hinged_catalogue(raw)

    def test_the_release_ships_the_table(self):
        import json
        features = json.loads((ROOT / 'config/release-features.json').read_text(encoding='utf-8'))
        patterns = [p for f in (features if isinstance(features, list) else features.get('features', []))
                    if 'door-audio' in f.get('steps', []) for p in f.get('patterns', [])]
        self.assertIn('id1/hinged-doors.txt', patterns)


if __name__ == '__main__':
    unittest.main()
