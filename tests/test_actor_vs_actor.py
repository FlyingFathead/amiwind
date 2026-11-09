# SPDX-License-Identifier: GPL-3.0-only
"""Fights between two actors (v0.0.63, COMBAT-ACTOR-VS-ACTOR-62): a slot's target is the player (0) or another
actor; StartCombat on another actor sets both against each other; a slot against an actor is no hostile of the
player; the fight ends with its target; GetTarget reads the target. No native fixture links aw_combat.c (its engine
half needs the server), so these are source tests, as for the follow fold."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    depth, i = 0, text.index('{', start)
    while True:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        i += 1


class ActorVsActor(unittest.TestCase):
    def setUp(self):
        self.c = code('aw_combat.c')

    def test_a_slot_has_a_target_and_the_player_is_zero(self):
        self.assertIn('short target_num;', self.c)
        hostiles = body(self.c, 'int AW_CombatHostiles(void) {')
        self.assertIn('!slots[i].target_num', hostiles)          # battle music, the wait refusal: the player's fights

    def test_the_physics_routes_think_and_strike_by_the_target(self):
        phys = body(self.c, 'void AW_CombatPhysics(void) {')
        self.assertIn('if(s->target_num && s->state!=S_DEAD && !s->f.dead && !actor_target(s)){release(s);continue;}', phys)
        self.assertIn('if(s->target_num){slot_t *v=actor_target(s);if(v)npc_strike_actor(s,v);}', phys)
        self.assertIn('else if(!you.dead && !((int)p->v.flags&FL_NOTARGET))npc_strike(s,p);', phys)   # unchanged
        self.assertIn('think(s,v?v->e:p,dt)', phys)
        think = body(self.c, 'static void think(slot_t *s,edict_t *p,float dt) {')
        self.assertIn('if(!s->target_num && you.dead)', think)

    def test_the_strike_between_actors_uses_the_swing_and_the_outcome(self):
        strike = body(self.c, 'static void npc_strike_actor(slot_t *s,slot_t *v) {')
        self.assertIn('AW_CombatSwing(&aw_combat_settings,&s->f,&v->f,', strike)
        self.assertIn('victim_outcome(v,s->e,&out)', strike)
        self.assertNotIn('aw_combat_killed', strike)              # no crime of the player's
        self.assertNotIn('you.', strike)
        outcome = body(self.c, 'static int victim_outcome(slot_t *v,edict_t *attacker,const aw_swing_t *out) {')
        for part in ('set_state(v,S_DEAD,G_DEATH)', 'aw_combat_actor_died(v->e)', 'essential_death(v->e)',
                     'set_state(v,S_KNOCK,G_KNOCK)', 'set_state(v,S_HIT,G_HIT)', 'start_block(v)'):
            self.assertIn(part, outcome)

    def test_engage_against_keeps_a_fight_with_the_player(self):
        eng = body(self.c, 'int AW_CombatEngageAgainst(edict_t *e,const aw_fighter_t *a,edict_t *v,const aw_fighter_t *b) {')
        self.assertIn('if(!was_e || se->target_num)se->target_num=(short)NUM_FOR_EDICT(v);', eng)
        self.assertIn('if(!was_v)sv_->target_num=(short)NUM_FOR_EDICT(e);', eng)

    def test_the_scripts_reach_it(self):
        host = code('aw_mwhost.c')
        hc = body(host, 'static void host_combat(int instance,int target,int verb,int other){')
        self.assertIn('AW_CombatEngageAgainst(e,&sheet,o,&other_sheet)', hc)
        self.assertIn('if(!sv_player || sv_player->v.health<=0)return;', hc)          # the player's path as before
        gt = host[host.index('case AWF_GETTARGET:'):host.index('case AWF_ROTATE:')]
        self.assertIn('AW_CombatTargetOf(e,&pl)', gt)


class JoinFights(unittest.TestCase):
    # v0.0.63 (OpenMW 0.51 actors.cpp engageCombat): allies (the actor followed or escorted, and its followers and
    # escorts) join a fight their ally is in; guards join against a creature in a fight within fAlarmRadius unless it
    # follows someone; only on sight and notice; checked once a second, against the fighters collected once
    def test_the_join_rules(self):
        host = code('aw_mwhost.c')
        j = body(host, 'static void join_fights(float dt){')
        self.assertIn('join_clock+=dt;if(join_clock<1)return;', j)
        self.assertIn('if(!nf)return;', j)                                       # nothing while nobody fights
        self.assertIn('if(f==leader || fights[j].leader==e){x=t;why=1;break;}', j)   # allies, both ways
        self.assertIn('ff->creature && alarm>0 && !fights[j].leader', j)         # guards: a creature not following
        self.assertIn('if(guard<0)guard=crime_guard(e);', j)
        self.assertIn('if(!AW_CrimeSight(e,x) || !detected(e,x))continue;', j)   # getLOS and the awareness check
        self.assertIn('join_fights(dt);', body(host, 'void AW_MwscriptTick(float dt){'))
        # the player's own followers and escorts: they help the player against whoever fights him, and never start a
        # fight with the player by their Fight value (OpenMW engageCombat: the player is their ally)
        self.assertIn('if(leader==sv_player && t==sv_player){x=f;why=1;break;}', j)
        amb = code('aw_ambient.c')
        self.assertIn('if((s->travel==3 || s->travel==4 || s->travel==5) && sv_player && '
                      's->follow_num==NUM_FOR_EDICT(sv_player))return;', body(amb, 'static void aggro(slot_t *s) {'))
        leader = body(amb, 'edict_t *AW_AmbientLeaderOf(edict_t *e) {')
        self.assertIn('s->travel!=3 && s->travel!=4 && s->travel!=5', leader)
        self.assertIn('float AW_CrimeAlarmRadius(void){return full()?settings.fAlarmRadius*SCALE:0;}', code('aw_crime.c'))


if __name__ == '__main__':
    unittest.main()
