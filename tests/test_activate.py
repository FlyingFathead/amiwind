# SPDX-License-Identifier: GPL-3.0-only
"""What the use key acts on (FOCUS-NPC-OVERRIDES-ITEM-62): as in OpenMW 0.51 the nearest thing along the view ray within
the activation distance, never the nearest actor. The rules in host C by number (an item between the player and an
actor, an item beside a body, a plant before a resident) and the source contracts that every use path (the prompt, E,
the body's search) asks the same choice."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(name, start):
    text = code(name)
    at = text.index(start)
    depth, i = 0, text.index('{', at)
    for j in range(i, len(text)):
        depth += {'{': 1, '}': -1}.get(text[j], 0)
        if depth == 0:
            return text[at:j + 1]
    raise AssertionError('unbalanced ' + start)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class ActivateNativeTests(unittest.TestCase):
    def test_the_nearest_thing_on_the_ray_takes_the_use(self):
        native.NativeSourceTests().compile_run('aga_activate_rules_test.c', [SRC / 'aw_activate_rules.c'],
                                               cflags=UBSAN)

    def test_a_body_gives_its_use_to_a_script_that_reads_onactivate(self):
        # CONTAINER-SCRIPT-ACTIVATE-67: a dead actor whose script holds the use is not searched by E; the script's
        # Activate searches it; a living actor is left to the talk (aga_corpse_activate_test.c plays aw_corpse.c)
        native.NativeSourceTests().compile_run('aga_corpse_activate_test.c', [SRC / 'aw_corpse.c'], cflags=UBSAN)


class ScriptedActivatorUseTests(unittest.TestCase):
    """ROOM-SCRIPTED-ACTIVATOR-NO-USE-68: a named activator ('N' focus row) whose script reads OnActivate takes the use
    key (OpenMW 0.51 Activator::activate: the script's OnActivate), found on the Halls of Penumbra's ice wall
    (bm_ice_wall, icewallScript): its focus row names it by the stable id 2126003, its script's instance is bound under
    the merged number 8417459, and an 'N' row was a name alone."""

    def code(self, name):
        return (SRC / name).read_text(encoding='latin-1')

    def test_a_named_activator_whose_script_takes_the_use_is_used(self):
        inv = self.code('aw_inventory.c')
        body = inv[inv.index('static int placed_use(void){'):inv.index('/* COLLECT-CAPACITY-REJECTED-60')]
        self.assertIn("if(best>=0 && focus_rows[best].kind=='N')\n"
                      "        return aw_inventory_intercept && aw_inventory_intercept(focus_rows[best].reference)?1:0;",
                      body)
        self.assertIn("return row->kind=='N' && aw_inventory_takes_use && aw_inventory_takes_use(row->reference);", inv)
        self.assertIn("focus_rows[best].kind=='C' || scripted_board(&focus_rows[best])))\n        placed_aim=nearest;", inv)
        host = self.code('aw_mwhost.c')
        self.assertIn('aw_inventory_takes_use=object_takes_use;', host)
        vm = self.code('aw_mwvm.c')
        query = vm[vm.index('int AW_MwvmTakesUse(uint32_t reference){'):]
        query = query[:query.index('}') + 1]
        self.assertNotIn('flags|=', query)          # a question: the instance's flags stay as they are
        self.assertNotIn('flags&=', query)

    def test_the_script_is_found_under_either_form_of_the_reference(self):
        host = self.code('aw_mwhost.c')
        self.assertIn('if(r>=(1u<<22) && r<(3u<<22))return ((r>>22)<<20)|(r&0x3FFFFFu);', host)
        self.assertIn('if(r>=(1u<<20) && r<(3u<<20))return ((r>>20)<<22)|(r&0xFFFFFu);', host)
        self.assertIn('(!AW_MwvmUse(reference) && (other==reference || !AW_MwvmUse(other)))', host)

        def other(r):
            if (1 << 22) <= r < (3 << 22):
                return ((r >> 22) << 20) | (r & 0x3FFFFF)
            if (1 << 20) <= r < (3 << 20):
                return ((r >> 20) << 22) | (r & 0xFFFFF)
            return r
        import sys
        sys.path[:0] = [str(ROOT / 'tools')]
        from ref_identity import stable_ref
        wall = stable_ref('Bloodmoon.esm', 8417459 - (2 << 22))
        self.assertEqual(wall, 2126003)
        self.assertEqual((other(wall), other(8417459)), (8417459, 2126003))
        self.assertEqual(other(225480), 225480)      # a base game number: both forms


class ActivateSourceTests(unittest.TestCase):
    def test_nothing_is_taken_or_opened_before_the_inventory_is_allowed(self):
        # PRISON-SHIP-ITEMS-TAKEABLE-65: the original's NullAction while the Inventory window is not allowed (OpenMW
        # 0.53 Container::activate, Class::defaultItemActivate, Light::activate): the game's own flag (aw_story.c
        # AW_StoryInventoryAllowed, set by the papers' EnableInventoryMenu) gates the player's use of a container, a
        # plant and an item, after a script that takes the activation and after the book reader (the host C test
        # aga_focus_pickup_test.c plays it: no take, no window, no action line; a book reads)
        self.assertIn('aw_inventory_allowed=AW_StoryInventoryAllowed;', code('aw_debug.c'))
        use = body('aw_inventory.c', 'static int placed_use(void){')
        self.assertIn('return inventory_allowed()?container_open(&focus_rows[best]):1;', use)
        intercept = use.index('aw_inventory_intercept(row->reference))return 1;')
        reader = use.index('aw_book_reader(row->reference))return 1;')
        refuse = use.index('if(!inventory_allowed())return 1;')
        self.assertLess(intercept, refuse)
        self.assertLess(reader, refuse)
        self.assertLess(refuse, use.index('return take_row(row);'))
        prompt = body('aw_inventory.c', 'int AW_ItemPrompt(char *line,int size,int *steal){')
        self.assertIn('return inventory_allowed()?container_prompt(&focus_rows[best],line,size,steal):0;', prompt)
        self.assertIn('if((code&3)!=FOCUS_ACT_READ && !inventory_allowed())return 0;', prompt)
        scene = body('aw_scene.c', 'int AW_SceneUse(void) {')
        self.assertIn('((!aw_inventory_allowed || aw_inventory_allowed()) && AW_HarvestUse())', scene)
        # a book is read but not taken: the reader shows no Take and E there takes nothing (OpenMW 0.53
        # mwgui/bookwindow.cpp and scrollwindow.cpp setInventoryAllowed); the reader's Take path refuses too
        self.assertIn('if(!inventory_allowed())return 0;', body('aw_inventory.c', 'int AW_PlacedTake(unsigned reference){'))
        self.assertIn("(key=='e' || key=='E' || key==K_ENTER) && take_allowed())close_reader(1);",
                      body('aw_reader.c', 'int AW_ReaderKey(int key)'))
        self.assertIn('if(take_allowed()){', body('aw_reader.c', 'void AW_ReaderDraw(void)'))

    def test_a_container_gives_its_use_to_a_script_that_reads_onactivate(self):
        # CONTAINER-SCRIPT-ACTIVATE-67: the original's rule for every object (OpenMW 0.51 mwworld/refdata.cpp
        # activate, mwscript/miscextensions.cpp OpActivate): a container whose script holds the use stays shut on E
        # (the script's OnActivate reads 1 on its next run) and opens by the script's Activate, through the
        # container's own rules (the Inventory window's flag, the lock, the trap, the strip). The hook is the items'
        # (aw_mwhost.c object_intercept); the host C test aga_focus_pickup_test.c plays both halves
        use = body('aw_inventory.c', 'static int placed_use(void){')
        held = use.index('aw_inventory_intercept(focus_rows[best].reference))return 1;')
        self.assertLess(held, use.index('return inventory_allowed()?container_open(&focus_rows[best]):1;'))
        # the census registration's refusal stays first (OPENING-REGRESSION-64)
        self.assertLess(use.index('aw_census_take_refused()'), held)
        activate = body('aw_inventory.c', 'int AW_ContainerActivate(unsigned reference){')
        self.assertIn("if(focus_rows[i].kind!='C' || focus_rows[i].reference!=reference)continue;", activate)
        self.assertIn('if(inventory_allowed())container_open(&focus_rows[i]);', activate)
        host = body('aw_mwhost.c', 'static void object_activate(uint32_t reference){')
        self.assertLess(host.index('if(AW_PlacedActivate(reference))return;'),
                        host.index('if(AW_ContainerActivate(reference))return;'))
        self.assertLess(host.index('if(AW_ContainerActivate(reference))return;'), host.index('AW_DialWindowTalkTo(e)'))
        self.assertIn('aw_inventory_intercept=object_intercept;', code('aw_mwhost.c'))
        # a dead actor's body the same way (the Spriggans of Solstheim): E is the script's while it holds the use,
        # and the script's Activate on a dead actor searches the body instead of opening a talk
        corpse = body('aw_corpse.c', 'static int corpse_use(void){')
        self.assertLess(corpse.index('if(aw_scene_intercept && aw_scene_intercept(reference))return 1;'),
                        corpse.index('return aw_container_open('))
        self.assertIn('&& !AW_CorpseActivate(e,reference))', host)
        self.assertLess(host.index('!AW_CorpseActivate(e,reference))'), host.index('AW_DialWindowTalkTo(e)'))
        self.assertIn('aw_scene_intercept=aw_hinged_intercept=object_intercept;', code('aw_mwhost.c'))

    def test_no_text_overlay_on_placed_objects_before_the_papers(self):
        # PRISON-SHIP-ITEMS-TAKEABLE-65 (the maintainer's rule, 17 November 2026): before the papers no placed object
        # shows a name or an action line (the prison ship's bottles, travel lantern, crates and hammock); a door keeps
        # its name; the rule is the story's (aw_story.c AW_StoryObjectLabels), wired in aw_debug.c, and both the name
        # (AW_PlacedFocus, which AW_SceneDraw takes the title from) and the action line (AW_ItemPrompt) obey it. The
        # host C tests play it (aga_focus_pickup_test.c, aga_character_state_test.c)
        self.assertIn('aw_object_labels=AW_StoryObjectLabels;', code('aw_debug.c'))
        story = body('aw_story.c', 'int AW_StoryObjectLabels(void)')
        self.assertIn('aw_story.stage>=AW_STAGE_PAPERS', story)
        focus = body('aw_inventory.c', 'int AW_PlacedFocus(const char **name,')
        self.assertIn("if(focus_rows[best].kind!='D' && !labels_allowed())return 0;", focus)
        prompt = body('aw_inventory.c', 'int AW_ItemPrompt(char *line,int size,int *steal){')
        self.assertLess(prompt.index('if(!labels_allowed())return 0;'), prompt.index('placed_target()'))
        draw = body('aw_scene.c', 'void AW_SceneDraw(void) {')
        self.assertIn('AW_PlacedFocus(&focus_name,', draw)

    def test_every_use_path_asks_the_same_choice(self):
        # HUD-TEXTS-OVERLAP-67: ONE focus a frame (aw_scene.c focus_kind, the rule AW_FocusChoose): the prompt and the
        # name under the view (npc_target), E (pr_cmds.c aw_npctarget and AW_SceneUse) and the body's search
        # (aw_corpse.c) all take it; the plain actor test stays for combat and spells
        scene = code('aw_scene.c')
        self.assertIn('static edict_t *npc_target(void) {return focus_kind()==AW_FOCUS_ACTOR?focus_actor:NULL;}', scene)
        self.assertIn('return focus_kind()==AW_FOCUS_ACTOR?focus_actor:NULL;', body('aw_scene.c', 'edict_t *AW_ActivateActor('))
        self.assertIn('AW_ActivateActor(player,player->v.v_angle)', body('pr_cmds.c', 'static void PF_aw_npctarget('))
        self.assertIn('AW_ActivateActor(p,p->v.v_angle)', body('aw_corpse.c', 'static edict_t *corpse_target('))
        self.assertNotIn('AW_ActivateActor', code('aw_combat.c'))

    def test_one_focus_a_frame_weighs_every_kind_on_the_ray(self):
        # HUD-TEXTS-OVERLAP-67: the actor's box, the item or plant, the load door and the hinged door, each by where the
        # view ray meets it, go to the one rule; the actor's hold uses his whole model's box for a moment only
        choice = body('aw_scene.c', 'static int focus_kind(void) {')
        for part in ('e=AW_NPCTarget(p,cl.viewangles);aim.actor_near=npc_aim_near;aim.actor_far=npc_aim_far;',
                     # PLANT-BOX-AIM-69: the item or container and the plant to pick, the nearer of them (and a plant
                     # inside the container's measured box), AW_PlantFirst (host tested)
                     'float item=AW_InventoryAimDistance(),plant=AW_HarvestAimDistance();',
                     'focus_plant_first=AW_PlantFirst(item,plant,plant>=0 && item>=0 && AW_PlacedAimHolds(plant));',
                     'aim.thing=focus_plant_first?plant:item;',
                     'aim.door=aimed_door()>=0?door_aim:-1;', 'aim.hinged=aw_hinged_aim?aw_hinged_aim():-1;',
                     'focus_held_kind=AW_FocusChoose(&aim,focus_held_kind);',
                     'realtime>focus_actor_seen && realtime-focus_actor_seen<AW_FOCUS_HOLD_SECONDS'):
            self.assertIn(part, choice)
        self.assertIn('door_aim=best>=0?closest:-1;', body('aw_scene.c', 'static int aimed_door(void) {'))
        self.assertIn('aw_hinged_aim=AW_HingedDoorAimDistance;', code('aw_hinged_door.c'))

    def test_the_use_key_and_the_title_follow_the_one_focus(self):
        # HUD-TEXTS-OVERLAP-67: E opens a load door or a hinged door only when it has the focus (a door behind the person
        # shown is never opened); the draw gives ONE title: the person's (WHO) or an object's own, never both
        use = body('aw_scene.c', 'int AW_SceneUse(void) {')
        self.assertIn('i=kind==AW_FOCUS_DOOR?aimed_door():-1;', use)
        self.assertIn('return kind==AW_FOCUS_HINGED && aw_hinged_use?aw_hinged_use():0;', use)
        draw = body('aw_scene.c', 'void AW_SceneDraw(void) {')
        self.assertEqual(draw.count('AW_UIObjectName('), 0)
        self.assertEqual(draw.count('focus_title_draw('), 3)
        self.assertIn('if(ami && (npc || !name || !*name))focus_title_draw(who,(int)target_style.value);', draw)
        self.assertIn('if(!npc && *name)focus_title_draw(name,(int)label_style.value);', draw)
        self.assertIn('i=kind==AW_FOCUS_DOOR?aimed_door():-1;', draw)
        self.assertIn('kind==AW_FOCUS_HINGED && aw_hinged_hint && aw_hinged_hint(&name,&action)', draw)

    def test_the_choice_weighs_the_item_and_the_plant_against_the_actors_box(self):
        choice = body('aw_scene.c', 'edict_t *AW_ActivateActor(')
        self.assertIn('AW_InventoryAimDistance()', choice)
        self.assertIn('AW_HarvestAimDistance()', choice)
        self.assertIn('AW_ActivateItemFirst(AW_ActivateNearest(', choice)
        # the actor test keeps where the ray enters and leaves the chosen actor's box
        target = body('aw_scene.c', 'edict_t *AW_NPCTargetReach(')
        self.assertIn('AW_RayBox(end,ray,fmins,fmaxs,&lo,&hi) && lo<limit){limit=lo;best=e;npc_aim_near=lo;npc_aim_far=hi;}',
                      target)

    def test_a_persons_use_box_is_his_body(self):
        # FOCUS-NPC-OVERRIDES-ITEM-62: a person's model stores one frame since v0.0.52 whose box encloses every pose;
        # the use test and the focus hold take his body's box (aw_activate_rules.c AW_ActorUseBox, host tested by
        # aga_activate_rules_test.c and aga_npc_contact_test.c), evicted too by the bit a resident look keeps; a
        # creature by aw_ambient.c's slot, else its progs/c_ model; a body by the fight's state
        target = body('aw_scene.c', 'edict_t *AW_NPCTargetReach(')
        narrow = 'actor_use_box(e,frames,fmins,fmaxs,fmins,fmaxs);'
        self.assertIn(narrow, target)
        self.assertLess(target.index(narrow), target.index('AW_RayBox(end,ray,fmins,fmaxs,&lo,&hi)'))
        self.assertIn('m->flags=(m->flags&~AW_MODEL_ONE_STORED_FRAME)|(frames==1?AW_MODEL_ONE_STORED_FRAME:0);', target)
        whole = body('aw_scene.c', 'static int actor_whole_box(')
        self.assertIn('actor_use_box(target,(m->flags&AW_MODEL_ONE_STORED_FRAME)?1:0,m->mins,m->maxs,wmins,wmaxs);',
                      whole)
        self.assertIn('AW_RayBox(end,ray,wmins,wmaxs,lo,hi)', whole)
        box = body('aw_scene.c', 'static int actor_use_box(')
        self.assertIn('AW_ActorPersonHull(e->v.mins,e->v.maxs)', box)
        self.assertIn('use_box_creature(e)', box)
        self.assertIn('AW_CombatSlotState(e,NULL)==2', box)
        self.assertIn('!strncmp(pr_strings+e->v.model,"progs/c_",8)', body('aw_scene.c', 'static int use_box_creature('))
        self.assertIn('aw_actor_creature=slot_creature;', code('aw_ambient.c'))
        # the loaders and model.h stay as they are: their sources are pinned in the CHIM world stages' key
        # (tools/engine_loader_policy.py), so the bit is kept by the use test itself
        for name in ('model.h', 'model.c', 'model_alias_stream.inc'):
            self.assertNotIn('AW_MODEL_ONE_STORED_FRAME', (SRC / name).read_text(encoding='utf-8'))

    def test_an_actors_own_focus_row_never_hides_an_item(self):
        placed = body('aw_inventory.c', 'static int placed_target(void){')
        self.assertIn("if(row->kind=='A')continue;", placed)
        # an item, a container, or a named activator whose script takes the use (ROOM-SCRIPTED-ACTIVATOR-NO-USE-68);
        # never an actor's row
        self.assertIn("(focus_rows[best].kind=='I' || focus_rows[best].kind=='C' || scripted_board(&focus_rows[best])))"
                      "\n        placed_aim=nearest;", placed)

    def test_an_item_lying_on_another_goes_to_what_the_ray_meets_first(self):
        # CENSUS-CRAB-PLATE-FOCUS-66: the crab meat on the census office's silver plate (their centres half a game
        # unit apart): the use went to the plate, whose origin lay a hair nearer the crosshair line. Every row the map
        # draws with a shape the ray can meet is aimed where the ray meets it: an edict of its own by the view trace's
        # first hit, a CHIM room's item by its placement box (ranked), the placed list's by its model (the host C test
        # aga_focus_pickup_test.c takes the crab meat, and the plate when the ray meets the plate)
        placed = body('aw_inventory.c', 'static int placed_target(void){')
        self.assertIn('view_ref=view_reference(p,eye,f,reach,&view_hit);', placed)
        # CONTAINER-BRUSH-ROWS-67: a container drawn as a brush of its own the same way
        self.assertIn("if((row->kind=='I' || row->kind=='C') && row->live && view_ref && row->reference==view_ref){",
                      placed)
        self.assertIn('nearest=view_hit;best=i;continue;', placed)
        self.assertIn('(hit=aw_room_ray(row->reference,eye,f))>=0 && hit<along)rank=hit;', placed)
        self.assertIn('if(!aim_takes(i,rank,best,nearest,reach,shift,eye,f))continue;', placed)   # PLANT-BOX-AIM-69
        self.assertIn('nearest=rank;best=i;', placed)
        self.assertNotIn('nearest=along;best=i;', placed)
        view = body('aw_inventory.c', 'static unsigned view_reference(')
        self.assertIn('tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);', view)
        self.assertIn('GetEdictFieldValue(tr.ent,"aw_ref")', view)
        # the aim report says what the ray meets and always lists the aimed row
        report = body('aw_inventory.c', 'void AW_PlacedAimReport(void){')
        self.assertIn('the view ray meets reference %u first', report)
        self.assertIn('if(shown>=12 && i!=best)continue;', report)

    def test_an_item_standing_in_furniture_is_aimed_past_its_hull(self):
        # CENSUS-SHELF-PLATE-BAKED-67: the census office's Limeware Platter (119554) stands inside its bookshelf's
        # collision hull (119541, the hull over the shelf's open front), so the view ray met the shelf and the sight line
        # to the platter's origin met it too: no box, E took nothing. One more trace past the furniture met first: the
        # item met inside the furniture's box is aimed (the host C test aga_focus_pickup_test.c takes it)
        inner = body('aw_inventory.c', 'static unsigned view_inner_reference(')
        self.assertIn('tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,holder);', inner)
        self.assertIn('tr.endpos[k]<holder->v.absmin[k]-1 || tr.endpos[k]>holder->v.absmax[k]+1', inner)
        self.assertIn('view_met=tr.ent;', body('aw_inventory.c', 'static unsigned view_reference('))
        placed = body('aw_inventory.c', 'static int placed_target(void){')
        self.assertIn('inner_ref=view_inner_reference(view_met,eye,f,reach,&inner_hit);', placed)
        self.assertIn("if(row->kind=='I' && row->live && inner_ref && row->reference==inner_ref && inner_ref!=view_ref){",
                      placed)
        self.assertIn('nearest=inner_hit;best=i;continue;', placed)
        self.assertIn('in it, the ray meets reference %u at %.1f', body('aw_inventory.c', 'void AW_PlacedAimReport(void){'))

    def test_what_stands_in_a_plants_box_wins_over_the_plant(self):
        # PLANT-BOX-AIM-69: every plant that opens as a container carries its measured box (FARGOTH-STASH-STUMP-69),
        # the visible box of the whole plant, far coarser than its leaves: 3 items, 18 boards (two of them Balmora's
        # signposts), 4 people, 37 plants to pick and 3,316 smaller plants stand inside one outdoors. Every branch of the
        # placed rows' choice asks the one rule (aw_activate.h AW_AimTakes, host tested), never the nearer alone
        placed = body('aw_inventory.c', 'static int placed_target(void){')
        self.assertNotIn('hit>nearest', placed)
        self.assertNotIn('rank>nearest', placed)
        self.assertEqual(placed.count('aim_takes(i,'), 7)
        for t in ('view_hit', 'inner_hit', 'rank'):
            self.assertIn('aim_takes(i,%s,best,nearest,reach,shift,eye,f)' % t, placed)
        self.assertEqual(placed.count('aim_takes(i,hit,best,nearest,reach,shift,eye,f)'), 4)
        # the eye inside a container's box (standing in the bush): the box says nothing of where the plant is along the
        # ray and would take every aim; the container is aimed at its point instead, as before the boxes
        box = placed[placed.index("if(row->kind=='C' && row->box>=0 && row->box<focus_boards){"):]
        box = box[:box.index('VectorAdd(row->at,shift,at);along=DotProduct(delta,f);')]
        self.assertIn('(hit=focus_board_ray(focus_board_axis[row->box],at,eye,f))<0)continue;', box)
        self.assertIn('if(hit>0){', box)
        self.assertIn('placed_best=best;VectorCopy(eye,placed_eye);VectorCopy(f,placed_dir);VectorCopy(shift,placed_shift);',
                      placed)
        takes = body('aw_inventory.c', 'static int aim_takes(')
        self.assertIn('return AW_AimTakes(t,nearest,reach,best>=0,t>nearest && holds,t<=nearest && holds);', takes)
        holds = body('aw_inventory.c', 'static int focus_box_holds(')
        self.assertIn("row->kind!='C' || row->box<0 || row->box>=focus_boards", holds)
        self.assertIn('AW_BoxHolds(at,(const float (*)[3])focus_board_axis[row->box],point)', holds)
        # the box the use key's thing is aimed by gives way to a person or a door met inside it, and a plant to pick
        # nearer than the container (or inside its box) takes the use, the title and the action line
        self.assertIn('if(!aim_is_placed || placed_best<0 || placed_best>=focus_count || !(distance>=0))return 0;',
                      body('aw_inventory.c', 'int AW_PlacedAimHolds(float distance){'))
        self.assertIn('aim_is_placed=placed>=0 && (drop<0 || placed<=drop);',
                      body('aw_inventory.c', 'float AW_InventoryAimDistance(void){'))
        choice = body('aw_scene.c', 'static int focus_kind(void) {')
        for part in ('aim.actor_far>=0 && AW_PlacedAimHolds(aim.actor_near)', 'aim.door>=0 && AW_PlacedAimHolds(aim.door)',
                     'aim.hinged>=0 && AW_PlacedAimHolds(aim.hinged)'):
            self.assertIn(part, choice)
        self.assertLess(choice.index('aim.hinged=aw_hinged_aim?aw_hinged_aim():-1;'),
                        choice.index('AW_PlacedAimHolds(aim.hinged)'))
        self.assertLess(choice.index('aim.thing=-1;'), choice.index('focus_held_kind=AW_FocusChoose(&aim,focus_held_kind);'))
        use = body('aw_scene.c', 'int AW_SceneUse(void) {')
        self.assertIn('(focus_plant_first?((!aw_inventory_allowed || aw_inventory_allowed()) && AW_HarvestUse()) || '
                      'AW_InventoryUse():', use)
        draw = body('aw_scene.c', 'void AW_SceneDraw(void) {')
        # PLANT-PICK-DIRECT-DEFAULT-69: the AmiWind pick's plant line follows the same order (a mushroom nearer wins)
        self.assertEqual(draw.count('!focus_plant_first &&'), 3)
        self.assertIn('!focus_plant_first &&\n            (name=AW_PlacedPlantHint(&steal))!=NULL', draw)
        self.assertLess(draw.index('!focus_plant_first &&\n           (AW_InventoryFocus('), draw.index('AW_PlacedFocus(&focus_name,'))
        self.assertIn('!focus_plant_first &&\n            AW_ItemPrompt(take,sizeof(take),&steal)', draw)
        self.assertIn('WEAK int AW_PlacedAimHolds(float distance)', (ROOT / 'tests' / 'aga_hook_stubs.c').read_text(
            encoding='utf-8'))

    def test_the_rules_file_is_built(self):
        self.assertIn('aw_activate_rules.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))

    def test_the_container_aim_check_stands_within_reach_and_asks_the_use_test(self):
        # DBG-CONTAINER-AIM-OUT-OF-REACH-67: aw_placed container aim stood 40 units out over the floor (the eye 46 to 60
        # from the row's point, past the 48-unit reach) and looked 8 above the point; it said "Aimed at" whatever the
        # use would take. Now the eye is AW_AIM_EYE from the point (aw_activate_rules.c AW_AimEye, tested natively), the
        # use test (placed_target) is asked with that view, and "Aimed at" is said only when it takes this row.
        command = body('aw_inventory.c', 'void AW_ContainerCommand(void){')
        aim = command[command.index('if(!strcmp(a,"aim")){'):command.index('if((!strcmp(a,"take")')]
        self.assertIn('AW_AimEye(at,dx,dy,lifts[l],eye,&yaw,&pitch);', aim)
        self.assertNotIn('*40', aim)
        self.assertNotIn('+8', aim)
        self.assertIn('VectorCopy(p->v.angles,p->v.v_angle);', aim)
        self.assertLess(aim.index('VectorCopy(p->v.angles,p->v.v_angle);'), aim.index('got=placed_target();'))
        self.assertIn('if(got==(int)(row-focus_rows))', aim)
        self.assertLess(aim.index('if(got==(int)(row-focus_rows))'), aim.index('"Aimed at %s (%s %u): aw_view'))
        self.assertIn('from this view the use goes to row %d (%c %u %s), not to %s %u', aim)
        self.assertIn('from this view the use takes nothing', aim)
        self.assertIn('#define AW_AIM_EYE 24.0f', code('aw_activate.h'))


if __name__ == '__main__':
    unittest.main()
