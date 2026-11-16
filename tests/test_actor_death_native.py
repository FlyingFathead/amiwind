# SPDX-License-Identifier: GPL-3.0-only
"""A script's SetHealth 0 kills (MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66).

SetHealth sets the base and the current health (OpenMW 0.51 statsextensions.cpp OpSetDynamic), and a current health
under 1 is death whatever the base (creaturestats.cpp CreatureStats::setDynamic). The engine killed only at 0 or
below, and a script's change only while the base was above 0, so a script's SetHealth 0 left the actor standing (the
end of the main quest: Dagoth Ur fighting at health 0, the dreamer workers alive). The native part runs the actor
record (aw_actorstate.c) on the builder's own actor table and the blow rule (aw_combat_rules.c):
tests/aga_actor_death_test.c. The rest checks the wiring the native test cannot reach: the script's call in
aw_mwhost.c and every other path that decides a death (a spell, its ticks, a fall, a fight's spell hit)."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'
# src before tools (TEST-WORKER-SYSPATH-32, seen again in v0.0.66-dev11): tools/mwad.py would otherwise shadow the src/mwad package for every
# module the discovery imports after this one in the same process
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(name, start):
    text = code(name)
    text = text[text.index(start):]
    return text[:text.index('\n}\n')]


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class DeathNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_actorstate import build
        _, raw, _ = build()
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-actor-death-'))
        (cls.tmp / 'a.awm').write_bytes(raw)
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(SRC),
                                str(ROOT / 'tests/aga_actor_death_test.c'), str(SRC / 'aw_actorstate.c'),
                                str(SRC / 'aw_combat_rules.c'), '-lm', '-o', str(cls.tmp / 'death')],
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(cls.tmp / 'death'), str(cls.tmp / 'a.awm')], capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        cls.out = run.stdout.splitlines()
        cls.line = {l.split()[0]: l for l in cls.out}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_rule(self):
        # under 1 is death (0, 0.5, below 0), 1 is not; a fall only from a living health
        self.assertEqual(self.line['rule'], 'rule 1 1 0 1 fell 1 0 0')

    def test_sethealth_zero_kills_a_living_actor_once(self):
        self.assertIn('rat health 30.00 base 30.00', self.out)
        self.assertEqual(self.line['sethealth0'],
                         'sethealth0 killed 1 dead 1 health 0.00 base 0.00 ondeath 1 0 reports 1')

    def test_a_dead_actor_dies_no_second_time(self):
        self.assertEqual(self.line['again'], 'again killed 0 dead 1 health 0.00 base 0.00 ondeath 0 0 reports 1')
        self.assertIn('rat count 1', self.out)

    def test_an_actor_taken_to_half_dies(self):
        # ModCurrentHealth, SetHealth and ModHealth alike; the health goes to 0 at the death (OpenMW setDynamic)
        self.assertEqual(self.line['modcurrent-half'],
                         'modcurrent-half killed 1 dead 1 health 0.00 base 50.00 ondeath 1 0 reports 2')
        self.assertEqual(self.line['sethealth-half'],
                         'sethealth-half killed 1 dead 1 health 0.00 base 0.50 ondeath 1 0 reports 3')
        self.assertEqual(self.line['modhealth-half'],
                         'modhealth-half killed 1 dead 1 health 0.00 base 0.50 ondeath 1 0 reports 4')

    def test_an_actor_left_at_one_lives(self):
        self.assertEqual(self.line['sethealth-one'],
                         'sethealth-one killed 0 dead 0 health 1.00 base 1.00 ondeath 0 0 reports 4')
        self.assertEqual(self.line['modcurrent-one'],
                         'modcurrent-one killed 0 dead 0 health 1.00 base 50.00 ondeath 0 0 reports 4')

    def test_a_body_with_no_health_dies_no_second_time(self):
        self.assertEqual(self.line['body'], 'body killed 0 dead 0 health 0.00 base 0.00 ondeath 0 0 reports 4')
        self.assertIn('npc count 3 reports 4', self.out)

    def test_a_blow_that_leaves_half_kills(self):
        self.assertEqual(self.line['blow-half'], 'blow-half damage 1.00 dead 1 health 0.00')
        self.assertEqual(self.line['blow-one'], 'blow-one damage 1.00 dead 0 health 1.00')


class DeathWiringTests(unittest.TestCase):
    def test_the_rule_lives_in_one_place(self):
        header = (SRC / 'aw_actorstate.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_ACTOR_HEALTH_DEAD(health) ((health)<1.0f)', header)
        mod = body('aw_actorstate.c', 'void AW_ActorModCurrent(')
        self.assertIn('if(d==0)AW_ActorHealthDeath(a,(a->flags&AWL_DEAD)!=0,before);', mod)
        self.assertNotIn('dyn_base[0]>0', mod)

    def test_a_scripts_health_call_kills_as_a_blow(self):
        host = body('aw_mwhost.c', 'static aw_mwcell_t host_actor(')
        self.assertIn('was_dead=(a->flags&AWL_DEAD)!=0;before=a->dyn_cur[0];', host)
        self.assertIn('if(stat==AWA_HEALTH && a->reference!=AW_ACTOR_PLAYER_REF)script_death(a,e,was_dead,before);', host)
        self.assertNotIn('dyn_base[0]>0', host)
        # the record before the call, the call, the death; then the player's sheet and the fight's sheet
        self.assertLess(host.index('was_dead='), host.index('AW_ActorSetStat(a,stat,v);'))
        self.assertLess(host.index('script_death('), host.index('to_fighter(a,f);'))
        death = body('aw_mwhost.c', 'static void script_death(')
        # the record's death once, then the death a blow gives on a loaded NPC or creature (as aw_fall.c landed)
        self.assertIn('if(!AW_ActorHealthDeath(a,was_dead,before))return;', death)
        self.assertIn('if(is_actor(e) && !AW_CombatSpellHit(e,0,0))AW_CombatTestEngage(e,1);', death)
        raw = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('killed by a script', raw)                 # aw_mwscript_status counts them
        self.assertIn('wanders,script_deaths);}', raw)

    def test_every_path_that_decides_a_death_has_the_rule(self):
        host = code('aw_mwhost.c')
        self.assertEqual(host.count('if(AW_ACTOR_HEALTH_DEAD(a->dyn_cur[0])){AW_EffectsForget('), 2)   # a spell, its ticks
        self.assertNotIn('if(a->dyn_cur[0]<=0){AW_EffectsForget(', host)
        spell = body('aw_combat.c', 'int AW_CombatSpellHit(')
        self.assertIn('int dead=AW_ACTOR_HEALTH_DEAD(health);', spell)
        self.assertIn('s->f.health=!dead && health>0?health:0;', spell)
        self.assertNotIn('if(health<=0)', spell)
        self.assertIn('if(AW_ACTOR_HEALTH_DEAD(v->health)){v->health=0;v->dead=1;v->knocked=0;}',
                      body('aw_combat_rules.c', 'void AW_CombatSwing('))
        landed = body('aw_fall.c', 'static void landed(')
        self.assertIn('if(AW_ACTOR_HEALTH_DEAD(health)){', landed)
        self.assertNotIn('if(health<=0)', landed)


if __name__ == '__main__':
    unittest.main()
