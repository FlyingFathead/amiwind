# SPDX-License-Identifier: GPL-3.0-only
"""The doors of the opening's Census and Excise Office and of CHIM rooms, on the builder's side (AW-20260928-12,
docs/DOOR_MAPPING.md "The worked example").

- The census office is a room map in the default build (tools/prepare_census.py writes id1/maps/census.bsp; the room
  stages that feed the CHIM rooms leave it out), so its doors are func_wall edicts the engine turns.
- Its doors are kept as geometry by the interior converter, and the hinged door table holds the hall door (172860, lock
  level 100: locked until the story unlocks it) and the office's ordinary door (397586, unlocked), as in the game data.
- A CHIM room record keeps every placement's reference, the key of the hinged door table, for the rooms made from
  converted room maps and for batch rooms alike (both go through chim.interior.Store.add_room).
Synthetic records only: the game data is not in the repository."""
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chim import placed as P  # noqa: E402
from chim import interior as I  # noqa: E402
from mwad.interior import omission_reason  # noqa: E402
from prepare_door_audio import LOCKED, hinged_catalogue, hinged_text, sample_name  # noqa: E402
from test_hinged_doors_table import cell, door, ref, sound  # noqa: E402

HALL, OFFICE, EXIT = 172860, 397586, 119665
ACTIVATED = ROOT / 'engine/aga/src/aw_activated.h'


def census_master():
    """The census office's doors as the game data has them (record ids, names, sounds, lock): the hall door
    "chargen door hall" (Door, lock level 100, no key, no script), the office's "in_c_door_arched" (Sturdy Arched
    Door, unlocked) and the load door "chargen door exit" (a destination: not a hinged door)."""
    raw = door('chargen door hall', 'Door', 'Door Latched Two Open', 'Door Latched One Close')
    raw += door('in_c_door_arched', 'Sturdy Arched Door', 'Door Heavy Open', 'Door Heavy Close')
    raw += door('chargen door exit', 'Wooden Door', 'Door Latched One Open', 'Door Latched One Close')
    for name, source in (('Door Latched Two Open', 'Fx\\trans\\drlatch_opn2.wav'),
                         ('Door Latched One Open', 'Fx\\trans\\drlatch_opn.wav'),
                         ('Door Latched One Close', 'Fx\\trans\\drlatch_cls.wav'),
                         ('Door Heavy Open', 'Fx\\trans\\drhvy_opn.wav'), ('Door Heavy Close', 'Fx\\trans\\drhvy_cls.wav'),
                         ('LockedDoor', 'Fx\\trans\\lockeddoor.wav')):
        raw += sound(name, source)
    raw += cell('Seyda Neen, Census and Excise Office',
                ref(HALL, 'chargen door hall', ('FLTV', struct.pack('<i', 100))),
                ref(OFFICE, 'in_c_door_arched'),
                ref(EXIT, 'chargen door exit', ('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0))))
    return raw


class CensusOfficeDoors(unittest.TestCase):
    def test_the_census_office_is_a_room_map_in_the_default_build(self):
        # The default build makes CHIM rooms from the room stages' area-work folders (tools/build.py
        # chim_interior_commands: intro-scene/area-work and the chim-rooms-* stages); the area rooms leave the census
        # office and the prison ship to their own converters (tools/prepare_census.py writes maps/census.bsp).
        build = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        self.assertIn("sources = [run / 'intro-scene' / 'area-work'] + [run / name / 'scene' / 'area-work'", build)
        area = (ROOT / 'tools/prepare_area.py').read_text(encoding='utf-8')
        self.assertIn("s['interior'] and s['map'] not in ('prison','census')", area)
        census = (ROOT / 'tools/prepare_census.py').read_text(encoding='utf-8')
        self.assertIn("target=scene/'id1/maps/census.bsp'", census)
        scenes = json.loads((ROOT / 'config/seyda_area.json').read_text(encoding='utf-8'))
        self.assertIn({'id': 2, 'map': 'census', 'cell': 'Seyda Neen, Census and Excise Office', 'interior': True},
                      scenes['scenes'])

    def test_its_doors_are_kept_as_geometry(self):
        # tools/prepare_census.py selects the office's geometry with mwad.interior.select_geometry: every DOOR placed
        # with a model is kept, so each door is a func_wall edict at its placement's origin and yaw.
        for number, identifier, model in ((HALL, 'chargen door hall', 'd\\In_C_door_wood_square.nif'),
                                          (OFFICE, 'in_c_door_arched', 'd\\In_C_door_arched.nif'),
                                          (EXIT, 'chargen door exit', 'd\\Ex_nord_door_01.NIF')):
            with self.subTest(number=number):
                self.assertIsNone(omission_reason({'number': number, 'id': identifier, 'type': 'DOOR', 'model': model}))

    def test_the_hinged_door_table_holds_the_hall_door_and_the_office_door(self):
        bases, rows, sounds = hinged_catalogue(census_master())
        by = {r['reference']: r for r in rows}
        self.assertEqual(sorted(by), [HALL, OFFICE])                 # the load door has a destination: not hinged
        self.assertEqual((by[HALL]['lock'], by[HALL]['key']), (100, ''))
        self.assertEqual((by[OFFICE]['lock'], by[OFFICE]['key']), (0, ''))
        text = hinged_text(bases, rows, sounds, lambda source: (sample_name(source), 1.0)).splitlines()
        base_names = [line.split(' ', 3)[3] for line in text if line.startswith('B ')]
        d = {int(line.split()[1]): line.split()[2:] for line in text if line.startswith('D ')}
        self.assertEqual(base_names[int(d[HALL][0])], 'Door')
        self.assertEqual(base_names[int(d[OFFICE][0])], 'Sturdy Arched Door')
        self.assertEqual((int(d[HALL][1]), int(d[HALL][2]) & LOCKED), (100, LOCKED))  # locked until the story
        self.assertEqual((int(d[OFFICE][1]), int(d[OFFICE][2]) & LOCKED), (0, 0))
        self.assertTrue(any(line.startswith('L ') for line in text))                   # the locked sound
        samples = [line.split()[1] for line in text if line.startswith('W ')]
        b = [line.split() for line in text if line.startswith('B ')]
        hall = b[int(d[HALL][0])]
        self.assertEqual(samples[int(hall[1])], sample_name('Fx\\trans\\drlatch_opn2.wav'))
        self.assertEqual(samples[int(hall[2])], sample_name('Fx\\trans\\drlatch_cls.wav'))

    def test_the_hall_door_is_the_engines_story_door(self):
        # aw_activated.h names it; aw_opening.c answers the hinged door's story hook for it
        self.assertIn('#define AW_REF_CENSUS_HALL_DOOR %d' % HALL, ACTIVATED.read_text(encoding='ascii'))
        opening = (ROOT / 'engine/aga/src/aw_opening.c').read_text(encoding='utf-8')
        self.assertIn('int AW_OpeningHingedStory(unsigned ref,int event)', opening)
        self.assertIn('case AW_HINGE_STORY_LOCK:return aw_story.hall?0:1;', opening)
        hinged = (ROOT / 'engine/aga/src/aw_hinged_door.c').read_text(encoding='utf-8')
        self.assertIn('static int door_row(unsigned reference){return AW_HingedDoorRow(reference);}', hinged)
        debug = (ROOT / 'engine/aga/src/aw_debug.c').read_text(encoding='utf-8')
        self.assertIn('AW_HingedDoorInit();aw_hinged_story=AW_OpeningHingedStory;', debug)


class RoomRecordDoorReferences(unittest.TestCase):
    def room(self, refs):
        spec = {'variants': [{'name': 'door', 'lo': (-8.0, -40.0, 0.0), 'hi': (8.0, 40.0, 32.0)}], 'textures': {},
                'placements': [{'variant': 0, 'ref': r, 'origin': (10.0 * i, 0.0, 0.0), 'yaw': 90.0 * i}
                               for i, r in enumerate(refs)]}
        return {'room': 'census', 'cell': 'Seyda Neen, Census and Excise Office', 'spec': spec, 'fallbacks': 0,
                'levels': {r: 40 for r in refs}, 'bounds': ((-50.0, -50.0, 0.0), (50.0, 50.0, 40.0))}

    def test_every_placement_keeps_its_reference(self):
        store = I.Store()
        store.model_id = lambda variant, textures: 5          # one stored model; the record is what is checked
        refs = [HALL, OFFICE, EXIT, 4242]
        data, row = store.add_room(self.room(refs))
        placed = I.read_room_record(data)['placements']
        self.assertEqual([p['ref'] for p in placed], refs)
        self.assertEqual([p['pid'] for p in placed], [0, 1, 2, 3])
        self.assertEqual(row['placements'], 4)
        # the engine reads the same field (chim_format.c ChimFormat_Record: the second word)
        at = len(data) - 4 * P.PLACEMENT.size
        self.assertEqual([struct.unpack_from('>I', data, at + i * P.PLACEMENT.size + 4)[0] for i in range(4)], refs)

    def test_batch_rooms_keep_their_doors(self):
        # a batch room's kept placements (tools/chim_room_batches.py placements.json) are every exported reference but
        # the plant sprites; the room record is made from them by the same Store.add_room
        batches = (ROOT / 'tools/chim_room_batches.py').read_text(encoding='utf-8')
        self.assertIn("placements = [r['number'] for r in index['references'] if r['number'] not in skipped]", batches)
        self.assertIn('kept_placements', (ROOT / 'tools/chim/interior.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
