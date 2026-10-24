# SPDX-License-Identifier: GPL-3.0-only
"""AW-20260928-10: every load door gets its DOOR record's opening and closing sounds (tools/prepare_door_audio.py).

The catalogue was made from the opening scene's links only (id1/scene-doors*.txt): 28 Seyda Neen and prison ship
doors, none of Balmora's 70 door references, so every Balmora door was silent in room maps and CHIM rooms alike.
It now lists every load door of the game data by its reference number, the key every door bank uses (room maps,
CHIM rooms, CHIM frames, town interiors), in the AWSFX2 table the engine reads (engine/aga/src/aw_door_audio.c,
tests/aga_door_audio_test.c)."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_door_audio
from prepare_door_audio import catalogue, scene_links, table


def sub(tag, body):
    return tag + struct.pack('<I', len(body)) + body


def record(tag, body, flags=0):
    return tag + struct.pack('<III', len(body), 0, flags) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def door(name, opening, closing):
    body = sub(b'NAME', z(name)) + sub(b'MODL', z('d/door.nif'))
    if opening:
        body += sub(b'SNAM', z(opening))
    if closing:
        body += sub(b'ANAM', z(closing))
    return record(b'DOOR', body)


def sound(name, path, volume):
    return record(b'SOUN', sub(b'NAME', z(name)) + sub(b'FNAM', z(path)) + sub(b'DATA', bytes((volume, 0, 255))))


def ref(number, base, destination=False, deleted=False):
    body = sub(b'FRMR', struct.pack('<I', number)) + sub(b'NAME', z(base)) + \
        sub(b'DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))
    if destination:
        body += sub(b'DODT', struct.pack('<6f', 1, 2, 3, 0, 0, 0)) + sub(b'DNAM', z('Balmora, Somewhere'))
    if deleted:
        body += sub(b'DELE', b'\0\0\0\0')
    return body


def cell(name, refs, interior=True):
    body = sub(b'NAME', z(name)) + sub(b'DATA', struct.pack('<Iii', 1 if interior else 0, 0, 0)) + b''.join(refs)
    return record(b'CELL', body)


def game():
    return b''.join([
        record(b'TES3', sub(b'HEDR', b'\0' * 300)),
        sound('Door Creaky Open', 'Fx\\object\\Door Creaky Open.wav', 255),
        sound('Door Creaky Close', 'Fx\\object\\Door Creaky Close.wav', 255),
        sound('Door Heavy Open', 'Fx\\object\\Door Heavy Open.wav', 128),
        door('in_hlaalu_door', 'door creaky open', 'door creaky close'),
        door('ex_hlaalu_door', 'Door Creaky Open', 'Door Creaky Close'),
        door('ex_trap_door', 'door heavy open', ''),
        door('in_cabinet_door', 'door creaky open', 'door creaky close'),
        cell('Balmora', [ref(315559, 'ex_hlaalu_door', destination=True), ref(32928, 'ex_trap_door', destination=True),
                         ref(41172, 'in_cabinet_door')], interior=False),
        cell("Balmora, Balyn Omarel's House", [ref(363121, 'in_hlaalu_door', destination=True),
                                               ref(390593, 'in_hlaalu_door', destination=True, deleted=True)]),
        cell('Seyda Neen, Census and Excise Office', [ref(172860, 'in_cabinet_door')]),
    ])


class DoorAudioCatalogue(unittest.TestCase):
    def test_every_load_door_and_the_scene_links_are_listed(self):
        rows = catalogue(game(), {172860})
        self.assertEqual([r['reference'] for r in rows], [32928, 172860, 315559, 363121])
        by_ref = {r['reference']: r for r in rows}
        self.assertEqual([s['id'] for s in by_ref[363121]['sounds']], ['door creaky open', 'door creaky close'])
        self.assertEqual(by_ref[32928]['sounds'][1], None)            # no closing sound in its record
        self.assertAlmostEqual(by_ref[32928]['sounds'][0]['volume'], 128 / 255)
        # a door with no destination is listed only when the scene asks for it; a deleted reference never
        self.assertNotIn(41172, by_ref)
        self.assertNotIn(390593, by_ref)
        # the earlier catalogue: only the scene's links
        self.assertEqual([r['reference'] for r in catalogue(game(), {172860}, load_doors=False)], [172860])

    def test_table_stores_each_pair_once_and_references_in_order(self):
        rows = catalogue(game(), {172860})
        converted = {}
        for row in rows:
            for s in row['sounds']:
                if s:
                    source = s['source'].replace('\\', '/').casefold()
                    converted[source] = {'path': 'doors/d' + ('%016x' % len(converted)) + '.wav', 'seconds': 1.5}
        lines = table(rows, converted)
        self.assertEqual(lines[0], 'AWSFX2')
        pairs = [line for line in lines if line.startswith('p ')]
        refs = [line for line in lines[1 + len(pairs):]]
        self.assertEqual(len(pairs), 2)            # creaky open/close (three doors) and heavy open with no close
        self.assertTrue(all(line.startswith('p ') for line in lines[1:1 + len(pairs)]))   # pairs come first
        self.assertEqual([int(line.split()[0]) for line in refs], [32928, 172860, 315559, 363121])
        # pairs in first-use order: the trap door (heavy open, no close) first, then the creaky doors' pair
        self.assertEqual(refs[0].split()[1], '0')
        self.assertEqual({line.split()[1] for line in refs[1:]}, {'1'})
        self.assertIn(' - ', pairs[0])
        for line in pairs:                          # the engine's row: two paths, two volumes, two durations
            self.assertEqual(len(line.split()), 7)

    def test_scene_links_read_the_placed_reference_banks(self):
        with tempfile.TemporaryDirectory() as temp:
            scene = Path(temp)
            (scene / 'id1').mkdir()
            (scene / 'id1' / 'scene-doors.txt').write_text('AWD3\nseyda census 119513 0 0 0\n\n', encoding='utf-8',
                                                          newline='\n')
            self.assertEqual(scene_links(scene), {119513})
            (scene / 'id1' / 'scene-doors-x.txt').write_text('AWD2\n', encoding='utf-8', newline='\n')
            with self.assertRaises(ValueError):
                scene_links(scene)

    def test_bounds_match_the_engine(self):
        source = (ROOT / 'engine/aga/src/aw_door_audio.c').read_text(encoding='utf-8')
        self.assertIn('#define AW_DOOR_PAIRS %d' % prepare_door_audio.MAX_PAIRS, source)
        self.assertIn('#define AW_DOOR_REFS %d' % prepare_door_audio.MAX_REFERENCES, source)


if __name__ == '__main__':
    unittest.main()
