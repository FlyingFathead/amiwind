# SPDX-License-Identifier: GPL-3.0-only
"""The creatures summoning effects call up (SUMMONED-CREATURES-62; tools/chim/actors.py summoned_creatures,
summons_text and build_table SUMMONED; engine aw_mwhost.c summons, aw_effects.c AW_EffectSummon).

A summoning effect calls up the creature its game setting (sMagic...ID) names (rule from OpenMW 0.51
apps/openmw/mwmechanics/summoning.cpp). None of those records is placed or listed, so before v0.0.62 the actor table
had no base for them. Checked on synthetic data: the settings read by effect number (an unknown setting and an empty
one left out); the summons file names only creature records; the table gives each summoned creature a
base with its library text after every other base (the earlier bases, records and lists unchanged), once even when a
list names it too; a creature without a library model gets a base without text; write_table writes the summons file
beside the table, empty when the masters name none.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_entity_tracker import record, sub, z  # noqa: E402
from test_chim_levelled import MASTER, LIBRARY, crea  # noqa: E402


def gmst(name, value):
    return record('GMST', sub('NAME', z(name)), sub('STRV', value.encode('latin1')))


SUMMONED = MASTER + crea('scamp_summon', 'r\\scamp_fetch.nif', 'Scamp') + \
    crea('atronach_flame_summon', 'r\\atronach_fire.nif', 'Flame Atronach') + b''.join([
        gmst('sMagicScampID', 'Scamp_Summon'), gmst('sMagicFlameAtronachID', 'atronach_flame_summon'),
        gmst('sMagicHungerID', 'hunger_summon'),            # no such record in this master
        gmst('sMagicBonelordID', ''), gmst('sMagicSomethingID', 'crab'), gmst('sDone', 'Done')])
SUMMON_LIBRARY = dict(LIBRARY, scamp_summon='"classname" "aw_npc"\n"model" "progs/c_scamp.mdl"\n')


class SummonedCreatureTests(unittest.TestCase):
    def test_settings_by_effect(self):
        from chim import actors as A
        self.assertEqual(A.summoned_creatures(SUMMONED), {102: 'scamp_summon', 112: 'hunger_summon',
                                                          114: 'atronach_flame_summon'})
        self.assertEqual(A.summoned_creatures(MASTER), {})
        self.assertEqual(len(A.SUMMON_EFFECTS), 22)
        self.assertEqual(sorted(A.SUMMON_EFFECTS)[:16], list(range(102, 117)) + [134])
        text = A.summons_text(A.summoned_creatures(SUMMONED), set(A.creature_ids(SUMMONED)))
        self.assertEqual(text, '102 scamp_summon\n114 atronach_flame_summon\n')
        # an id with a space is kept (the base game's golden saint and winged twilight); 108 is the least bonewalker
        self.assertEqual(A.summons_text({113: 'golden saint_summon', 108: 'bonewalker_summon'},
                                        {'golden saint_summon', 'bonewalker_summon'}),
                         '108 bonewalker_summon\n113 golden saint_summon\n')
        self.assertEqual(A.SUMMON_EFFECTS[108], 'sMagicLeastBonewalkerID')

    def test_table_bases_after_the_others(self):
        from chim import actors as A
        refs, lists, creatures = A.exterior_actors(SUMMONED), A.levelled_lists(SUMMONED), A.creature_ids(SUMMONED)
        before, _ = A.build_table(refs, {}, lists, creatures, SUMMON_LIBRARY)
        summoned = A.summoned_creatures(SUMMONED)
        data, rep = A.build_table(refs, {}, lists, creatures, SUMMON_LIBRARY, summoned=summoned.values())
        _, _, recs0, bases0, _ = A.read_table(before)
        _, _, recs, bases, _ = A.read_table(data)
        self.assertEqual(recs, recs0)
        self.assertEqual(bases[:len(bases0)], bases0)
        self.assertEqual(A.read_lists(data), A.read_lists(before))
        new = bases[len(bases0):]
        self.assertEqual([b['hash'] for b in new], [A.fnv('atronach_flame_summon'), A.fnv('scamp_summon')])
        self.assertEqual(new[0]['text'], '')                               # no library model: a base without text
        self.assertIn('c_scamp.mdl', new[1]['text'])
        self.assertEqual(rep['summoned'], {'creatures': 2, 'with_model': 1})
        # a creature a list names already has its base: no second one
        data2, rep2 = A.build_table(refs, {}, lists, creatures, SUMMON_LIBRARY, summoned=['crab'])
        self.assertEqual(len(A.read_table(data2)[3]), len(bases0))
        self.assertEqual(rep2['summoned'], {'creatures': 1, 'with_model': 1})

    def test_write_table_writes_the_summons_file(self):
        from chim import actors as A
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'maps').mkdir()
            for name, raw, want in (('a.esm', SUMMONED, '102 scamp_summon\n114 atronach_flame_summon\n'),
                                    ('b.esm', MASTER, '')):
                (d / name).write_bytes(raw)
                A.write_table(d / 'maps' / A.FILE_NAME, d / name, d / 'maps', library=SUMMON_LIBRARY)
                self.assertEqual((d / 'maps' / A.SUMMONS_FILE).read_text(encoding='ascii'), want)

    def test_engine_reads_the_file(self):
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('"maps/chim-summons.txt"', host)
        self.assertIn('summons_tick()', host)


if __name__ == '__main__':
    unittest.main()
