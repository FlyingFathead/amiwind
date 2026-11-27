# SPDX-License-Identifier: GPL-3.0-only
"""ACTOR-ATTACK-ONE-CLOCK-69: a fighter's swing or shot runs on the clock of the group it is seen to play.

What was wrong: every swing of an NPC or creature ran on one engine attack group of its model layout (a person's
hand-to-hand chop: 8 table frames, about 1 s, the blow at 0.714 of it), while the animation pick showed the weapon's
own group (one-handed, two-handed, two-wide, hand-to-hand, bow, crossbow, thrown; chop, slash or thrust) stretched
onto that clock. So the blow landed off the shown hit key (a one-handed thrust two frames past it, a crossbow bolt six
frames late), and every class and type took the same time. What is right now (the original's rule, OpenMW 0.53
character.cpp, read, not copied: the weapon group's sections at their own key times scaled by the weapon's speed,
the damage at the group's hit key, a shot at its release key): at the start of a swing the fight asks the pick for
the span it will show (the same state, rules and key lookup), takes that span's time over the weapon's speed and
lands the blow at its hit key's share; the pick shows that span by the fight's own clock. An actor without such a
span (a baked model, a creature's own attacks) keeps its layout's clock as before. A hit recovery the same way: it
lasted hit1's length whatever hitN was shown; now the kit rolls the hitN when the blow lands (the send keeps that roll)
and the recovery lasts that group's own span, shown by the fight's clock (OpenMW 0.53 refreshHitRecoilAnims). The
AmiWind miss style (aw_combat_miss 1, the default) is kept: the fixture proves a miss still plays the block or dodge.

Natively: tests/aga_attack_clock_test.c (the real key times of base_anim.nif, 15 attacks: the old clock was off the
hit frame for 11, now none is) and the fight's side in tests/aga_combat_test.c (run by tests/test_combat.py: a swing
asks once, lasts the table's time over the speed, strikes at its share). Here the wiring, by the source."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))
sys.path.insert(2, str(Path(__file__).resolve().parent))

import test_aga_native_source as native  # noqa: E402

UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class AttackClockNativeTests(unittest.TestCase):
    def test_every_weapon_group_and_type_lands_on_its_own_hit_frame(self):
        native.NativeSourceTests().compile_run('aga_attack_clock_test.c', [SRC / 'aw_animkit_rules.c', SRC / 'aw_anim.c'],
                                               defines=['AW_ANIM_HOST_TEST'], cflags=UBSAN)


class AttackClockWiringTests(unittest.TestCase):
    def setUp(self):
        self.combat = code('aw_combat.c')
        self.kit = code('aw_animkit.c')

    def test_the_pick_names_the_key_the_blow_lands_on(self):
        rules = code('aw_animpick_rules.inc')
        self.assertIn('put(o->hit,AW_PICK_KEY,"shoot release",NULL);', rules)
        self.assertIn('put(o->hit,AW_PICK_KEY,attacks[s->attack%3]," hit");', rules)
        self.assertIn('char hit[AW_PICK_KEY];', code('aw_animpick.h'))
        clock = body(rules, 'int AW_PickAttackClock(int from,int hit,int to,float rate,float speed,float *seconds,'
                            'float *hit_fraction) {')
        self.assertIn('*seconds=(float)(to-from)/rate/speed;', clock)
        self.assertIn('*hit_fraction=(float)(hit-from)/(float)(to-from);', clock)

    def test_a_swing_asks_the_pick_for_its_clock_at_its_start(self):
        clock = body(self.combat, 'static void swing_clock(slot_t *s,float speed) {')
        # the layout's group first, as before; the table's span when the pick has one
        self.assertIn('s->swing_time=duration(s,G_ATTACK)/speed;s->swing_hit=s->hit_fraction;s->swing_clock=1;', clock)
        self.assertIn('AW_AnimKitAttackTiming(s->e,s->attack,&seconds,&hit)', clock)
        self.assertIn('s->swing_time=seconds/speed;s->swing_hit=hit;s->swing_clock=2;', clock)
        think = body(self.combat, 'static void think(slot_t *s,edict_t *p,float dt) {')
        # the shot (the bow, crossbow or thrown weapon's speed) and the melee swing (the weapon's speed, 1 without one)
        self.assertIn('swing_clock(s,s->f.speed>0?s->f.speed:1);', think)
        self.assertIn('swing_clock(s,s->f.weapon && s->f.speed>0?s->f.speed:1);', think)
        self.assertNotIn('swing_time=duration(s,G_ATTACK)', think)
        # the attack type is chosen before the clock is asked
        self.assertLess(think.index('s->attack=0;'), think.index('swing_clock(s,s->f.speed>0?s->f.speed:1);'))
        self.assertLess(think.index('s->attack=(unsigned char)AW_CombatBestAttack(&s->f,&rng);'),
                        think.index('swing_clock(s,s->f.weapon && s->f.speed>0?s->f.speed:1);'))

    def test_the_blow_and_the_release_land_at_this_swings_share(self):
        physics = body(self.combat, 'void AW_CombatPhysics(void) {')
        self.assertIn('if(!s->struck && s->state_time>=s->swing_time*s->swing_hit){', physics)
        self.assertNotIn('swing_time*s->hit_fraction', self.combat)
        # the per-swing values live in the fight slot, cleared with it (release and a freed edict memset the slot)
        slot = self.combat[self.combat.index('typedef struct {\n    edict_t *e;\n    aw_fighter_t f;'):
                           self.combat.index('} slot_t;')]
        self.assertIn('float swing_hit;unsigned char swing_clock;', slot)
        self.assertIn('memset(s,0,sizeof(*s));', body(self.combat, 'static void release(slot_t *s) {'))

    def test_the_clock_follows_the_picks_own_state_rules_and_keys(self):
        timing = body(self.kit, 'int AW_AnimKitAttackTiming(edict_t *e,int attack,float *seconds,float *hit_fraction) {')
        table = body(self.kit, 'static const aw_skel_table_t *timing_table(edict_t *e,int group,picker_t **pp,'
                               'int *were_out) {')
        # no clock wherever the send would not pick the weapon's span (the guards shared with the hit's clock)
        for guard in ('!pick_on', '!aw_anim_kit_enabled', 'forced_now(e)', 'Cache_Check(&m->cache)', '!a->from_layout',
                      '!a->g[group].present'):
            self.assertIn(guard, table)
        self.assertIn('if(were)t=p?p->table:NULL;', table)
        self.assertIn('if(!(t=timing_table(e,AW_ANIM_ATTACK,&p,&were)))return 0;', timing)
        self.assertIn('!o.hit[0]', timing)
        # the stance's weapon as drive draws it, the same attack state, the same rules and the same key lookup
        self.assertIn('s.weapon=(signed char)(p && p->fighting?p->weapon:were?AW_PW_HANDTOHAND:weapon_of(e));', timing)
        self.assertIn('attack_state(&s,attack);', timing)
        self.assertIn('AW_AnimPick(&s,table_has,(void *)t,&o)', timing)
        self.assertIn('AW_PickAttackClock(key_frame(t,g,o.start),key_frame(t,g,o.hit),key_frame(t,g,o.stop),t->rate,1,'
                      'seconds,', timing)
        drive = body(self.kit, 'static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,'
                               'int g,int storm,int were) {')
        self.assertIn('case AW_ANIM_ATTACK:attack_state(&s,AW_CombatAttackType(e));break;', drive)
        self.assertIn('p->weapon=were?AW_PW_HANDTOHAND:weapon_of(e);', drive)
        # a table-timed swing is shown by the fight's own clock, after the engine group's progress and before the frame
        own = 'if(g==AW_ANIM_ATTACK){float q;if(AW_CombatSwingClock(e,NULL,NULL,&q)==2 && q>=0)progress=q;}'
        self.assertLess(drive.index('if(progress>1)progress=1;'), drive.index(own))
        self.assertLess(drive.index(own), drive.index('else out=p->from+(int)(progress*(float)(p->to-p->from)+.5f);'))
        state = body(self.kit, 'static void attack_state(aw_pick_state_t *s,int attack) {')
        self.assertIn('s->follow=AW_PF_LARGE;', state)

    def test_a_hit_recovery_lasts_the_hit_group_it_is_seen_to_play(self):
        # the fight asks at the hit's start, ends the recovery at that time; both entries into it go through start_hit
        start = body(self.combat, 'static void start_hit(slot_t *s) {')
        self.assertIn('set_state(s,S_HIT,G_HIT);', start)
        self.assertIn('s->hit_time=duration(s,G_HIT);s->hit_clock=1;', start)
        self.assertIn('if(AW_AnimKitHitTiming(s->e,&seconds) && seconds>0){s->hit_time=seconds;s->hit_clock=2;}', start)
        self.assertEqual(self.combat.count('set_state(s,S_HIT,G_HIT)'), 1)
        self.assertNotIn('set_state(v,S_HIT,G_HIT)', self.combat)
        self.assertEqual(self.combat.count('start_hit('), 3)          # its definition, the player's blow, an actor's
        think = body(self.combat, 'static void think(slot_t *s,edict_t *p,float dt) {')
        self.assertIn('if(s->state==S_HIT){if(s->state_time>=s->hit_time)set_state(s,S_CHASE,G_IDLE);', think)
        self.assertNotIn('duration(s,G_HIT)', think)
        self.assertIn('float hit_time;unsigned char hit_clock;', self.combat)
        # the kit rolls the hitN at that moment and keeps the roll for the send, which shows it by the fight's clock
        timing = body(self.kit, 'int AW_AnimKitHitTiming(edict_t *e,float *seconds) {')
        self.assertIn('if(!(t=timing_table(e,AW_ANIM_HIT,&p,&were)) || (!p && !(p=picker_of(e,1))))return 0;', timing)
        self.assertIn('p->roll=(unsigned char)AW_Roll(256);p->hit_rolled=1;s.roll=p->roll;', timing)
        self.assertIn('*seconds=(float)(to-from)/t->rate;', timing)
        drive = body(self.kit, 'static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,'
                               'int g,int storm,int were) {')
        self.assertIn('if((s.event!=p->last.event || !p->picked) && !(s.event==AW_PE_HIT && p->hit_rolled))'
                      'p->roll=(unsigned char)AW_Roll(256);', drive)
        self.assertIn('if(s.event==AW_PE_HIT)p->hit_rolled=0;', drive)
        own = 'if(g==AW_ANIM_HIT){float q;if(AW_CombatHitClock(e,NULL,&q)==2 && q>=0)progress=q;}'
        self.assertLess(drive.index('if(progress>1)progress=1;'), drive.index(own))
        self.assertLess(drive.index(own), drive.index('else out=p->from+(int)(progress*(float)(p->to-p->from)+.5f);'))
        reader = body(self.combat, 'int AW_CombatHitClock(edict_t *e,float *seconds,float *progress) {')
        self.assertIn('if(!s || !s->hit_clock)return 0;', reader)
        self.assertIn('int AW_AnimKitHitTiming(struct edict_s *e,float *seconds);',
                      (SRC / 'aw_animkit.h').read_text(encoding='utf-8'))
        self.assertIn('hit recovery %.3f s, from %s (%s).', self.kit)
        fixture = (ROOT / 'tests' / 'aga_combat_test.c').read_text(encoding='utf-8')
        self.assertIn('assert(ended-started>=sec-.021f && ended-started<=sec+.121f && hit_asks==asks+1);', fixture)

    def test_the_miss_style_stays_the_default_and_still_plays(self):
        # KEEP: aw_combat_miss 1 is the default, and the fight fixture proves a miss still plays the block or the dodge
        self.assertIn('static cvar_t miss_cvar={"aw_combat_miss","1",true};', self.combat)
        fixture = (ROOT / 'tests' / 'aga_combat_test.c').read_text(encoding='utf-8')
        self.assertIn('found=1;assert(!strcmp(cvars[k]->string,"1") && cvars[k]->value==1);}', fixture)
        self.assertIn('if(run_no)assert(frame<31);else assert(frame>=31 && frame<41);', fixture)

    def test_the_clock_is_read_back_by_the_pick_and_dbg(self):
        reader = body(self.combat, 'int AW_CombatSwingClock(edict_t *e,float *seconds,float *hit,float *progress) {')
        self.assertIn('if(!s || !s->swing_clock)return 0;', reader)
        self.assertIn('return s->swing_clock;', reader)
        self.assertIn('swing clock %.3f s, the blow at %.3f of it, from %s (%s).', self.kit)
        # declared beside its callers: aw_combat.h is keyed by the CHIM world stage, and no header a build stage reads
        # changes (the fight slot count, the item kinds)
        header = (SRC / 'aw_combat.h').read_text(encoding='utf-8')
        self.assertNotIn('AW_CombatSwingClock', header)
        self.assertNotIn('AW_AnimKitAttackTiming', header)
        self.assertIn('int AW_AnimKitAttackTiming(struct edict_s *e,int attack,float *seconds,float *hit_fraction);',
                      (SRC / 'aw_animkit.h').read_text(encoding='utf-8'))
        self.assertIn('int AW_CombatSwingClock(edict_t *e,float *seconds,float *hit,float *progress);', self.kit)

    def test_the_fight_fixture_checks_the_clock(self):
        fixture = (ROOT / 'tests' / 'aga_combat_test.c').read_text(encoding='utf-8')
        self.assertIn('int AW_AnimKitAttackTiming(edict_t *e,int attack,float *seconds,float *hit_fraction){', fixture)
        self.assertIn('assert(fabsf(struck-started-sec*hit)<=.021f && fabsf(ended-started-sec)<=.021f);', fixture)

    def test_the_tests_and_docs_are_listed(self):
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        self.assertIn('"tests/aga_attack_clock_test.c"', files)
        self.assertIn('"tests/test_attack_clock.py"', files)
        self.assertIn('ACTOR-ATTACK-ONE-CLOCK-69', (ROOT / 'docs' / 'ACTOR_RECORDS.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
