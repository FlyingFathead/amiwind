# SPDX-License-Identifier: GPL-3.0-only
"""HEART-OF-LORKHAN-FOLLOWS-DAGOTH-65: a creature whose record can move by no means (no walk, swim, fly or biped flag)
never moves in AmiWind: the actor table carries the record's movement flags (tools/mwscript/actors.py), the engine's
rule AW_ActorBaseStationary (aw_actorstate.h) reads them, the ambient walk and the combat chase, flee and dodge ask
AW_ActorStationary (aw_ambient.c) first.

Morrowind.esm's creatures that move by no means (CREA FLAG without 0x01, 0x10, 0x20, 0x40; read from the original
data on 13 November 2026): heart_akulakhan (0x08) and the Kwama Queens (0x08 / 0x0A)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from mwscript import actors  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'

# (record id, CREA FLAG) from Morrowind.esm
SAMPLES = {
    'heart_akulakhan': (0x08, True),
    'Kwama Queen': (0x0A, True),
    'kwama queen_shurdan': (0x08, True),
    'dagoth_ur_2': (0x48, False),        # walks
    'skeleton': (0x40D, False),          # bipedal
    'vivec_god': (0x89, False),          # bipedal
    'slaughterfish': (0x10, False),      # swims
    'cliff racer': (0x20, False),        # flies
}


def table_flags(flag):
    """The ACTB flags actors.py writes for a CREA FLAG (the movement bits)."""
    return ((actors.ACTOR_WALKS if flag & 0x40 else 0) | (actors.ACTOR_SWIMS if flag & 0x10 else 0) |
            (actors.ACTOR_FLIES if flag & 0x20 else 0) | (actors.ACTOR_BIPEDAL if flag & 1 else 0))


class StationaryCreatureTests(unittest.TestCase):
    def setUp(self):
        self.header = (SRC / 'aw_actorstate.h').read_text(encoding='utf-8')

    def define(self, name):
        return int(re.search(r'#define %s (\d+)' % name, self.header).group(1))

    def test_engine_bits_match_the_table_writer(self):
        for name in ('WALKS', 'SWIMS', 'FLIES', 'BIPEDAL'):
            self.assertEqual(self.define('AWR_' + name), getattr(actors, 'ACTOR_' + name), name)
        src = (ROOT / 'tools' / 'mwscript' / 'actors.py').read_text(encoding='utf-8')
        for bit, name in ((0x40, 'WALKS'), (0x10, 'SWIMS'), (0x20, 'FLIES'), (1, 'BIPEDAL')):
            self.assertRegex(src, r'ACTOR_%s if flag & %s' % (name, hex(bit) if bit > 1 else '1'))

    def test_rule_names_every_movement_flag(self):
        rule = re.search(r'#define AW_ActorBaseStationary\(kind,flags\) (.*)', self.header).group(1)
        for name in ('AWR_WALKS', 'AWR_SWIMS', 'AWR_FLIES', 'AWR_BIPEDAL'):
            self.assertIn(name, rule)
        self.assertIn('(kind)==1', rule)

    def test_the_original_creatures(self):
        moving = (self.define('AWR_WALKS') | self.define('AWR_SWIMS') | self.define('AWR_FLIES') |
                  self.define('AWR_BIPEDAL'))
        for rid, (flag, still) in SAMPLES.items():
            self.assertEqual(not (table_flags(flag) & moving), still, rid)

    def test_walk_and_chase_ask_first(self):
        amb = (SRC / 'aw_ambient.c').read_text(encoding='utf-8')
        walk = amb.split('static void walk(slot_t *s,float dt) {')[1]
        self.assertLess(walk.index('AW_ActorStationary(s->e)'), walk.index('if(s->manual_walk)'))
        com = (SRC / 'aw_combat.c').read_text(encoding='utf-8')
        self.assertEqual(com.count('AW_ActorStationary(s->e)'), 3)   # chase, flee, dodge
        self.assertLess(com.index('if(AW_ActorStationary(s->e)){'), com.index('A flying fighter (COMBAT-FLYER-FLEES-57)'))


if __name__ == '__main__':
    unittest.main()
