# SPDX-License-Identifier: GPL-3.0-only
"""The actor spec check (BUILD-ACTOR-SPEC-CHECK-66, tools/actor_spec_check.py): a kind placed short of the original
fails, an out-of-spec actor record fails, a correct set passes; the original's references are counted per area kind
from the cells (interior, exterior, water by the swim-only creatures and lists), deleted references left out; every
allowlisted shortfall names its register entry. With the expansions selected both sides count the same master's
references, and the places the build sets aside on purpose leave both sides, named (BUILD-ACTOR-SPEC-EXPANSIONS-66),
each list of rooms the room batch stage does not make read as its own group, its empty cells included
(BUILD-ACTOR-SPEC-EMPTY-ROOMS-66)."""
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

import actor_spec_check as asc  # noqa: E402
from test_actorstate import record, sub  # noqa: E402

# measured on the v0.0.66-dev1 build (2026_11_13_v0.0.66-dev1_full-v0.0.66-dev1_7130bd0, source before the town join)
DEV1 = {
    'exterior-region': {'CREA': (329, 329), 'LEVC': (4970, 4970), 'NPC_': (531, 531)},
    'exterior-town': {'CREA': (4, 0), 'LEVC': (112, 0), 'NPC_': (35, 35)},
    'interior': {'CREA': (530, 527), 'LEVC': (1270, 1266), 'NPC_': (2477, 2475)},
    'water': {'CREA': (131, 131), 'LEVC': (1236, 1190)},
}
# measured on the v0.0.66-dev2 build with Tribunal and Bloodmoon selected (2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_
# 70a33a5, town join on), as the image step counted it when it stopped: the three masters' room references against
# the base game's levelled points alone (LEVC), and the places the build sets aside counted as missing (NPC_)
DEV2_STOPPED = {
    'interior': {'CREA': (904, 1150), 'LEVC': (1532, 1266), 'NPC_': (2790, 2738)},
}
# the same build counted like for like: the room references each map places, under their own record's kind, and the
# 13 creatures and 50 NPCs of the Tribunal places the room batch stage set aside left out of both sides; Solstheim's
# exterior cells (120 creatures, 860 levelled points, 82 NPCs), which no map holds, left out of both sides too
DEV2 = {
    'exterior-region': {'CREA': (329, 329), 'LEVC': (4974, 4974), 'NPC_': (534, 534)},
    'exterior-town': {'CREA': (4, 4), 'LEVC': (112, 112), 'NPC_': (35, 35)},
    'interior': {'CREA': (891, 888), 'LEVC': (1532, 1528), 'NPC_': (2740, 2738)},
    'water': {'CREA': (131, 131), 'LEVC': (1236, 1236)},
}
# measured on the v0.0.66-dev3 build (2026_11_15_v0.0.66-dev3_full-v0.0.66-dev3-try2_ed4676d, town join on), as the
# image step counted it when it stopped: the room batch stage now lists Mournhold, Royal Palace (one Tribunal NPC, no
# door leads in) under "empty", no longer under "refused", and the check set aside only the two older lists, so that
# NPC counted as missing (BUILD-ACTOR-SPEC-EMPTY-ROOMS-66); with the empty cells set aside the same build passes (the
# creatures are the dev2 numbers plus the 5 of the Sotha Sil rooms, converted since)
DEV3_STOPPED = {'interior': {'CREA': (896, 893), 'LEVC': (1532, 1528), 'NPC_': (2741, 2738)}}
DEV3 = {'interior': {'CREA': (896, 893), 'LEVC': (1532, 1528), 'NPC_': (2740, 2738)}}
TRIBUNAL, BLOODMOON = 1 << 22, 2 << 22       # mwad.masters ADDON_KEY_STRIDE: the expansions' merged numbers
ROOM_GROUPS = {'exterior_like', 'refused', 'empty'}     # the room batch stage's lists of the rooms it does not make


def counts(table):
    return {a: {k: {'original': o, 'placed': p} for k, (o, p) in v.items()} for a, v in table.items()}


def allowlist():
    return json.loads(asc.ALLOWLIST.read_text(encoding='utf-8'))['allow']


def fields(**bad):
    """An audit field table: every field carried, BAD = {field: (missing, different)}."""
    out = {}
    for f in ('level', 'skills', 'health', 'fight', 'weapon', 'ranged weapon'):
        m, d = bad.get(f.replace(' ', '_'), (0, 0))
        out[f] = {'missing': {'records': m, 'examples': ['x']}, 'different': {'records': d, 'examples': ['y']}}
    return out


class PlacementVerdict(unittest.TestCase):
    def test_dev1_fails_on_the_town_creatures(self):
        bad = asc.placement_verdict(counts(DEV1), allowlist())
        self.assertEqual(len(bad), 3, bad)
        self.assertTrue(any('exterior-town CREA: 0 of 4' in b for b in bad))
        self.assertTrue(any('exterior-town LEVC: 0 of 112' in b for b in bad))
        self.assertTrue(any('water LEVC: 1190 of 1236' in b for b in bad))

    def test_a_missing_kind_fails(self):
        t = {a: {k: (o, o) for k, (o, _p) in v.items()} for a, v in DEV1.items()}
        t['water']['CREA'] = (131, 0)        # the slaughterfish gone
        bad = asc.placement_verdict(counts(t), {})
        self.assertEqual(bad, ['placement water CREA: 0 of 131 placed, 131 missing (allowed 0)'])

    def test_complete_set_passes(self):
        t = {a: {k: (o, o) for k, (o, _p) in v.items()} for a, v in DEV1.items()}
        self.assertEqual(asc.placement_verdict(counts(t), {}), [])

    def test_allowlist_names_its_entries(self):
        for key, row in allowlist().items():
            self.assertRegex(key, r'^(interior|exterior-region|exterior-town|water)/(NPC_|CREA|LEVC)$')
            self.assertRegex(row.get('register', ''), r'^[A-Z0-9-]+-\d+$', key)
            self.assertTrue(row.get('why'), key)
            self.assertGreater(row['missing'], 0, key)

    def test_dev2_stopped_on_the_count_and_passes_like_for_like(self):
        bad = asc.placement_verdict(counts(DEV2_STOPPED), allowlist())
        self.assertEqual(bad, ['placement interior LEVC: 1266 of 1532 placed, 266 missing (allowed 4)',
                               'placement interior NPC_: 2738 of 2790 placed, 52 missing (allowed 2)'])
        self.assertEqual(asc.placement_verdict(counts(DEV2), allowlist()), [])

    def test_dev3_stopped_on_the_empty_room_and_passes_with_it_set_aside(self):
        bad = asc.placement_verdict(counts(DEV3_STOPPED), allowlist())
        self.assertEqual(bad, ['placement interior NPC_: 2738 of 2741 placed, 3 missing (allowed 2)'])
        self.assertEqual(asc.placement_verdict(counts(DEV3), allowlist()), [])

    def test_set_aside_groups_name_their_entries(self):
        groups = json.loads(asc.ALLOWLIST.read_text(encoding='utf-8'))['set_aside']
        self.assertEqual(set(groups), ROOM_GROUPS | {'unplanned_exterior'})
        self.assertEqual(groups['empty']['register'], 'ROOM-EMPTY-CELL-66')
        for group, row in groups.items():
            self.assertRegex(row.get('register', ''), r'^[A-Z0-9-]+-\d+$', group)
            self.assertTrue(row.get('why'), group)


class SetAside(unittest.TestCase):
    TAGS = {'fargoth': 'NPC_', 'trib_npc': 'NPC_', 'trib_lev': 'LEVC', 'trib_crab': 'CREA', 'bm_wolf': 'CREA',
            'mudcrab': 'CREA'}

    def test_master_of_the_merged_numbers(self):
        self.assertEqual(asc.master_of(477475), 'Morrowind.esm')
        self.assertEqual(asc.master_of(TRIBUNAL + 5), 'Tribunal.esm')
        self.assertEqual(asc.master_of(BLOODMOON + 7), 'Bloodmoon.esm')

    def test_like_for_like_and_set_aside(self):
        refs = [
            (True, None, 'trib_lev', TRIBUNAL + 1, 'Mournhold, Temple: Shrine'),       # an expansion room's point
            (True, None, 'trib_npc', TRIBUNAL + 2, 'Mournhold, Great Bazaar'),         # exterior-like: set aside
            (True, None, 'fargoth', 10, 'Mournhold, Great Bazaar'),                    # a base game one: missing
            (True, None, 'trib_crab', TRIBUNAL + 3, 'Sotha Sil, Dome of Udok'),        # a refused room: set aside
            (True, None, 'trib_crab', TRIBUNAL + 4, 'Mournhold, Temple: Shrine'),      # not placed, not set aside
            (False, (-24, 22), 'bm_wolf', BLOODMOON + 5, ''),                          # Solstheim: set aside
            (False, (-24, 22), 'mudcrab', 11, ''),                                     # a base game one: counted
            (False, (0, -7), 'mudcrab', 12, ''),
        ]
        rooms = {'mournhold, great bazaar': ('exterior_like', 'waiting'), 'sotha sil, dome of udok': ('refused', 'lava')}
        inside, outside, aside = asc.sort_refs(self.TAGS, refs, {TRIBUNAL + 1}, rooms, {(0, -7)})
        self.assertEqual(inside, {'LEVC': {'original': 1, 'placed': 1}, 'NPC_': {'original': 1, 'placed': 0},
                                  'CREA': {'original': 1, 'placed': 0}})
        self.assertEqual(outside, [((-24, 22), 'mudcrab', 'CREA'), ((0, -7), 'mudcrab', 'CREA')])
        self.assertEqual(aside, {('interior', 'Mournhold, Great Bazaar', 'Tribunal.esm', 'exterior_like'): {'NPC_': 1},
                                 ('interior', 'Sotha Sil, Dome of Udok', 'Tribunal.esm', 'refused'): {'CREA': 1},
                                 ('exterior', None, 'Bloodmoon.esm', 'unplanned_exterior'): {'CREA': 1}})

    def test_an_empty_cell_of_the_game_data_is_set_aside(self):
        # the v0.0.66-dev3 stop: the one NPC of Mournhold, Royal Palace, a cell the room batch stage lists as empty
        refs = [
            (True, None, 'trib_npc', TRIBUNAL + 6, 'Mournhold, Royal Palace'),         # empty: set aside
            (True, None, 'fargoth', 13, 'Mournhold, Royal Palace'),                    # a base game one: missing
        ]
        rooms = {'mournhold, royal palace': ('empty', 'empty in the game data: no placement the room converter keeps '
                                                      '(1 references: NPC_ a shady smuggler); 0 doors lead in')}
        inside, outside, aside = asc.sort_refs(self.TAGS, refs, set(), rooms, None)
        self.assertEqual(inside, {'NPC_': {'original': 1, 'placed': 0}})
        self.assertEqual(outside, [])
        self.assertEqual(aside, {('interior', 'Mournhold, Royal Palace', 'Tribunal.esm', 'empty'): {'NPC_': 1}})

    def test_base_game_alone_sets_nothing_aside(self):
        refs = [(True, None, 'fargoth', 10, 'Seyda Neen, Arrille\'s Tradehouse'), (False, (0, -7), 'mudcrab', 12, '')]
        inside, outside, aside = asc.sort_refs(self.TAGS, refs, {10}, {}, None)
        self.assertEqual((inside, len(outside), aside), ({'NPC_': {'original': 1, 'placed': 1}}, 1, {}))

    def test_rooms_the_batch_stage_did_not_make(self):
        record = {'rooms': [{'room': 'Vor Lair, Interior', 'map': 'ri1'}],
                  'exterior_like': [{'cell': 'Mournhold, Godsreach', 'master': 'Tribunal.esm', 'state': 'waiting'}],
                  'refused': {'Sotha Sil, Dome of Udok': 'ValueError: lava', 'Vor Lair, Interior': 'made later'},
                  'empty': {'Mournhold, Royal Palace': 'empty in the game data (1 references); 0 doors lead in',
                            'Vor Lair, Interior': 'made after all'}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / asc.ROOM_RECORD).write_text(json.dumps(record), encoding='utf-8')
            got = asc.set_aside_rooms(tmp)
        self.assertEqual(got, {'mournhold, godsreach': ('exterior_like', 'waiting'),
                               'sotha sil, dome of udok': ('refused', 'ValueError: lava'),
                               'mournhold, royal palace': ('empty', 'empty in the game data (1 references); 0 doors '
                                                                    'lead in')})
        self.assertEqual(asc.set_aside_rooms(None), {})

    def test_every_room_list_is_a_named_group(self):
        # BUILD-ACTOR-SPEC-EMPTY-ROOMS-66: each list of rooms the room batch stage does not make is read as its own
        # group, and every group the check can set aside under names its register entry in the allowlist file
        record = {'rooms': [], 'exterior_like': [{'cell': 'a', 'state': 'waiting'}], 'refused': {'b': 'error'},
                  'empty': {'c': 'empty in the game data'}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / asc.ROOM_RECORD).write_text(json.dumps(record), encoding='utf-8')
            groups = {group for group, _why in asc.set_aside_rooms(tmp).values()}
        self.assertEqual(groups, ROOM_GROUPS)
        named = json.loads(asc.ALLOWLIST.read_text(encoding='utf-8'))['set_aside']
        self.assertTrue(groups <= set(named), sorted(groups - set(named)))

    def test_room_placements_from_the_tracker(self):
        tracker = {'placed_refs': {'interior:Balmora, Guild of Mages': {'npc': [1, 2], 'creature': [3], 'door': [9]},
                                   'exterior:0,-7': {'creature': [4]}}}
        self.assertEqual(asc.interior_placed(tracker), {1, 2, 3})
        with self.assertRaises(ValueError):
            asc.interior_placed({'totals': {}})

    def test_ranged_gap_counts_the_expansions_records(self):
        # the v0.0.66-dev2 build: 52 records hold a melee weapon where the record gives a ranged one (40 of the base
        # game, 3 of Tribunal, 9 of Bloodmoon); 43 were listed, so the image step stopped
        gaps = json.loads(asc.GAPS.read_text(encoding='utf-8'))['gaps']
        self.assertEqual(asc.record_verdict(fields(ranged_weapon=(7, 52)), gaps), [])
        self.assertTrue(asc.record_verdict(fields(ranged_weapon=(7, 53)), gaps))


class RecordVerdict(unittest.TestCase):
    def test_out_of_spec_record_fails(self):
        bad = asc.record_verdict(fields(health=(0, 1)), {})
        self.assertEqual(len(bad), 1)
        self.assertIn('record health: 1 records different', bad[0])

    def test_wrong_weapon_class_fails(self):
        # a skeleton archer holding its fists, not its bow: the ranged weapon field is missing
        self.assertTrue(asc.record_verdict(fields(ranged_weapon=(1, 0)), {}))

    def test_tracked_gap_and_correct_set_pass(self):
        self.assertEqual(asc.record_verdict(fields(), {}), [])
        gaps = {'ranged weapon': {'missing': 7, 'different': 43}}
        self.assertEqual(asc.record_verdict(fields(ranged_weapon=(7, 43)), gaps), [])
        self.assertTrue(asc.record_verdict(fields(ranged_weapon=(8, 43)), gaps))


def cell(interior, xy, refs):
    flags = 1 if interior else 0
    parts = [sub('NAME', 'room' if interior else ''), sub('DATA', struct.pack('<Iii', flags, *xy))]
    for n, (ident, deleted) in enumerate(refs):
        parts += [sub('FRMR', struct.pack('<I', n + 1)), sub('NAME', ident)]
        if deleted:
            parts.append(sub('DELE', struct.pack('<I', 0)))
    return record('CELL', *parts)


def crea(ident, flag):
    return record('CREA', sub('NAME', ident), sub('FLAG', struct.pack('<I', flag)))


class OriginalCount(unittest.TestCase):
    def test_areas_and_water(self):
        data = b''.join([
            crea('mudcrab', 0x50),            # walks and swims: not water
            crea('slaughterfish', 0x10),      # swims only
            crea('cliff racer', 0x20),
            record('NPC_', sub('NAME', 'fargoth')),
            record('LEVC', sub('NAME', 'h2o_lev'), sub('CNAM', 'slaughterfish'), sub('INTV', struct.pack('<H', 1))),
            record('LEVC', sub('NAME', 'mixed_lev'), sub('CNAM', 'slaughterfish'), sub('INTV', struct.pack('<H', 1)),
                   sub('CNAM', 'mudcrab'), sub('INTV', struct.pack('<H', 1))),
            cell(False, (-2, -9), [('mudcrab', False), ('slaughterfish', False), ('h2o_lev', False),
                                   ('mixed_lev', False), ('fargoth', True), ('a_rock', False)]),
            cell(True, (0, 0), [('fargoth', False), ('cliff racer', False)]),
        ])
        tags, flags, lists, refs = asc.read_original(data)
        water = asc.water_ids(tags, flags, lists)
        self.assertEqual(water, {'slaughterfish', 'h2o_lev'})
        ext = sorted(i for interior, _xy, i in refs if not interior and i in tags)
        self.assertEqual(ext, ['h2o_lev', 'mixed_lev', 'mudcrab', 'slaughterfish'])   # deleted fargoth left out
        self.assertEqual(sorted(i for interior, _xy, i in refs if interior), ['cliff racer', 'fargoth'])
        self.assertEqual({xy for interior, xy, _i in refs if not interior}, {(-2, -9)})


class EnginePlaces(unittest.TestCase):
    """OUTDOOR-CREATURES-REGRESSION-66: an exterior row counts as placed only when the engine can spawn it. The table of
    tests/test_chim_levelled.py: in cell 0 0 the lists all_lev (11) and top_lev (12), the villager (13, no model in its
    library) and the crab (14, a model); in cell 1 0 the list outer (21, a list inside a list) and late (22: only the
    cliff racer, no model, and an unknown id). The check before counted every row of the table as placed."""

    @classmethod
    def setUpClass(cls):
        from chim import actors as A
        import test_chim_levelled as L
        cls.A = A
        data, _ = A.build_table(A.exterior_actors(L.MASTER), {}, A.levelled_lists(L.MASTER), A.creature_ids(L.MASTER),
                                L.LIBRARY)
        _head, _cells, cls.records, cls.bases, _ = A.read_table(data)
        cls.lists = A.read_lists(data)

    def placed(self, settings):
        return {r['key'] for r in self.records
                if asc.engine_places(self.bases[r['base']], self.bases, self.lists, settings)}

    def test_only_what_the_engine_can_spawn(self):
        self.assertEqual(self.placed({'table': True, 'creatures': True}), {11, 12, 14, 21})

    def test_the_table_left_off_places_no_levelled_point(self):
        # the frame maps hold the people and placed creatures, never a levelled point (CHIM-EXTERIOR-ACTORS-MISSING-46)
        self.assertEqual(self.placed({'table': False, 'creatures': True}), {14})

    def test_creatures_off_places_no_creature(self):
        self.assertEqual(self.placed({'table': True, 'creatures': False}), set())

    def test_every_creature_without_its_model(self):
        # the actor library lost the creature models: every creature and levelled point is missing, the check fails
        bare = [dict(b, text='') if b['kind'] == self.A.KINDS['CREA'] else b for b in self.bases]
        got = {r['key'] for r in self.records
               if asc.engine_places(bare[r['base']], bare, self.lists, {'table': True, 'creatures': True})}
        self.assertEqual(got, set())
        t = {a: {k: (o, o) for k, (o, _p) in v.items()} for a, v in DEV2.items()}
        t['exterior-region']['LEVC'] = (4974, 0)
        t['exterior-region']['CREA'] = (329, 0)
        bad = asc.placement_verdict(counts(t), allowlist())
        self.assertEqual(len(bad), 2, bad)

    def test_shipped_settings(self):
        cases = [
            ('', {'table': False, 'creatures': True}),
            ('chim actors table 1\n', {'table': True, 'creatures': True}),
            ('// Actor table\nchim actors table 1\nchim actors table 0\n', {'table': False, 'creatures': True}),
            ('chim actors table on\n', {'table': False, 'creatures': True}),          # the engine's atoi: "on" is 0
            ('chim actors table 1\nchim actors creatures 0\n', {'table': True, 'creatures': False}),
            ('chim actors table 1\ndbg creatures off\n', {'table': True, 'creatures': False}),
            ('chim actors table 1\ndbg creatures maybe\n', {'table': True, 'creatures': True}),
            ('chim actors table 1 // on\n', {'table': True, 'creatures': True}),
        ]
        for text, want in cases:
            with tempfile.TemporaryDirectory() as tmp:
                if text:
                    (Path(tmp) / asc.CONFIG).write_text(text, encoding='latin-1')
                self.assertEqual(asc.engine_settings(tmp), want, text)

    def test_the_builder_writes_the_line_the_check_reads(self):
        # tools/build_aga.py writes "chim actors table 1" into the image's default-game.cfg with the table on
        src = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn("b'chim actors table 1\\n'", src)


class Wiring(unittest.TestCase):
    def test_placement_counts_what_the_engine_spawns(self):
        src = (ROOT / 'tools' / 'actor_spec_check.py').read_text(encoding='utf-8')
        body = src.split('def placement(', 1)[1].split('\ndef ', 1)[0]
        self.assertIn('engine_places(b, bases, lists, settings)', body)
        self.assertIn('settings = engine_settings(id1)', body)

    def test_image_step_runs_it_after_the_census(self):
        src = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        census = src.index('creature_census_stage(boot/')
        spec = src.index('actor_spec_stage(out.parent')
        self.assertLess(census, spec)
        self.assertTrue(re.search(r'if creature_census_partial\(args\) is None:\s+from actor_spec_check', src))


if __name__ == '__main__':
    unittest.main()
