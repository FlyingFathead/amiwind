# SPDX-License-Identifier: GPL-3.0-only
"""The draw and the put-away of a fighter's weapon, as in the original (ACTOR-WEAPON-SHOWN-BEFORE-DRAW-69,
ACTOR-DRAW-STOPS-LEGS-69).

What was wrong: the weapon and shield were in the hand from the first frame of the draw and gone before the put-away
played; a first swing could start under the draw's pose; and the draw posed the whole body, so the legs of a fighter
running at its enemy stood still in the draw pose. What is right now (OpenMW 0.53 character.cpp, read, not copied:
the weapon shown at the draw's "equip attach" key and hidden at the put-away's "unequip detach" key, at the group's
start when it has none; an attack only from the equipped state; the weapon groups on the upper body above the
movement on the lower body of a two-legged actor): the set is held out of the hand until the attach key and kept on
the hand until the detach key, no swing or shot starts under the draw, and a draw or put-away while the actor moves
plays on its torso while its legs keep the walk. The miss style (aw_combat_miss 1) is untouched.

Natively: tests/aga_combat_test.c (the hold, no swing under the draw, the put-away kept to the detach key, the time
limits, a hidden actor, the old route without the kit) and tests/test_skel_native.py (three pose layers: the torso on
the draw over the walk, an arm's own layer under it). Here the wiring, by the source."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


class WeaponInTheHandTests(unittest.TestCase):
    def setUp(self):
        self.kit = code('aw_animkit.c')
        self.combat = code('aw_combat.c')

    def test_the_draw_and_the_put_away_know_their_key(self):
        over = body(self.kit, 'static void over(picker_t *p,const aw_skel_table_t *t,aw_pick_state_t s) {')
        self.assertIn('p->over_event=s.event==AW_PE_EQUIP || s.event==AW_PE_UNEQUIP?s.event:0;', over)
        self.assertIn('p->over_key=key_frame(t,g,p->over_event==AW_PE_EQUIP?"equip attach":"unequip detach");', over)
        self.assertIn('if(p->over_from>=0)over_items(p,0,1);', over)       # an over played over by another ends
        tell = body(self.kit, 'static void over_items(picker_t *p,int frame,int ending) {')
        self.assertIn('(!ending && p->over_key>=0 && frame<p->over_key)', tell)
        self.assertIn('if(p->over_event==AW_PE_EQUIP)AW_CombatItemsInHand(p->e,1);else AW_CombatSheathed(p->e);', tell)

    def test_the_send_holds_the_set_until_the_key(self):
        drive = body(self.kit, 'static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,'
                               'int g,int storm,int were) {')
        self.assertIn('if(p->over_from>=0 && p->over_event==AW_PE_EQUIP)AW_CombatItemsInHand(e,0);', drive)
        self.assertIn('if(p->over_from<0 || p->over_event!=AW_PE_UNEQUIP)AW_CombatSheathed(e);', drive)
        self.assertIn('over_items(p,out,done && p->over_loops<=0);', drive)
        self.assertIn('if(p->over_from>=0)over_items(p,0,1);', drive)      # a hit or a fall cuts the draw: in the hand
        drawing = body(self.kit, 'int AW_AnimKitDrawing(edict_t *e) {')
        self.assertIn('return p && p->over_from>=0 && p->over_event==AW_PE_EQUIP;', drawing)
        sheathes = body(self.kit, 'int AW_AnimKitSheathes(edict_t *e) {')
        self.assertIn('strcmp(pr_strings+e->v.classname,"aw_npc")', sheathes)   # driven once its slot is let go
        self.assertIn('s.event=AW_PE_UNEQUIP;', sheathes)

    def test_the_fight_holds_and_keeps_the_set(self):
        held = body(self.combat, 'void AW_CombatItemsInHand(edict_t *e,int in_hand) {')
        self.assertIn('items_drawn(s,0);s->items_held=1;s->items_hold_until=(float)sv.time+items_hold_seconds;', held)
        drawn = body(self.combat, 'static void items_drawn(slot_t *s,int in_hand) {')
        self.assertIn('s->item_model[k]=(short)i->v.modelindex;i->v.modelindex=0;', drawn)
        put = body(self.combat, 'static void items_put_away(slot_t *s,edict_t *alive) {')
        self.assertIn('!AW_AnimKitSheathes(alive)){items_hide(s);return;}', put)
        self.assertIn('AW_ItemsMoveSet(s->item,sheathes[i].item);', put)
        self.assertIn('items_put_away(s,alive);', body(self.combat, 'static void release(slot_t *s) {'))
        update = body(self.combat, 'static void sheathes_update(int now) {')
        self.assertIn('if(!now || e->free || e->v.modelindex<=0 || sv.time>=sheathes[i].until){', update)
        physics = body(self.combat, 'void AW_CombatPhysics(void) {')
        self.assertIn('if(s->items_held && sv.time>=s->items_hold_until){items_drawn(s,1);s->items_held=0;}', physics)
        self.assertIn('sheathes_update(1);', physics)
        self.assertIn('sheathes_update(0);', body(self.combat, 'void AW_CombatClear(void) {'))
        for reset in ('void AW_CombatServerReset(void) {', 'void AW_CombatSceneSpawn(void) {'):
            self.assertIn('memset(sheathes,0,sizeof(sheathes));', body(self.combat, reset))
        engage = body(self.combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        self.assertIn('AW_CombatSheathed(e);', engage)
        self.assertIn('void AW_ItemsMoveSet(edict_t *from[AW_ITEMS_KINDS],edict_t *to[AW_ITEMS_KINDS]) {',
                      code('aw_items.c'))

    def test_no_swing_or_shot_under_the_draw(self):
        think = body(self.combat, 'static void think(slot_t *s,edict_t *p,float dt) {')
        self.assertEqual(think.count('if(s->cooldown<=0 && !AW_AnimKitDrawing(s->e)){'), 2)
        self.assertNotIn('if(s->cooldown<=0){', think)

    def test_declared_beside_their_callers(self):
        # aw_combat.h is keyed by the CHIM world stage and aw_items.h is read by a build stage: neither changes
        for name in ('AW_CombatItemsInHand', 'AW_CombatSheathed', 'AW_AnimKitDrawing'):
            self.assertNotIn(name, (SRC / 'aw_combat.h').read_text(encoding='utf-8'))
        for name in ('AW_ItemsMoveSet', 'AW_ItemsTorsoRoot', 'aw_items_torso_layer'):
            self.assertNotIn(name, (SRC / 'aw_items.h').read_text(encoding='utf-8'))
        header = (SRC / 'aw_animkit.h').read_text(encoding='utf-8')
        self.assertIn('int AW_AnimKitDrawing(struct edict_s *e);', header)
        self.assertIn('int AW_AnimKitSheathes(struct edict_s *e);', header)


class LegsWalkOnTests(unittest.TestCase):
    def setUp(self):
        self.kit = code('aw_animkit.c')

    def test_a_draw_over_the_walk_plays_on_the_torso(self):
        drive = body(self.kit, 'static void drive(picker_t *p,edict_t *e,const aw_skel_table_t *t,const aw_anim_t *a,'
                               'int g,int storm,int were) {')
        self.assertIn('if(p->over_event && !were && s.event==AW_PE_NONE && s.move!=AW_PM_NONE &&', drive)
        self.assertIn('(root=AW_ItemsTorsoRoot(sv.models[(int)e->v.modelindex],t))>=0){', drive)
        self.assertIn('p->torso_root=root;p->torso_frame=out;p->torso_num=NUM_FOR_EDICT(e);p->torso_send=pick_sends;',
                      drive)
        # standing, or no movement group for the legs: the draw on the whole body as before
        self.assertIn('out=p->torso_frame;p->torso_root=-1;torso_now--;', drive)
        self.assertLess(drive.index('p->torso_root=-1;\n    if(p->over_from>=0){'), drive.index('torso_now++;'))
        presend = body(self.kit, 'void AW_AnimPickPreSend(void) {')
        self.assertIn('pick_sends++;torso_now=0;', presend)
        lookup = body(self.kit, 'static int torso_of_number(int n,float *layer_frame,int *root) {')
        self.assertIn('if(!torso_now)return 0;', lookup)          # no cost while no actor draws over its walk
        self.assertIn('p->torso_send==pick_sends', lookup)
        self.assertIn('R_AliasTorsoLayer=torso_render;aw_items_torso_layer=torso_items;', self.kit)

    def test_the_renderer_and_the_items_pose_the_torso_alike(self):
        alias = code('r_alias.c')
        key = body(alias, 'static int AW_SkelEntityKey (const entity_t *e, const model_t *model, const aliashdr_t *hdr,'
                          ' int frame, float yaw,')
        self.assertIn('if (e && R_AliasTorsoLayer && R_AliasTorsoLayer (e, &l, &r))', key)
        self.assertIn('*torso = 1 + (int)l;', key)
        self.assertIn('slot->torso = torso;', alias)
        self.assertIn('#define AW_SKEL_LAYERS 3', (SRC / 'aw_skel.h').read_text(encoding='utf-8'))
        items = code('aw_items.c')
        root = body(items, 'int AW_ItemsTorsoRoot(const model_t *m,const void *skel_table) {')
        self.assertIn('neck!=tab->parent[r] || tab->parent[neck]<=0)return -1;', root)
        self.assertIn('return tab->parent[neck];', root)
        rows = body(items, 'static int skel_rows(int t,int f,edict_t *actor,float rows[AW_ITEMS_ROW]) {')
        self.assertIn('aw_items_torso_layer(actor,&layers[1],&roots[1])', rows)
        self.assertIn('*frame=pose_key(actor);', items)


class ListedTests(unittest.TestCase):
    def test_the_module_is_shipped(self):
        self.assertIn('"tests/test_draw_moments.py"', (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
