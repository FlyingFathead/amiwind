# SPDX-License-Identifier: GPL-3.0-only
"""The creatures placed in rooms (TOMB-NO-CREATURES-61; tools/chim/actors.py room_placed_creatures and placed_lists,
tools/room_levelled.py, tools/actor_library.py plan).

Before v0.0.62 a room placed only the creatures config/interior_creatures.json lists (Vivec, Dagoth Ur, the Heart):
the census of the v0.0.61 image found 4 of the 533 creature references of the base game's rooms placed. Now every
creature placed in a room gets a list of one in the actor table (after the real lists, so their indices and bases are
as before), a model in the actor library and an aw_levelled entity in its room map, which the engine spawns from the
creature's table base through its levelled path (no engine change). Checked on synthetic data: the room creatures
(the listed ones and those of exterior cells left out; off gives none); the table's lists and bases with them; the
roll of a placed list at every level and seed gives its creature; the entities written for levelled and placed
references, not for a reference the map already holds nor a listed creature; each mode alone; the residents report
loses the written rows; the actor library plans the room creatures' models (a dead one: its corpse).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_entity_tracker import cell  # noqa: E402
from test_chim_actor_table import ref  # noqa: E402
from test_chim_levelled import MASTER, LIBRARY, crea  # noqa: E402
from test_room_levelled import room_map, entity_text  # noqa: E402

# the levelled master plus a tomb that places a crab, a dead rat, Vivec (listed: the resident stage's) and a levelled
# list, and an exterior crab that stays the exterior's
TOMB = MASTER + crea('vivec_god', 'r\\lordvivec.nif', 'Vivec') + cell(
    'Some Tomb', True, refs=ref(41, 'crab', (400.0, -800.0, 16.0), 0.25) + ref(42, 'dead_rat') + ref(43, 'vivec_god')
    + ref(44, 'unused') + ref(45, 'crab', deleted=True))


def tomb_refs():
    return [
        {'number': 41, 'id': 'crab', 'type': 'CREA', 'position': [400.0, -800.0, 16.0],
         'rotation_radians': [0, 0, 0.25], 'scale': 1.0},
        {'number': 42, 'id': 'dead_rat', 'type': 'CREA', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
         'scale': 1.0},
        {'number': 43, 'id': 'vivec_god', 'type': 'CREA', 'position': [0.0, 0.0, 0.0],
         'rotation_radians': [0, 0, 0], 'scale': 1.0},
        {'number': 44, 'id': 'unused', 'type': 'LEVC', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
         'scale': 1.0},
        {'number': 46, 'id': 'crab', 'type': 'CREA', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
         'scale': 1.2},
    ]


class RoomPlacedCreatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.master = self.dir / 'Morrowind.esm'
        self.master.write_bytes(TOMB)
        for env in ('AMIWIND_ROOM_LEVELLED', 'AMIWIND_ROOM_PLACED'):
            os.environ.pop(env, None)
        import room_levelled
        room_levelled._orders.clear()

    def tearDown(self):
        for env in ('AMIWIND_ROOM_LEVELLED', 'AMIWIND_ROOM_PLACED'):
            os.environ.pop(env, None)
        self.tmp.cleanup()

    def test_room_creatures(self):
        from chim import actors as A
        self.assertEqual(A.room_placed_creatures(TOMB), ['crab', 'dead_rat'])     # vivec_god: the resident stage's
        self.assertEqual(A.room_placed_creatures(TOMB, exclude=()), ['crab', 'dead_rat', 'vivec_god'])
        self.assertEqual(A.room_placed_creatures(MASTER), [])                     # no creature in its cave
        os.environ['AMIWIND_ROOM_PLACED'] = 'off'
        self.assertEqual(A.room_placed_creatures(TOMB), [])
        self.assertEqual(A.master_tables(self.master)[5], [])

    def test_table_lists_after_the_real_ones(self):
        from chim import actors as A
        refs, lists, creatures = A.exterior_actors(TOMB), A.levelled_lists(TOMB), A.creature_ids(TOMB)
        roots, placed = A.room_levelled_roots(TOMB), A.room_placed_creatures(TOMB)
        before, rep0 = A.build_table(refs, {}, lists, creatures, LIBRARY, room_roots=roots)
        data, rep = A.build_table(refs, {}, lists, creatures, LIBRARY, room_roots=roots, placed=placed)
        order = A.table_list_order(lists, refs, roots, placed)
        self.assertEqual(order[-2:], [(A.PLACED, 'crab'), (A.PLACED, 'dead_rat')])
        self.assertEqual(rep['levelled']['placed_lists'], 2)
        old_lists, new_lists = A.read_lists(before), A.read_lists(data)
        self.assertEqual(new_lists[:len(old_lists)], old_lists)        # the real lists and their targets as before
        _, _, recs0, bases0, _ = A.read_table(before)
        _, _, recs, bases, _ = A.read_table(data)
        self.assertEqual(recs, recs0)
        self.assertEqual(bases[:len(bases0)], bases0)                   # the earlier bases keep their indices
        crab_list = new_lists[order.index((A.PLACED, 'crab'))]
        self.assertEqual((crab_list[0], crab_list[1] & A.ALL_LEVELS, len(crab_list[2])), (0, A.ALL_LEVELS, 1))
        self.assertIn('c_crab.mdl', bases[crab_list[2][0][1]]['text'])
        rat_list = new_lists[order.index((A.PLACED, 'dead_rat'))]
        self.assertEqual(bases[rat_list[2][0][1]]['text'], '')          # no library model for it here: no text

    def test_roll_always_gives_the_creature(self):
        from chim import actors as A
        refs, lists, creatures = A.exterior_actors(TOMB), A.levelled_lists(TOMB), A.creature_ids(TOMB)
        roots, placed = A.room_levelled_roots(TOMB), A.room_placed_creatures(TOMB)
        data, _ = A.build_table(refs, {}, lists, creatures, LIBRARY, room_roots=roots, placed=placed)
        table_lists = A.read_lists(data)
        index = A.table_list_order(lists, refs, roots, placed).index((A.PLACED, 'crab'))
        target = table_lists[index][2][0][1]
        for level in range(1, 41):
            for seed in range(25):
                self.assertEqual(A.levelled_pick(table_lists, index, level, A.rng_seed(41, seed))[0], target)

    def test_write_levelled_and_placed(self):
        import room_levelled as R
        from chim import actors as A
        maps = self.dir / 'maps'
        maps.mkdir()
        keep = '{\n"classname" "worldspawn"\n}\n{\n"classname" "aw_npc"\n"aw_ref" "43"\n"aw_source_id" "vivec_god"\n}\n'
        (maps / 'ri_tomb.bsp').write_bytes(room_map(keep))
        rooms = {'ri_tomb': {'refs': tomb_refs()}}
        report = R.write(maps, rooms, self.master)
        self.assertEqual((report['mode'], report['placed_mode'], report['placed'], report['creatures']),
                         ('table', 'table', 1, 2))
        text = entity_text((maps / 'ri_tomb.bsp').read_bytes())
        self.assertTrue(text.startswith(keep.rstrip('\n')))
        self.assertEqual(text.count('"classname" "aw_levelled"'), 3)
        index = R.list_index(self.master)
        self.assertIn('"aw_ref" "41"\n"sounds" "%d"' % index[(A.PLACED, 'crab')], text)
        self.assertIn('"origin" "100.00000 -200.00000 4.00000"', text)
        self.assertIn('"aw_source_id" "dead_rat"', text)
        self.assertEqual(text.count('"aw_ref" "43"'), 1)                # Vivec: the resident's row only
        self.assertEqual([(r['reference'], r['reason']) for r in report['left_out']],
                         [(46, R.REASON_SCALED_CREATURE)])
        left = [{'map': 'ri_tomb', 'reference': n, 'type': t} for n, t in ((41, 'CREA'), (42, 'CREA'), (43, 'CREA'),
                                                                            (44, 'LEVC'), (46, 'CREA'))]
        self.assertEqual([r['reference'] for r in R.drop_placed(left, report['maps'], rooms, index)], [43, 46])

    def test_each_mode_alone(self):
        import room_levelled as R
        for env, want in (('AMIWIND_ROOM_PLACED', (1, 0)), ('AMIWIND_ROOM_LEVELLED', (0, 2))):
            for e in ('AMIWIND_ROOM_LEVELLED', 'AMIWIND_ROOM_PLACED'):
                os.environ.pop(e, None)
            os.environ[env] = 'off'
            R._orders.clear()
            maps = self.dir / ('maps-' + env)
            maps.mkdir()
            (maps / 'ri_tomb.bsp').write_bytes(room_map('{\n"classname" "worldspawn"\n}\n'))
            report = R.write(maps, {'ri_tomb': {'refs': tomb_refs()}}, self.master)
            self.assertEqual((report['placed'], report['creatures']), want, env)
        os.environ['AMIWIND_ROOM_LEVELLED'] = 'off'
        os.environ['AMIWIND_ROOM_PLACED'] = 'off'
        raw = room_map('{\n"classname" "worldspawn"\n}\n')
        (self.dir / 'ri_tomb.bsp').write_bytes(raw)
        report = R.write(self.dir, {'ri_tomb': {'refs': tomb_refs()}}, self.master)
        self.assertEqual((report['placed'], report['creatures'], (self.dir / 'ri_tomb.bsp').read_bytes()), (0, 0, raw))
        os.environ['AMIWIND_ROOM_PLACED'] = 'sometimes'
        with self.assertRaises(ValueError):
            R.placed_mode()

    def test_actor_library_plans_the_room_creatures(self):
        import actor_library
        meshes, _bipedal, _scales, _npcs, _planned, corpses = actor_library.plan(TOMB)
        self.assertIn('crab', meshes['r/mudcrab.nif'])
        self.assertIn('dead_rat', corpses['r/rust rat.nif'])
        self.assertNotIn('r/lordvivec.nif', meshes)                      # the resident stage bakes Vivec
        os.environ['AMIWIND_ROOM_PLACED'] = 'off'
        _, _, _, _, _, corpses = actor_library.plan(TOMB)
        self.assertNotIn('r/rust rat.nif', corpses)

    def test_actors_a_script_places(self):
        # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): a creature a script places with no reference of its own gets a library
        # model and a table base with its text, after the bases the rest made (their indices as before); an id no
        # actor record has is left out; a commented-out call does not count
        import struct
        import actor_library
        from chim import actors as A

        def sub(tag, data):
            return tag.encode() + struct.pack('<I', len(data)) + data

        def rec(tag, *subs):
            body = b''.join(subs)
            return tag.encode() + struct.pack('<III', len(body), 0, 0) + body
        text = b'Begin Summoner\nPlaceAtPC "scamp_one", 1, 128, 1\n;PlaceAtPC crab 1 1 1\nPlaceItem no_such 1 2 3 0\nEnd'
        master = TOMB + crea('scamp_one', 'r\\scamp.nif', 'Scamp') + rec('SCPT', sub('SCHD', b'Summoner'.ljust(52, b'\0')),
                                                                         sub('SCTX', text))
        self.assertEqual(A.script_placed_actors(master), {'NPC_': [], 'CREA': ['scamp_one']})
        meshes = actor_library.plan(master)[0]
        self.assertIn('scamp_one', meshes['r/scamp.nif'])
        refs, lists, creatures = A.exterior_actors(master), A.levelled_lists(master), A.creature_ids(master)
        library = dict(LIBRARY, scamp_one='"classname" "aw_creature"\n"model" "progs/c_scamp.mdl"\n')
        before, _ = A.build_table(refs, {}, lists, creatures, library)
        data, rep = A.build_table(refs, {}, lists, creatures, library, script_placed=[('scamp_one', 'CREA')])
        _, _, _, bases0, _ = A.read_table(before)
        _, _, _, bases, _ = A.read_table(data)
        self.assertEqual(rep['script_placed_bases'], 1)
        self.assertEqual(bases[:len(bases0)], bases0)
        self.assertIn('c_scamp.mdl', bases[-1]['text'])
        self.assertEqual(A.master_tables(self.master)[6], [])           # the tomb's master has no placing script

    def test_build_options(self):
        build = (ROOT / 'tools/build.py').read_text()
        self.assertIn("os.environ['AMIWIND_ROOM_PLACED']", build)
        self.assertIn('"room_placed_creatures"', build)


if __name__ == '__main__':
    unittest.main()
