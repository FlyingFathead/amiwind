# SPDX-License-Identifier: GPL-3.0-only
"""Actors the game keeps out of the world, and fights that must not cross a map change (read only, no build).

PLAZA-FABRICANTS-LIVE-AT-START-67: on a game that never started An Attack on Mournhold, the Plaza Brindisi Dorom's eight
fabricants (fabricant_verm_attack, Fight 100, script fab_attack_2; fabricant_hulkin_attack, Fight 90, fab_attack_1)
disable themselves at their first run ("if FabAttack == 1 enable ... else disable"). The v0.0.67-dev3 image ran those
scripts (dbg sweep: "hidden on purpose: 4 disabled by a script" in the frame map mh0005), yet the hidden fabricants
still attacked on sight: a Disable only took the edict's model off, the ambient think kept checking its Fight, the
combat layer took the fight and its mover drew the actor again. OpenMW 0.51 World::disable takes such a reference out
of the scene (mwworld/worldimp.cpp): nothing fights it and it fights nobody.

GAENOR-ATTACKS-AT-START-67: the fight slots name edicts. A server spawn frees the old map's edicts and the new map's take
the same memory, so a slot kept over the spawn read as a fight of the new map's actor at that edict number; the actors'
change list captured it in the map's first window tick (aw_actors.c Tick, inside the player's scene set-up, before
AW_CombatSceneSpawn) and resumed it (ApplyLoaded). The two fabricants fighting in the Plaza (its 2nd and 4th actors)
became both Gaenors of the Temple Courtyard (its 2nd and 4th; Fight 30, no script of theirs attacks), and the same pair
became Dravil Indrano and Gureryne Selvilo in the Great Bazaar. Any map change could do it, in Vvardenfell too.

The behaviour is proven natively in tests/aga_combat_test.c (test_combat.CombatNativeTests); these are the wiring
contracts of the engine files around it.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='latin-1'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


class DisabledActorFightTests(unittest.TestCase):
    def test_the_one_engage_refuses_a_disabled_reference(self):
        combat = code('aw_combat.c')
        helper = body(combat, 'static int disabled_actor(edict_t *e) {')
        self.assertIn('GetEdictFieldValue(e,"aw_ref")', helper)
        self.assertIn('AW_ObjectDisabled((unsigned int)v->_float)', helper)
        engage = body(combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        gate = engage.index('if(!engage_dead && disabled_actor(e)){disabled_refused++;return 0;}')
        self.assertLess(gate, engage.index('begin_encounter();'))          # refused before a slot or an encounter
        self.assertLess(gate, engage.index('AW_AnimMover(e,1);'))          # never drawn again by its mover
        # every route into a fight goes through that engage: on sight, StartCombat, joins, crimes, resumed rows
        aggro = body(combat, 'int AW_CombatAggro(edict_t *e,const aw_fighter_t *sheet,const char *layout,')
        self.assertIn('AW_CombatEngage(e,&f,layout)', aggro)
        test_engage = body(combat, 'int AW_CombatTestEngage(edict_t *t,int dead) {')
        self.assertIn('AW_CombatEngage(t,&sheet,NULL)', test_engage)

    def test_a_disable_ends_the_actors_fight_before_its_model_is_kept(self):
        host = code('aw_mwhost.c')
        end = body(host, 'static void disabled_fight_end(edict_t *e){')
        self.assertIn('AW_CombatFighter(e)', end)
        self.assertIn('!f->dead', end)                                     # a body keeps its slot
        self.assertIn('aw_mwscript_combat_end(e)', end)
        for head in ('static void object_hide(object_t *o){', 'static void ledger_hide(uint32_t ref){'):
            with self.subTest(head=head):
                hide = body(host, head)
                self.assertLess(hide.index('disabled_fight_end(e);'), hide.index('shown_state(e,'))

    def test_the_ambient_think_skips_a_disabled_actor(self):
        physics = body(code('aw_ambient.c'), 'void AW_AmbientPhysics(void) {')
        skip = physics.index('AW_ObjectDisabled((unsigned int)s->ref)')
        self.assertLess(skip, physics.index('think(s,dt);'))
        self.assertIn('st.disabled++;continue;', physics)


class ServerSpawnFightTests(unittest.TestCase):
    def test_a_server_spawn_drops_the_old_maps_fights_before_the_new_entities(self):
        server = code('sv_main.c')
        spawn = server[server.index('void SV_SpawnServer (char *server)\n#endif\n{'):]
        spawn = spawn[:spawn.index('\n}\n')]
        reset = spawn.index('AW_CombatServerReset();')
        self.assertLess(spawn.index('memset (&sv, 0, sizeof(sv));'), reset)
        self.assertLess(reset, spawn.index('ED_LoadFromFile (sv.worldmodel->entities);'))
        # declared in sv_main.c, not in aw_combat.h: the CHIM world stage keys that header
        self.assertIn('void AW_CombatServerReset (void);', server)
        self.assertNotIn('AW_CombatServerReset', (SRC / 'aw_combat.h').read_text(encoding='latin-1'))

    def test_the_reset_clears_every_edict_pointer_the_combat_layer_keeps(self):
        reset = body(code('aw_combat.c'), 'void AW_CombatServerReset(void) {')
        for part in ('memset(&slots[i],0,sizeof(slots[i]))', 'enemy=NULL;', 'memset(&retry,0,sizeof(retry));',
                     'shots_clear();'):
            self.assertIn(part, reset)

    def test_the_change_list_still_resumes_a_fight_only_from_its_rows(self):
        # the rows are captured each tick while the old map runs; after the spawn nothing of the old server can
        # mark a new map's actor as fighting
        actors = code('aw_actors.c')
        tick = body(actors, 'static void Tick (void)\n{')
        self.assertIn('AW_CombatSlotState (e, NULL) != 0', tick)
        self.assertIn('else if (c->fight && AW_CombatTestEngage (e, 0))', body(actors, 'static void ApplyLoaded (void)\n{'))


if __name__ == '__main__':
    unittest.main()
