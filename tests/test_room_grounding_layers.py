# SPDX-License-Identifier: GPL-3.0-only
"""The room residents' grounding classes with the expansions (ROOM-BATCH-NPC-GROUNDING-48, v0.0.66-dev2).

The v0.0.66-dev2 build stopped 14 minutes in, at the chim-room-batches stage's own check: 179 residents of the
expansion rooms had no class. The census that writes the classes then refused on a room the stage sets aside, a
Mournhold district flagged "behave like exterior" (INTERIOR-NO-AMBI-66), because it asked the reader for every room of
the list whatever the selected masters. Checked on synthetic masters:
- the census measures the rooms the build converts: with the base game alone only the base batches (no refusal on an
  expansion room), with the expansions the layer batches too, the exterior-like cells set aside and listed by name;
- --write-rooms measures the whole list with every master it names and refuses a master selection that would leave a
  layer out; the base game's references go to config/actor_grounding_rooms.json written exactly as before the
  expansions (so no stage or unit key that names that file moves), the expansions' references (their rooms and the
  ones they add to base-game rooms) to config/actor_grounding_rooms_layers.json with each master's SHA-256 and the
  set-aside cells, and tools/actor_grounding.py reads the two together;
- the build preflight (tools/build_preflight.py room_grounding_problems, run by tools/build.py before any stage) finds
  an unclassified room resident in seconds, passes with the written classes, with the expansions and with the base
  game alone, and leaves the exterior-like cells to the exterior work as the stage does.
"""
import contextlib
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import actor_grounding as G  # noqa: E402
import actor_grounding_census as C  # noqa: E402
import build_preflight  # noqa: E402
import room_batches  # noqa: E402
from mwad import masters as M  # noqa: E402

AMBI = bytes([10, 20, 30, 0, 100, 90, 80, 0, 1, 2, 3, 0]) + struct.pack('<f', 0.5)


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def record(tag, payload):
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def header(*masters):
    payload = sub('HEDR', bytes(300))
    for name in masters:
        payload += sub('MAST', name.encode() + b'\0') + sub('DATA', bytes(8))
    return record('TES3', payload)


def npc(identifier):
    stats = bytearray(52)
    struct.pack_into('<h', stats, 38, 50)
    return record('NPC_', sub('NAME', identifier.encode() + b'\0') + sub('NPDT', bytes(stats)))


def room(name, refs, flags=1, ambi=AMBI):
    payload = sub('NAME', name.encode() + b'\0') + sub('DATA', struct.pack('<Iii', flags, 0, 0))
    if ambi is not None:
        payload += sub('AMBI', ambi)
    for number, identifier in refs:
        payload += sub('FRMR', struct.pack('<I', number)) + sub('NAME', identifier.encode() + b'\0')
        payload += sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))
    return record('CELL', payload)


ROOM_LIST = {'batches': [
    {'batch': 1, 'rooms': [{'room': 'Base Room', 'map': 'rb0001', 'id': 0}]},
    {'batch': 2, 'layer': 'Tribunal.esm', 'rooms': [{'room': 'Mournhold, Plaza', 'map': 'rb0002', 'id': 1},
                                                    {'room': 'Mournhold, Shop', 'map': 'rb0003', 'id': 2}]}]}
SHOP_GUY = M.ADDON_KEY_STRIDE + 2      # the merged number of the Tribunal file's reference 2 (mwad.masters)
VISITOR = M.ADDON_KEY_STRIDE + 3       # Tribunal's reference 3, placed in the base game's room


class LayerRooms(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.data = self.tmp / 'Data Files'
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(header() + npc('base guy') + room('Base Room', [(1, 'base guy')]))
        (self.data / 'Tribunal.esm').write_bytes(
            header('Morrowind.esm') + npc('plaza guy') + npc('shop guy') + npc('visitor')
            + room('Mournhold, Plaza', [(1, 'plaza guy')], flags=1 | 0x80, ambi=None)
            + room('Mournhold, Shop', [(2, 'shop guy')])
            + room('Base Room', [(3, 'visitor')]))      # an expansion's reference in a base-game room
        real = M.master_path
        merged = self.tmp / 'merged'
        for patcher in (mock.patch.object(room_batches, 'load', return_value=json.loads(json.dumps(ROOM_LIST))),
                        # the merged master in the test's folder, never the source tree's out/
                        mock.patch('mwad.masters.master_path',
                                   lambda data, masters=None, merged_dir=None: real(data, masters, merged)),
                        # no models: the rooms place no support, so no archive is read
                        mock.patch('mwad.archives.layered_bsa',
                                   lambda *a, **k: types.SimpleNamespace(entries={}, path='none')),
                        mock.patch.object(G, 'ROOMS', self.tmp / 'no-room-file.json')):
            patcher.start()
            self.addCleanup(patcher.stop)
        C._ROOM_WORKER.clear()

    def census(self, *extra, masters=None):
        env = {k: v for k, v in os.environ.items() if k != M.MASTERS_ENV}
        if masters is not None:
            env[M.MASTERS_ENV] = masters
        report = self.tmp / 'report.json'
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(io.StringIO()) as out:
            code = C.main(['--rooms', '--data-files', str(self.data), '--report', str(report), '--jobs', '1', *extra])
        self.assertEqual(code, 0)
        return json.loads(report.read_text(encoding='utf-8')), out.getvalue()

    def test_base_game_alone_measures_the_base_batches_only(self):
        # 15d93a45: the census asked the base master for every room of the list and refused on the first expansion
        # room ("Interior must resolve uniquely: Mournhold, Plaza")
        report, _ = self.census(masters='')
        self.assertEqual([(r['room'], r['id']) for r in report['rows']], [('Base Room', 'base guy')])
        self.assertEqual(report['summary']['set_aside'], [])
        self.assertEqual(report['summary']['masters'], ['Morrowind.esm'])

    def test_expansions_set_the_exterior_like_district_aside(self):
        report, text = self.census(masters='Morrowind.esm,Tribunal.esm')
        rows = {(r['room'], r['id'], r['reference']) for r in report['rows']}
        self.assertEqual(rows, {('Base Room', 'base guy', 1), ('Base Room', 'visitor', VISITOR),
                                ('Mournhold, Shop', 'shop guy', SHOP_GUY)})
        self.assertEqual([(r['cell'], r['master']) for r in report['summary']['set_aside']],
                         [('Mournhold, Plaza', 'Tribunal.esm')])
        self.assertIn('Set aside, as the room batches stage does: Mournhold, Plaza (Tribunal.esm)', text)
        self.assertEqual(report['summary']['by_layer'], {'Morrowind.esm': {'no_floor': 2},
                                                         'Tribunal.esm': {'no_floor': 1}})
        self.assertEqual(report['summary']['by_reference_owner'], {'Morrowind.esm': 1, 'Tribunal.esm': 2})

    def write_rooms(self, masters=None):
        out = self.tmp / 'rooms.json'
        self.census('--write-rooms', '--rooms-policy', str(out), masters=masters)
        return out

    def test_write_rooms_holds_the_whole_list_with_every_master(self):
        out = self.write_rooms()          # AMIWIND_MASTERS unset: the masters the list names
        base = json.loads(out.read_text(encoding='utf-8'))
        layers = json.loads((self.tmp / 'actor_grounding_rooms_layers.json').read_text(encoding='utf-8'))
        sha = {name: hashlib.sha256((self.data / name).read_bytes()).hexdigest()
               for name in ('Morrowind.esm', 'Tribunal.esm')}
        # the base game's file: its references only, written as before the expansions (no key that names it moves)
        self.assertEqual(base['format'], G.ROOMS_FORMAT)
        self.assertEqual(base['rooms'], {'Base Room': {'no_floor': [[1, 'base guy', '']]}})
        self.assertEqual(base['game_data'], {'Morrowind.esm': sha['Morrowind.esm']})
        self.assertEqual(base['room_list_rooms'], 1)
        self.assertNotIn('set_aside', base)
        self.assertEqual(out.read_text(encoding='utf-8'),
                         C.rooms_text(C.rooms_document([dict(room='Base Room', reference=1, id='base guy',
                                                             **{'class': 'no_floor'})],
                                                       ['Base Room'], sha['Morrowind.esm'])))
        # the expansions' file: the layer rooms and the expansion's reference in the base-game room
        self.assertEqual(layers['format'], G.ROOMS_FORMAT)
        self.assertEqual(layers['rooms'], {'Base Room': {'no_floor': [[VISITOR, 'visitor', '']]},
                                           'Mournhold, Shop': {'no_floor': [[SHOP_GUY, 'shop guy', '']]}})
        self.assertEqual(layers['game_data'], sha)
        self.assertEqual(layers['room_list_rooms'], 2)
        self.assertEqual([row['cell'] for row in layers['set_aside']], ['Mournhold, Plaza'])
        with mock.patch.object(G, 'ROOMS', out):            # both files, read together
            self.assertEqual(G.initial_state('base guy', 1), 'authored')
            self.assertEqual(G.initial_state('shop guy', SHOP_GUY), 'authored')
            self.assertEqual(G.initial_state('visitor', VISITOR), 'authored')
            with self.assertRaises(ValueError):
                G.initial_state('plaza guy', M.ADDON_KEY_STRIDE + 1)     # set aside: no class, never converted

    def test_write_rooms_refuses_a_selection_without_a_layer(self):
        with self.assertRaises(SystemExit) as caught:
            self.write_rooms(masters='Morrowind.esm')
        self.assertIn('leaves out Tribunal.esm', str(caught.exception))
        with self.assertRaises(SystemExit):
            self.census('--write-rooms', '--batches', '1', '--rooms-policy', str(self.tmp / 'x.json'))

    def test_build_preflight_finds_unclassified_residents_in_seconds(self):
        both = ['Morrowind.esm', 'Tribunal.esm']
        with contextlib.redirect_stdout(io.StringIO()):
            problems = build_preflight.room_grounding_problems(self.data, [1, 2], both, log=print)
        self.assertEqual(len(problems), 1)
        self.assertIn('3 resident actors in 2 rooms', problems[0])
        self.assertIn('Mournhold, Shop: shop guy (NPC_ %d)' % SHOP_GUY, problems[0])
        self.assertIn('Base Room: base guy (NPC_ 1), visitor (NPC_ %d)' % VISITOR, problems[0])
        self.assertNotIn('plaza guy', problems[0])                       # set aside, as the stage does
        self.assertIn('tools/actor_grounding_census.py --rooms --data-files DATA --write-rooms', problems[0])
        out = self.write_rooms()
        with mock.patch.object(G, 'ROOMS', out):
            self.assertEqual(build_preflight.room_grounding_problems(self.data, [1, 2], both, log=None), [])
            # the base game alone: its batches only, its classes unchanged
            self.assertEqual(build_preflight.room_grounding_problems(self.data, [1], ['Morrowind.esm'], log=None), [])
        # nothing to check: no room batches, no game data, a selected master missing (the expansion check names it)
        self.assertEqual(build_preflight.room_grounding_problems(self.data, [], both), [])
        self.assertEqual(build_preflight.room_grounding_problems(None, [1, 2], both), [])
        self.assertEqual(build_preflight.room_grounding_problems(self.data, [1], ['Morrowind.esm', 'Bloodmoon.esm']),
                         [])

    def test_the_build_runs_it_before_any_stage(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        check = text.index('build_preflight.room_grounding_problems(')
        self.assertLess(text.index('build_preflight.run(args.workspace'), check)
        self.assertLess(check, text.index("raise ValueError('Build preflight failed before any stage:"))
        self.assertIn('room_batch_selection(args)', text[check:check + 400])
        self.assertIn('master_list(expansion_selection(args))', text[check:check + 400])


if __name__ == '__main__':
    unittest.main()
