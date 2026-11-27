# SPDX-License-Identifier: GPL-3.0-only
"""A werewolf fights with its claws only and is drawn at its race's size (v0.0.68: NPC-WEREWOLF-FIGHTS-ARMED-68,
WEREWOLF-RACE-SCALE-68).

Rules from OpenMW 0.51 (read, not copied): mwmechanics/mechanicsmanagerimp.cpp setWerewolf 1880-1908 (every item off for
any actor, the readied spell put away), aicombataction.cpp prepareNextAction 170-174 (a werewolf character fights hand
to hand and weighs nothing else: no spell, potion, magic item or flee rating) and getMaxAttackDistance 363-375
(fCombatDistanceWerewolfMod), combat.cpp getHandToHandDamage 478-514 (the claws: health damage times the global
WerewolfClawMult), files/data/scripts/omw/input/playercontrols.lua ToggleSpell (the player's spell stance refused in the
form), mwclass/npc.cpp getEncumbrance (no load in the form) and adjustScale 1082-1115 (any character drawn at its race
and sex's weight and height, whatever its form).

The behaviour is proven natively: tests/aga_combat_rules_test.c (the claws' damage by hand, the sheet, the attack
distance; test_combat.CombatNativeTests), tests/aga_combat_test.c (a turned fighter with a mace, a shield, two spells
and magicka: claws only, no spell read or cast, health blows only, its own gear back at UndoWerewolf; a turned guard's
claws on another actor; the player's claws; same class), tests/aga_werewolf_parts_test.c section (j) on the real
aw_view.c code (the player's werewolf at his race's size, each turned character at its record's race, a crowd spread
over the sends; run by tests/test_werewolf_npc.py). Here the wiring those fixtures cannot reach. Each test fails on the
engine before: a turned character fought with its own weapon and spells, a werewolf's hand-to-hand blow was fatigue
damage, and every werewolf was drawn at the unit size."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


def body(text, head):
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


class WerewolfFightWiring(unittest.TestCase):
    def test_a_turned_character_fights_with_its_claws_from_the_engage_and_every_think(self):
        combat = code('aw_combat.c')
        engage = body(combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        self.assertLess(engage.index('fighter_load(s);'), engage.index('fighter_were(s);'))
        self.assertLess(engage.index('fighter_were(s);'), engage.index('AW_ItemsShow(e,s->item);'))
        # a werewolf draws nothing: aw_items.c's turned rule (tests/test_werewolf_npc.py)
        self.assertIn('turned(actor) || !frames_match(',
                      body(code('aw_items.c'), 'int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {'))
        think = body(combat, 'static void think(slot_t *s,edict_t *p,float dt) {')
        self.assertLess(think.index('if(s->state==S_DEAD)return;'), think.index('fighter_were(s);'))
        self.assertLess(think.index('fighter_were(s);'), think.index('if(s->state==S_KNOCK){'))
        were = body(combat, 'static void fighter_were(slot_t *s) {')
        self.assertIn('int now=!s->f.creature && were_of(s->e);', were)    # an NPC, never a creature
        self.assertIn('AW_CombatWerewolfClaws(&aw_combat_settings,&s->f);', were)
        self.assertIn('s->spell=-1;', were)
        self.assertIn('items_hide(s);', were)                     # AW_ItemsHide, and no set held for a draw (v0.0.69)
        self.assertIn('s->f.weapon=s->worn.weapon;', were)       # its own gear again at UndoWerewolf
        self.assertIn('fighter_load(s);', were)
        self.assertIn('if(s->state==S_CAST){', were)             # a cast under way put away with the spell
        # the hooks are the script host's, declared beside their reader and not in aw_combat.h (CHIM-keyed)
        self.assertIn('int (*aw_combat_werewolf)(struct edict_s *e);', combat)
        self.assertIn('float (*aw_combat_claw_mult)(void);', combat)
        header = (SRC / 'aw_combat.h').read_text(encoding='utf-8')
        for name in ('aw_combat_werewolf', 'aw_combat_claw_mult', 'AW_CombatSwingClaws', 'AW_CombatWerewolfClaws'):
            self.assertNotIn(name, header)
        host = code('aw_mwhost.c')
        self.assertIn('aw_combat_werewolf=AW_MwscriptWerewolfNpc;', host)
        self.assertIn('aw_combat_claw_mult=were_claw_mult;', host)

    def test_no_spell_and_no_flee_rating_for_a_werewolf(self):
        combat = code('aw_combat.c')
        choose = body(combat, 'static void choose_spell(slot_t *s,edict_t *p) {')
        self.assertLess(choose.index('if(s->were)return;'), choose.index('cache_spells(s,a);'))   # nothing read
        think = body(combat, 'static void think(slot_t *s,edict_t *p,float dt) {')
        self.assertIn('if(flee_on && ai_ok && s->state==S_CHASE && !s->were){', think)
        # the enemy in werewolf form: the player in the form or a character a script turned (vanillaRateFlee)
        self.assertIn('AW_CombatWerewolfFleeMod(&s->f,s->target_num?were_of(p):aw_move_werewolf,were_level,were_flee_mod)',
                      think)
        # a fleeing actor runs again when a werewolf comes within the werewolf's attack distance (aicombat.cpp 393)
        self.assertIn('reach=AW_CombatWerewolfAttackDistance(&aw_combat_settings,1,were_distance_mod)*SCALE;', think)
        load = body(combat, 'int AW_CombatSettingsLoad(void) {')
        self.assertIn('if(!Q_strcasecmp(name,"fCombatDistanceWerewolfMod"))were_distance_mod=value;', load)
        self.assertIn('were_distance_mod=AW_WERE_DISTANCE_MOD_DEFAULT;', load)

    def test_every_blow_carries_the_claws(self):
        combat = code('aw_combat.c')
        for head, claws in (('static void npc_strike(slot_t *s,edict_t *p) {', 'claws_of(s)'),
                            ('static void npc_strike_actor(slot_t *s,slot_t *v) {', 'claws_of(s)'),
                            ('static void player_strike(edict_t *p) {', 'aw_move_werewolf?claw_mult():-1')):
            with self.subTest(strike=head):
                strike = body(combat, head)
                self.assertIn('AW_CombatSwingClaws(', strike)
                self.assertIn(claws, strike)
                self.assertNotIn('AW_CombatSwing(', strike)
        self.assertIn('static float claws_of(const slot_t *s) {return s->were?claw_mult():-1;}', combat)
        # the player's sheet in the form: the claws, whatever the inventory adapter put on it, at every refresh
        for head in ('void AW_CombatPlayerSheet(aw_fighter_t *o) {', 'static void you_refresh(aw_fighter_t *o) {',
                     'void AW_CombatEquipmentChanged(void) {'):
            with self.subTest(sheet=head):
                self.assertIn('if(aw_move_werewolf)AW_CombatWerewolfClaws(&aw_combat_settings,', body(combat, head))
        rules = code('aw_combat_rules.c')
        swing = body(rules, 'static void swing(')
        self.assertIn('if(claws>=0){health=1;d*=claws;}', swing)
        self.assertLess(swing.index('if(claws>=0){health=1;d*=claws;}'), swing.index('if(health)d*=s->fHandtoHandHealthPer;'))
        self.assertIn('swing(s,a,v,attack,strength,angle,still,-1,r,out);', body(rules, 'void AW_CombatSwing('))

    def test_the_claws_multiplier_is_the_live_global(self):
        host = code('aw_mwhost.c')
        mult = body(host, 'static float were_claw_mult(void){')
        self.assertIn('AW_MwvmGlobalFloat(claw_global)', mult)
        self.assertIn('return AW_WERE_CLAW_MULT_DEFAULT;', mult)
        self.assertIn('"werewolfclawmult"', body(host, 'static void claw_global_find(void){'))
        # found at a change of form and at a load, not in a fight's frame
        case = host[host.index('case AWF_BECOMEWEREWOLF:case AWF_UNDOWEREWOLF:case AWF_ISWEREWOLF:{'):]
        self.assertIn('if(set)claw_global_find();', case[:case.index('case AWF_SETWEREWOLFACROBATICS:{')])
        self.assertIn('if(k>=0 && (were.player || were_npc_n))claw_global_find();', host)
        were = (SRC / 'aw_combat_were.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_WERE_CLAW_MULT_DEFAULT 25.0f', were)
        self.assertIn('#define AW_WERE_DISTANCE_MOD_DEFAULT .3f', were)

    def test_the_player_casts_nothing_in_the_form(self):
        cast = (SRC / 'aw_cast.c').read_text(encoding='utf-8')
        ready = cast[cast.index('static void ready_command(void){'):cast.index('/* the words after "spell"')]
        refuse = ready.index('if(!ready && aw_move_werewolf){')
        self.assertLess(refuse, ready.index('AW_HandReadyPress('))
        self.assertGreater(refuse, ready.index('AW_CONTROL_MAGIC'))


class WerewolfRaceScaleWiring(unittest.TestCase):
    def test_the_players_werewolf_is_drawn_at_his_race_size(self):
        view = code('aw_view.c')
        scale = body(view, 'static void body_scale(float *weight,float *height) {')
        self.assertIn('if(parts_were)(void)were_own_scale(weight,height);', scale)
        drawn = body(view, 'entity_t *AW_ViewBody(entity_t *ent) {')
        self.assertIn('body_scale(&w,&h);', drawn)
        self.assertIn('body.aw_sprite_scale=w;body.aw_alias_zscale=h;', drawn)
        self.assertIn('body_scale(&w,&h);', body(view, 'float AW_ViewRaceHeight(void) {'))
        own = body(view, 'static int were_own_scale(float *weight,float *height) {')
        self.assertIn('AW_PartsRaceScaleFind(rows,AW_PartsRaceScales(', own)
        # the confirmed robe page's assembly (parts_ready) is not where the size comes from
        self.assertNotIn('were_own_scale', body(view, 'static int parts_ready(const char *race,int female) {'))

    def test_a_turned_npc_is_drawn_at_its_race_size_for_the_draw_only(self):
        lod = code('aw_npc_lod.c')
        model = body(lod, 'model_t *AW_NpcLodModel(entity_t *e)\n{')
        self.assertLess(model.index('were_scale(e);'), model.index('return were;'))
        scale = body(lod, 'static void were_scale(entity_t *e)\n{')
        self.assertIn('e->aw_sprite_scale = s * w;', scale)
        self.assertIn('e->aw_alias_zscale = s * h;', scale)
        main = code('r_main.c')
        alias = main[main.index('case mod_alias:'):]
        alias = alias[:alias.index('default:')]
        self.assertLess(alias.index('own_effects = currententity->effects;'),
                        alias.index('currententity->model = AW_NpcLodModel (currententity);'))
        for restore in ('currententity->effects = own_effects;', 'currententity->aw_sprite_scale = own_scale;',
                        'currententity->aw_alias_zscale = own_zscale;'):
            self.assertIn(restore, alias)
        view = code('aw_view.c')
        self.assertIn('aw_npc_were_scale=npc_were_scale;', body(view, 'void AW_ViewInit(void) {'))
        send = body(view, 'void AW_ViewWereNpcSend(int what,int entity) {')
        self.assertIn('npc_were_scale_named(entity);', send)
        self.assertIn('npc_were_scale_sweep();', send)
        table = body(view, 'const aw_skel_table_t *AW_ViewWereNpcTable(void) {')
        self.assertLess(table.index('AW_PartsRaceScales('), table.index('Hunk_FreeToLowMark(mark);'))
        host = code('aw_mwhost.c')
        self.assertIn('aw_view_were_race=actor_race;', host)
        race = body(host, 'static int actor_race(int entity,char *race,int capacity,int *female){')
        self.assertIn('read_string(race_rows[i].race,race,capacity)', race)
        self.assertIn('(b.flags&AWR_FEMALE)!=0', race)

    def test_the_tests_and_docs_are_listed(self):
        files = (ROOT / 'tools/release-files.json').read_text(encoding='utf-8')
        for name in ('tests/test_werewolf_fight.py', 'engine/aga/src/aw_combat_were.h'):
            self.assertIn('"%s"' % name, files)
        combat = (ROOT / 'docs/COMBAT.md').read_text(encoding='utf-8')
        self.assertIn('NPC-WEREWOLF-FIGHTS-ARMED-68', combat)
        third = (ROOT / 'docs/THIRD_PERSON.md').read_text(encoding='utf-8')
        self.assertIn('WEREWOLF-RACE-SCALE-68', third)


if __name__ == '__main__':
    unittest.main()
