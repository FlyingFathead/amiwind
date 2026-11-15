# SPDX-License-Identifier: GPL-3.0-only
"""The actor record audit (NPC-CREATURE-COMBAT-STYLE-STATS-66, docs/ACTOR_RECORDS.md "Is it all there: the audit"):
(1) every field gap the world-wide table (docs/actor-record-audit.json, written by tools/actor_record_audit.py from
the game data and a build) shows is a known, tracked one (config/actor-record-gaps.json, each naming its ID), and no
more of it; (2) the audit's comparison on a small synthetic game data set (no game data in the repo): a stored NPC's
fields carried, a changed value counted as different, a missing actor row counted as missing; (3) the builder fix: a
creature with the "weapon and shield" flag equips the weapon and armour its inventory gives (CREATURE-COMBAT-WEAPON-54),
one without it does not, and a bow is never the equipped melee weapon (ACTOR-RANGED-COMBAT-MISSING-66)."""
import json
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

import actor_record_audit as ara  # noqa: E402
from test_actorstate import master_bytes, record, sub, aidt, npco  # noqa: E402

GAPS = ROOT / 'config/actor-record-gaps.json'
TABLE = ROOT / 'docs/actor-record-audit.json'


def wpdt(typ, chop=(2, 10)):
    return struct.pack('<fihhffh6Bi', 10.0, 50, typ, 300, 1.0, 1.0, 0, chop[0], chop[1], 3, 12, 4, 14, 0)


def extra():
    crea = struct.pack('<24i', 2, 3, *([30] * 8), 40, 0, 80, 10, 40, 5, 15, 1, 3, 2, 4, 0, 0, 0)
    return b''.join([
        record('WEAP', sub('NAME', 'test_axe'), sub('WPDT', wpdt(7))),
        record('WEAP', sub('NAME', 'test_bow'), sub('WPDT', wpdt(9))),
        record('ARMO', sub('NAME', 'test_shield'), sub('AODT', struct.pack('<ifiiii', 8, 9.0, 20, 200, 0, 8))),
        # bipedal (1), weapon and shield (4), walks (0x40): an armed skeleton
        record('CREA', sub('NAME', 'armed_skel'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x45)),
               aidt(0, 90, 0, 0), npco(1, 'test_axe'), npco(1, 'test_shield')),
        record('WEAP', sub('NAME', 'test_arrow'), sub('WPDT', wpdt(12, (1, 5)))),
        # a bow without arrows cannot shoot (rated 0); with arrows it is the weapon held
        record('CREA', sub('NAME', 'archer_skel'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x45)),
               aidt(0, 90, 0, 0), npco(1, 'test_bow')),
        record('CREA', sub('NAME', 'bowman_skel'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x45)),
               aidt(0, 90, 0, 0), npco(1, 'test_bow'), npco(20, 'test_arrow')),
        # an axe (chop 2-10, slash 3-12, thrust 4-14) against the bow with arrows: the bow rates higher at the
        # opening (x fAIRangeMeleeWeaponMult / fAIMeleeWeaponMult)
        record('CREA', sub('NAME', 'both_skel'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x45)),
               aidt(0, 90, 0, 0), npco(1, 'test_axe'), npco(1, 'test_bow'), npco(20, 'test_arrow')),
        # no weapon flag: its axe is loot only
        record('CREA', sub('NAME', 'loot_scamp'), sub('NPDT', crea), sub('FLAG', struct.pack('<I', 0x40)),
               aidt(0, 90, 0, 0), npco(1, 'test_axe')),
    ])


class Fixture:
    tmp = None

    @classmethod
    def data(cls):
        if cls.tmp is None:
            import tempfile
            cls.tmp = Path(tempfile.mkdtemp(prefix='aw-actor-audit-'))
            (cls.tmp / 'Morrowind.esm').write_bytes(master_bytes() + extra())
        return cls.tmp


class GapAllowlistTests(unittest.TestCase):
    def test_every_gap_tracked(self):
        table = json.loads(TABLE.read_text(encoding='utf-8'))
        gaps = json.loads(GAPS.read_text(encoding='utf-8'))['gaps']
        self.assertEqual(set(table['fields']), set(ara.FIELDS), 'the table is from another audit version: rerun it')
        for field, counts in table['fields'].items():
            for state in ('missing', 'different'):
                n = counts[state]['records']
                allowed = gaps.get(field, {}).get(state, 0)
                self.assertLessEqual(n, allowed, '%s: %d records %s, %d allowed (config/actor-record-gaps.json): a new '
                                     'gap is registered and fixed, or listed with its ID' % (field, n, state, allowed))
        for field, g in gaps.items():
            self.assertIn(field, ara.FIELDS)
            self.assertRegex(g.get('tracked', ''), r'^[A-Z0-9-]+-\d+$', field + ': names no tracker or register ID')

    def test_stats_all_carried(self):
        table = json.loads(TABLE.read_text(encoding='utf-8'))
        for field in ('level', 'attributes', 'skills', 'health', 'magicka', 'fatigue', 'hello', 'fight', 'flee',
                      'alarm', 'disposition', 'reputation', 'rank', 'gold', 'race', 'class', 'faction', 'spells',
                      'inventory', 'script', 'stats vocabulary', 'creature type', 'attacks', 'soul'):
            c = table['fields'][field]
            self.assertEqual((c['missing']['records'], c['different']['records']), (0, 0), field)


class AuditCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.refs = ara.read_masters(Fixture.data())
        cls.build = {'actors': {}, 'scripts': {}, 'wander': set(), 'vocab': {}, 'hash': lambda s: 0}
        cls.build = ara.fresh_actor_table(Fixture.data(), cls.build)

    def states(self, ident):
        tag = 'NPC_' if ident in self.records['NPC_'] else 'CREA'
        e = ara.expected(tag, self.records[tag][ident], self.records)
        return e, ara.compare(ident, tag, e, self.build)

    def test_creature_with_weapon_flag_equips(self):
        e, s = self.states('armed_skel')
        self.assertEqual(e['weapon'], ['test_axe'])
        self.assertEqual(self.build['actors']['armed_skel']['weapon'], 'test_axe')
        self.assertEqual((s['weapon'], s['armour'], s['weapon and shield flag']), ('carried',) * 3)

    def test_creature_without_flag_keeps_loot(self):
        e, s = self.states('loot_scamp')
        self.assertIsNone(e['weapon'])
        self.assertIsNone(self.build['actors']['loot_scamp']['weapon'])
        self.assertEqual(s['weapon'], 'absent')

    def test_bow_without_arrows_stays_a_gap(self):
        e, s = self.states('archer_skel')
        self.assertEqual((e['weapon'], e['ranged weapon']), (None, ['test_bow']))
        self.assertIsNone(self.build['actors']['archer_skel']['weapon'])
        self.assertEqual(s['ranged weapon'], 'missing')

    def test_bow_with_arrows_is_held(self):
        # ACTOR-RANGED-COMBAT-MISSING-66: the bow is the equipped weapon, its arrows stay in the inventory
        e, s = self.states('bowman_skel')
        self.assertEqual(self.build['actors']['bowman_skel']['weapon'], 'test_bow')
        self.assertEqual(s['ranged weapon'], 'carried')
        self.assertIn(('test_arrow', 20), [(n, c) for n, c, _f, _k, _t in self.build['actors']['bowman_skel']['inventory']])

    def test_opening_rating_prefers_the_bow(self):
        import prepare_combat
        e, s = self.states('both_skel')
        self.assertEqual(self.build['actors']['both_skel']['weapon'], 'test_bow')
        self.assertEqual((s['weapon'], s['ranged weapon']), ('carried', 'carried'))
        # without the ranged choice (the arena fighters, the held models) the axe stays
        npc = self.records['CREA']['both_skel']
        self.assertEqual(prepare_combat.equipment(self.records, npc, 3)[0][1], 'test_axe')
        self.assertEqual(prepare_combat.equipment(self.records, npc, 3, ranged=True)[0][1], 'test_bow')

    def test_missing_and_different_counted(self):
        held = self.build['actors']['fixed_npc']
        _, s = self.states('fixed_npc')
        self.assertEqual(s['level'], 'missing')         # the build dict has no stats here: no row read
        held.update(level=5)
        _, s = self.states('fixed_npc')
        self.assertEqual(s['level'], 'carried')
        held.update(level=6)
        _, s = self.states('fixed_npc')
        self.assertEqual(s['level'], 'different')

    def test_audit_counts(self):
        report = ara.audit(self.records, Counter(), self.build)
        self.assertEqual(report['records'], {'npc': 3, 'creature': 6})
        self.assertEqual(report['fields']['ranged weapon']['missing']['records'], 1)
        self.assertIn('ranged weapon', report['worst'] + [f for f in ara.FIELDS])


class AnimationKindTests(unittest.TestCase):
    """NPC-ATTACK-ANIMS-MISSING-65: the animation kinds of a record from its files' text keys, against the method's."""

    def test_text_keys_and_kinds(self):
        raw = b'\x0b\x00\x00\x00Idle: Start\x00\x00\x15\x00\x00\x00SpellCast: Self Start\x12\x00\x00\x00' \
              b'Attack2: Start\r\nSoundgen: Left\x00WalkForward: Loop Start\x00KnockOut: Start'
        groups = ara.text_key_groups(raw)
        self.assertEqual(groups, {'idle', 'spellcast', 'attack2', 'walkforward', 'knockout'})
        self.assertEqual({ara.anim_kind(g) for g in groups}, {'idle', 'spellcast', 'attack', 'walk', 'knockdown'})
        self.assertIsNone(ara.anim_kind('turnleft'))
        self.assertEqual(ara.anim_kind('bowandarrow'), 'attack bow')

    def test_compare_by_method(self):
        build = {'actors': {}, 'scripts': {}, 'wander': set(), 'vocab': {}, 'hash': lambda s: 0,
                 'anim': {'rat': ('creature library kf', {'idle', 'walk', 'run', 'attack', 'hit', 'death'}),
                          'body': ('corpse', {'death'})}}
        e = dict.fromkeys(ara.FIELDS)
        e.update({'anim knockdown': True, 'anim attack': True, 'anim idle': True, 'anim death': True})
        s = ara.compare('rat', 'CREA', e, build)
        self.assertEqual((s['anim knockdown'], s['anim attack'], s['anim swim']), ('missing', 'carried', 'absent'))
        s = ara.compare('body', 'NPC_', e, build)
        self.assertEqual((s['anim idle'], s['anim death']), ('absent', 'carried'))
        self.assertEqual(ara.compare('ghost', 'CREA', e, build)['anim idle'], 'missing')

    def test_opening_people_carry_every_kind(self):
        table = json.loads(TABLE.read_text(encoding='utf-8'))
        self.assertTrue(table['opening'], 'the census office people are listed')
        for ident, kinds in table['opening'].items():
            self.assertEqual({k for k, v in kinds.items() if v != 'carried'}, set(), ident)


class LibraryItemsTests(unittest.TestCase):
    """NPC-WEAPON-MESH-33: the NPC library's carried items (tools/npc_library.py library_items, held_items_all) never
    touch the game data for an unarmed or dead person, and a failure costs only its own appearance."""

    def test_unarmed_and_dead_need_nothing(self):
        import npc_library
        self.assertEqual(npc_library.library_items('/nonexistent', b'', {'id': 'x'}), (None, {}))
        self.assertEqual(npc_library.library_items('/nonexistent', b'', {'id': 'x', 'initially_dead': True,
                                                                         'carried_parts': {'weapon': {}}}), (None, {}))

    def test_failure_is_reported_per_appearance(self):
        import npc_library
        out = npc_library.held_items_all(['a', 'b'], '/nonexistent', b'',
                                         {'a': {'id': 'a'}, 'b': {'id': 'b', 'carried_parts': {'weapon': {}},
                                                                  'skeleton': 'x', 'weight': 1, 'height': 1}}, jobs=1)
        self.assertEqual(out['a'], ((None, {}), None))
        self.assertEqual(out['b'][0], (None, {}))
        self.assertTrue(out['b'][1])


if __name__ == '__main__':
    unittest.main()
