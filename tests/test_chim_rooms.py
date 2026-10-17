# SPDX-License-Identifier: GPL-3.0-only
"""The listed rooms of a CHIM-native town (tools/chim_rooms.py, stage chim-rooms-TOWN; BUILD-MINIWIND-ARENA-PIT-
REFUSED-36): which towns get the stage, where it sits in the plan, what the image installs, and the refusals."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import chim_rooms  # noqa: E402

TOOLS = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
RUN = Path('/private/run')


def output(root, files, town='vivec_arena'):
    """A chim-rooms output folder with FILES {id1-relative path: bytes}."""
    for rel, data in files.items():
        path = root / 'id1' / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    record = {'format': chim_rooms.FORMAT, 'town': town, 'map': town, 'door_file': 'vivec_arena-doors.txt',
              'rooms': [{'map': 'vai000', 'cell': 'Vivec, Arena Pit'}], 'excluded': {},
              'files': {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}}
    (root / chim_rooms.RECORD).write_text(json.dumps(record), encoding='utf-8')
    return root


class Rooms(unittest.TestCase):
    def test_which_towns_list_rooms(self):
        self.assertEqual([r['map'] for r in chim_rooms.listed_rooms('vivec_arena')], ['vai000'])
        self.assertTrue(chim_rooms.has_rooms('vivec_arena'))
        self.assertFalse(chim_rooms.has_rooms('bcoast_x7y2'))
        self.assertFalse(chim_rooms.has_rooms('no-such-town'))
        # excluded rooms are not converted (vivec_foreign lists Guild of Mages with an exclusion)
        self.assertNotIn('vqi013', [r['map'] for r in chim_rooms.listed_rooms('vivec_foreign')])

    def plan(self, *argv):
        args = build.parser().parse_args(list(argv))
        args.data_files, args.sdk, args.workspace = Path('/owned'), Path('/sdk'), Path('/private/ws')
        import build_font_options as options
        args.builder_options = options.resolve_builder(args)
        with patch('build_jobs.auto_jobs', return_value=4), contextlib.redirect_stdout(io.StringIO()):
            return build.commands(args, TOOLS, RUN)

    def test_a_chim_native_town_with_rooms_gets_the_stage_after_its_chim_town(self):
        steps = self.plan('--chim-area', 'balmora', '--chim-area', 'seyda', '--chim-area', 'vivec_arena',
                          '--extra-town', 'vivec_arena')
        names = [name for name, _ in steps]
        self.assertIn('chim-rooms-vivec_arena', names)
        self.assertEqual(names.index('chim-rooms-vivec_arena'), names.index('chim-town-vivec_arena') + 1)
        self.assertNotIn('town-vivec_arena', names)  # no legacy region maps (rule 1)
        self.assertNotIn('chim-rooms-balmora', names)  # Balmora's rooms keep balmora-interiors
        command = dict(steps)['chim-rooms-vivec_arena']
        for option in ('--qbsp', '--vis', '--light', '--chim-world', '--scene'):
            self.assertIn(option, command)
        image = dict(steps)['image']
        self.assertEqual(image[image.index('--chim-rooms') + 1], str(RUN / 'chim-rooms-vivec_arena'))
        # the image waits for the rooms it installs (BUILD-CHIM-ROOMS-IMAGE-RACE-36)
        import build_parallel
        self.assertIn('chim-rooms-vivec_arena', build_parallel.stage_dependencies(steps)['image'])

    def test_the_whole_city_takes_the_district_rooms_and_the_image_waits(self):
        steps = self.plan('--chim-area', 'balmora', '--chim-area', 'seyda', '--chim-area', 'vivec_city')
        import build_parallel
        self.assertIn('chim-rooms-vivec_city', [name for name, _ in steps])
        deps = build_parallel.stage_dependencies(steps)
        self.assertIn('chim-rooms-vivec_city', deps['image'])
        # 130 rooms on 16 October 2026; v0.0.42 plan 2.1: six rooms listed again after same-lit sharing and plant
        # sprites, the Redoran Temple Shrine recentred, Arena Waistworks listed (recentred): 138; the four Arena rooms
        # behind Arena Waistworks (Canalworks, Fighters Quarters, Fighters Training, Holding Cells): 142; Telvanni Tower
        # excluded again on 17 October (257 model precaches > 256, VIVEC-ROOM-PRECACHE-LIMIT-42): 141
        self.assertEqual(len(chim_rooms.listed_rooms('vivec_city')), 141)

    def test_the_default_build_makes_the_whole_city_rooms_and_no_other_room_stage(self):
        # all of Vivec in one CHIM frame is the default area (project decision 2026-10-11 09:55): its 130 rooms, the
        # Arena Pit among them, in one room stage
        steps = self.plan()
        rooms = [name for name, _ in steps if name.startswith('chim-rooms-')]
        self.assertEqual(rooms, ['chim-rooms-vivec_city'])
        self.assertIn('vai000', [r['map'] for r in chim_rooms.listed_rooms('vivec_city')])
        self.assertIn('--chim-rooms', dict(steps)['image'])
        balmora_only = self.plan('--chim-area', 'balmora', '--chim-area', 'seyda')
        self.assertFalse([name for name, _ in balmora_only if name.startswith('chim-rooms-')])
        self.assertNotIn('--chim-rooms', dict(balmora_only)['image'])

    def test_install_copies_the_rooms_and_refuses_other_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            rooms = output(tmp / 'rooms', {'maps/vai000.bsp': b'room', 'doors-vai000.txt': b'AWD3\n',
                                           'vivec_arena-doors.txt': b'AWD3\nlinked\n'})
            id1 = tmp / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            record = chim_rooms.install(rooms, id1)
            self.assertEqual((record['rooms'], record['files']), (['vai000'], 3))
            self.assertEqual((id1 / 'maps/vai000.bsp').read_bytes(), b'room')
            self.assertEqual(chim_rooms.install(rooms, id1)['files'], 3)  # the same bytes again: the same files
            (id1 / 'maps/vai000.bsp').write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'maps/vai000.bsp: staged in the image with other bytes'):
                chim_rooms.install(rooms, id1)
            (rooms / 'id1/maps/vai000.bsp').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'changed since the stage wrote it'):
                chim_rooms.install(rooms, tmp / 'fresh')

    def test_the_town_bank_of_the_rooms_wins_over_chim_towns(self):
        # chim_town.install keeps a door bank already in the image (the rooms' linked one)
        import chim_town
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            town = tmp / 'town'
            (town / 'id1').mkdir(parents=True)
            (town / 'door-bank.txt').write_text('AWD3\nunlinked\n', encoding='cp1252')
            (town / 'entities.json').write_text(json.dumps({'format': chim_town.FORMAT, 'town': 'vivec_arena',
                                                            'door_file': 'vivec_arena-doors.txt'}), encoding='utf-8')
            id1 = tmp / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            chim_rooms.install(output(tmp / 'rooms', {'vivec_arena-doors.txt': b'AWD3\nlinked\n'}), id1)
            with patch.object(chim_town, 'collisions', return_value=[]):
                record = chim_town.install(town, id1)
            self.assertEqual(record['door_bank'], 'converted interiors stage')
            self.assertEqual((id1 / 'vivec_arena-doors.txt').read_bytes(), b'AWD3\nlinked\n')

    def test_not_a_rooms_output_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / chim_rooms.RECORD).write_text('{"format": "other"}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Not a CHIM rooms output'):
                chim_rooms.install(tmp, Path(tmp) / 'id1')

    def test_seyda_and_towns_without_rooms_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'Seyda Neen'):
            chim_rooms.prepare('seyda', '/owned', '/scene', '/chim', '/out', 'q', 'v', 'l')


if __name__ == '__main__':
    unittest.main()
