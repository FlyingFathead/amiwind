# SPDX-License-Identifier: GPL-3.0-only
"""The actors of the CHIM region frames (EXPERIMENTAL, --chim-region-actors on; tools/chim/region_actors.py,
CHIM-EXTERIOR-ACTORS-MISSING-46).

On the CHIM test world (tests/test_chim_format.fixture: one frame at cell 0,0) and a synthetic master: a region
frame places its NPC and creature references at their authored spots with the towns' ground contact; an actor
authored 2,000 units up with a script keeps its spot (the falling wizard case), one 2 units up gets the ordinary
ground contact; levelled creature references are deferred with their reason, never dropped; a frame over the Cache
room is reported; frames without actors and the town frames are the same bytes as without the option. Synthetic
data only."""
import hashlib
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim import frame_map as M  # noqa: E402
from chim import region_actors as RA  # noqa: E402
from chim import regions as R  # noqa: E402
from chim.validate import terrain_height  # noqa: E402
from test_chim_format import fixture  # noqa: E402
from test_chim_frame_map import GROUND, alias  # noqa: E402
from test_chim_regions import awr  # noqa: E402
from test_entity_tracker import cell, record, sub, z  # noqa: E402

FRAME = R.frame_row((0, 0))                  # origin 1024, 1024, 0 (local units)
NPC_SPOT = (10.0, 20.0)                      # on the fixture's terrain, clear of its placements
CRAB_SPOT = (-100.0, -300.0)                 # on the sea floor (the terrain is under the water there)
WIZARD_SPOT = (200.0, -300.0)


def game(local_x, local_y, local_z):
    """Morrowind position of a frame-local point of FRAME."""
    return ((local_x + FRAME['origin'][0]) * 4, (local_y + FRAME['origin'][1]) * 4, (local_z + FRAME['origin'][2]) * 4)


def ground(x, y):
    return terrain_height(GROUND, x, y)


def ref(number, ident, pos, rot_z=0.0, scale=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident))
    out += (sub('XSCL', struct.pack('<f', scale)) if scale else b'')
    return out + sub('DATA', struct.pack('<6f', *pos, 0.0, 0.0, rot_z))


def npc(ident, script=None):
    return record('NPC_', sub('NAME', z(ident)), *([sub('SCRI', z(script))] if script else []))


MASTER = b''.join([
    npc('villager'), npc('falling wizard', 'fallScript'), record('CREA', sub('NAME', z('mudcrab'))),
    record('LEVC', sub('NAME', z('random_crab'))),
    cell('', False, 0, 0, ref(101, 'villager', game(*NPC_SPOT, ground(*NPC_SPOT) + 0.5))      # 2 units up
         + ref(102, 'mudcrab', game(*CRAB_SPOT, ground(*CRAB_SPOT)))
         + ref(103, 'falling wizard', game(*WIZARD_SPOT, ground(*WIZARD_SPOT) + 500.0), 1.0)  # 2,000 units up
         + ref(104, 'random_crab', game(0.0, 0.0, 0.0))
         + ref(105, 'nobody', game(0.0, 0.0, 0.0))),                 # no such record: not an actor reference
    cell('', False, 5, 5, ref(201, 'villager', (5 * 8192 + 100.0, 5 * 8192 + 100.0, 0.0))),
])


def text(ident, model='progs/test.mdl', mode='0', classname='aw_npc'):
    return ''.join('"%s" "%s"\n' % kv for kv in (('aw_source_id', ident), ('aw_ground_mode', mode),
                                                  ('classname', classname), ('model', model), ('netname', ident),
                                                  ('aw_idle_step', '0.1')))


TEXTS = {'villager': text('villager'), 'mudcrab': text('mudcrab'), 'falling wizard': text('falling wizard')}


class RegionActorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-region-actors-')
        root = Path(cls.tmp.name)
        cls.world_dir = root / 'world'
        fixture(cls.world_dir)
        cls.world = M.load(cls.world_dir)
        cls.lib = root / 'library' / 'id1'
        (cls.lib / 'progs').mkdir(parents=True)
        (cls.lib / 'progs/test.mdl').write_bytes(alias())
        cls.census = RA.census(MASTER)
        cls.refs = RA.by_cell(cls.census)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def unit(self, refs=None):
        place, deferred, left = RA.plan_frame(FRAME, refs or self.refs, TEXTS)
        return RA.frame_actors({'frame': FRAME, 'subworld': M.frame_subworld(self.world, (0, 0)), 'place': place,
                                'deferred': deferred, 'left_out': left, 'library_id1': str(self.lib)})

    def test_census_reads_type_script_scale_and_cell(self):
        rows = {r['number']: r for r in self.census}
        self.assertEqual(sorted(rows), [101, 102, 103, 104, 201])
        self.assertEqual((rows[103]['type'], rows[103]['script']), ('NPC_', 'fallScript'))
        self.assertEqual((rows[102]['type'], rows[104]['type']), ('CREA', 'LEVC'))
        self.assertEqual(sorted(self.refs), [(0, 0), (5, 5)])

    def test_a_region_frame_places_its_npc_and_creature(self):
        rows, rec = self.unit()
        by = {int(r['aw_ref']): r for r in rows}
        self.assertEqual(sorted(by), [101, 102, 103])
        self.assertEqual(rec['by_type'], {'NPC_': 2, 'CREA': 1})
        for number in (101, 102):
            row = by[number]
            self.assertEqual(row['aw_ground_mode'], '0')
            self.assertEqual(row['aw_ground_valid'], '1')
            self.assertEqual(row['aw_ground_baked'], row['origin'])
            status = next(a for a in rec['actors'] if a['reference'] == number)
            self.assertEqual(status['status'], 'grounded', status)
            # no relocation: x and y are the reference's, only the height meets the ground
            self.assertEqual(row['origin'].split()[:2], row['aw_authored_origin'].split()[:2])
        # the 2-units-up NPC: x, y kept, its soles put on the ground (the ordinary contact)
        x, y, zz = map(float, by[101]['origin'].split())
        self.assertEqual((x, y), NPC_SPOT)
        self.assertLess(abs(zz - ground(*NPC_SPOT)), 1.0)
        self.assertEqual(by[101]['angles'], '0 -0.00000 0')

    def test_an_actor_authored_far_up_with_a_script_keeps_its_spot(self):
        rows, rec = self.unit()
        wizard = next(r for r in rows if r['aw_ref'] == '103')
        authored = '%.5f %.5f %.5f' % RA.authored_point(next(r for r in self.census if r['number'] == 103), FRAME)
        self.assertEqual(wizard['origin'], authored)                    # exactly the authored spot
        self.assertEqual(wizard['aw_ground_mode'], '1')                 # the engine does not snap it either
        self.assertNotIn('aw_ground_valid', wizard)
        self.assertEqual(wizard['angles'], '0 -57.29578 0')
        status = next(a for a in rec['actors'] if a['reference'] == 103)
        self.assertEqual(status['status'], 'authored off the ground')
        self.assertEqual(status['script'], 'fallScript')
        # the sea is under him there (terrain below the water level 0): his height counts from the water surface
        above = ground(*WIZARD_SPOT) + 500.0 - max(ground(*WIZARD_SPOT), 0.0)
        self.assertAlmostEqual(status['height_above_support'], above, delta=0.5)
        self.assertFalse(status['in_water'])
        summary = RA.summary([rec])
        self.assertEqual(summary['off_the_ground'], 1)
        self.assertEqual([o['id'] for o in summary['off_the_ground_with_script']], ['falling wizard'])

    def test_levelled_creatures_are_deferred_with_their_reason(self):
        _, rec = self.unit()
        self.assertEqual([(d['reference'], d['type']) for d in rec['deferred']], [(104, 'LEVC')])
        self.assertIn('no invented roll', rec['deferred'][0]['reason'])
        self.assertEqual(RA.summary([rec])['deferred'], {'LEVC': 1})

    def test_nothing_is_dropped_silently(self):
        place, deferred, left = RA.plan_frame(FRAME, self.refs, {'villager': TEXTS['villager']}, town_refs={102},
                                              held={101: 'held at a new game'})
        self.assertEqual(place, [])
        reasons = {x['reference']: x['reason'] for x in left}
        self.assertEqual(reasons[101], 'held at a new game')
        self.assertEqual(reasons[102], RA.TOWN_REASON)
        self.assertEqual(reasons[103], RA.NO_MODEL_REASON)
        self.assertEqual([d['reference'] for d in deferred], [104])

    def test_a_frame_over_its_cache_room_is_reported(self):
        rows, rec = self.unit()
        lumps = M.empty_world((-512, -512, -600), (512, 512, 2048))
        lumps[0] = M.entity_text([{'classname': 'worldspawn', '_chim_frame': '0 0'}])
        data = F.brush_image(lumps)[0]
        _, fits = RA.apply(data, rows, rec, self.lib, 'vf0000')
        self.assertTrue(fits['memory']['baseline']['fits'])
        self.assertEqual(fits['over_budget'], [])
        out, over = RA.apply(data, rows, rec, self.lib, 'vf0000', heap_mb=1)      # a 1 MiB heap: no Cache room
        self.assertFalse(over['memory']['baseline']['fits'])
        self.assertIn('baseline', over['over_budget'])
        self.assertEqual(RA.summary([over])['over_budget']['baseline'][0]['frame'], FRAME['id'])
        self.assertEqual(over['placed'], 3)                             # reported, not refused: nothing leaves
        self.assertEqual(sum(1 for e in M.entities(out) if e.get('classname') == 'aw_npc'), 3)

    def test_overlay_changes_only_the_entities(self):
        lumps = M.empty_world((-512, -512, -600), (512, 512, 2048))
        lumps[0] = M.entity_text([{'classname': 'worldspawn', '_chim_frame': '0 0'}])
        data = F.brush_image(lumps)[0]
        rows, _ = self.unit()
        out = RA.overlay(data, rows)
        a, b = F.read_brush_image(data), F.read_brush_image(out)
        self.assertEqual(a[1:], b[1:])
        self.assertEqual(M.entities(out)[1:], rows)

    def test_unit_cache_key_follows_its_inputs(self):
        place, deferred, left = RA.plan_frame(FRAME, self.refs, TEXTS)
        task = {'frame': FRAME, 'subworld': M.frame_subworld(self.world, (0, 0)), 'place': place, 'deferred': deferred,
                'left_out': left, 'library_id1': str(self.lib)}
        key = RA.unit_inputs(task)
        self.assertEqual(key, RA.unit_inputs(dict(task)))
        moved = [[dict(r, position=[r['position'][0] + 4, *r['position'][1:]]), t] for r, t in place]
        self.assertNotEqual(key, RA.unit_inputs(dict(task, place=moved)))

    def test_mode_is_off_unless_asked(self):
        with mock.patch.dict(os.environ, {RA.ENV: ''}):
            self.assertEqual(RA.mode(), 'off')
        self.assertEqual(RA.mode('on'), 'on')
        with self.assertRaises(ValueError):
            RA.mode('maybe')


class RegionFrameMapTests(unittest.TestCase):
    """build_regions with and without actors on the CHIM test world: the actor frame gets its rows, the map of a
    frame without actor references is byte for byte the map made without the option."""
    FIELDS = {'aw_hand_idle': '2.5', 'aw_eye_height': '16.4'}

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='amiwind-region-actor-maps-')
        root = Path(cls.tmp.name)
        cls.world_dir = root / 'world'
        fixture(cls.world_dir)
        cls.world = M.load(cls.world_dir)
        cls.lib = root / 'library' / 'id1'
        (cls.lib / 'progs').mkdir(parents=True)
        (cls.lib / 'progs/test.mdl').write_bytes(alias())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_regions(self, actors):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'world').mkdir()
            (id1 / 'world/regions.awr').write_bytes(awr([(FRAME['origin'], (-1024, -1024, 1024, 1024),
                                                          (-1920, -1920, 1920, 1920))]))
            with mock.patch.object(M, 'stream_enabled', lambda: False), \
                    mock.patch.object(M, 'region_door_rows', lambda *a, **k: []):
                records, _ = M.build_regions(id1, [FRAME], self.world_dir, world=self.world, rows='game-data',
                                             hand_fields=self.FIELDS, actors=actors)
            raw = (id1 / 'maps/vf0000.chim').read_bytes()
            return hashlib.sha256(raw).hexdigest(), M.entities(raw), records[0]

    def actors(self, refs):
        return {'refs': refs, 'texts': TEXTS, 'library_id1': self.lib}

    def test_the_frame_map_carries_its_actors(self):
        plain, _, _ = self.run_regions(None)
        digest, rows, rec = self.run_regions(self.actors(RA.by_cell(RA.census(MASTER))))
        self.assertNotEqual(plain, digest)
        self.assertEqual(sorted(e['aw_ref'] for e in rows if e.get('classname') == 'aw_npc'), ['101', '102', '103'])
        self.assertEqual(rec['actors']['placed'], 3)
        self.assertEqual(rec['entities'], len(rows))

    def test_a_frame_without_actor_references_is_unchanged(self):
        plain, _, rec0 = self.run_regions(None)
        none, _, rec1 = self.run_regions(self.actors({(5, 5): RA.by_cell(RA.census(MASTER))[(5, 5)]}))
        self.assertEqual(plain, none)
        self.assertNotIn('actors', rec1)
        only_levelled = {(0, 0): [r for r in RA.census(MASTER) if r['type'] == 'LEVC']}
        same, _, rec2 = self.run_regions(self.actors(only_levelled))
        self.assertEqual(plain, same)                              # deferred only: recorded, the map unchanged
        self.assertEqual(rec2['actors']['deferred'][0]['reference'], 104)


class TownFramesUnchanged(unittest.TestCase):
    def test_town_frame_code_does_not_reach_the_region_actors(self):
        import inspect
        for function in (M.build, M.build_docks, M.town_unit, M.frame_entities, M.actor_contact):
            self.assertNotIn('region_actors', inspect.getsource(function))
        import chim_town
        self.assertNotIn('region_actors', inspect.getsource(chim_town))

    def test_region_map_key_code_does_not_reach_the_region_actors(self):
        # the region frame map's pass-cache key covers _region_frame_map's code: the actors keep their own unit, so
        # every region frame map keeps its key and a frame without actors its bytes
        import inspect
        for function in (M._region_frame_map, M._region_map_game_data, M._region_map, M.region_inputs):
            self.assertNotIn('actors', inspect.getsource(function))


if __name__ == '__main__':
    unittest.main()
