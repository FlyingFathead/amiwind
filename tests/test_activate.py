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
        # the prompt and the name under the view (aw_scene.c npc_target), E (pr_cmds.c aw_npctarget) and the body's
        # search (aw_corpse.c) all go through AW_ActivateActor; the plain actor test stays for combat and spells
        self.assertIn('cached=AW_ActivateActor(p,cl.viewangles);', code('aw_scene.c'))
        self.assertIn('AW_ActivateActor(player,player->v.v_angle)', body('pr_cmds.c', 'static void PF_aw_npctarget('))
        self.assertIn('AW_ActivateActor(p,p->v.v_angle)', body('aw_corpse.c', 'static edict_t *corpse_target('))
        self.assertNotIn('AW_ActivateActor', code('aw_combat.c'))

    def test_the_choice_weighs_the_item_and_the_plant_against_the_actors_box(self):
        choice = body('aw_scene.c', 'edict_t *AW_ActivateActor(')
        self.assertIn('AW_InventoryAimDistance()', choice)
        self.assertIn('AW_HarvestAimDistance()', choice)
        self.assertIn('AW_ActivateItemFirst(AW_ActivateNearest(', choice)
        # the actor test keeps where the ray enters and leaves the chosen actor's box
        target = body('aw_scene.c', 'edict_t *AW_NPCTargetReach(')
        self.assertIn('AW_RayBox(end,ray,fmins,fmaxs,&lo,&hi) && lo<limit){limit=lo;best=e;npc_aim_near=lo;npc_aim_far=hi;}',
                      target)

    def test_an_actors_own_focus_row_never_hides_an_item(self):
        placed = body('aw_inventory.c', 'static int placed_target(void){')
        self.assertIn("if(row->kind=='A')continue;", placed)
        self.assertIn("(focus_rows[best].kind=='I' || focus_rows[best].kind=='C'))placed_aim=nearest;", placed)

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
        self.assertIn('if(rank>nearest)continue;', placed)
        self.assertIn('nearest=rank;best=i;', placed)
        self.assertNotIn('nearest=along;best=i;', placed)
        view = body('aw_inventory.c', 'static unsigned view_reference(')
        self.assertIn('tr=SV_Move(eye,vec3_origin,vec3_origin,end,MOVE_NOMONSTERS,p);', view)
        self.assertIn('GetEdictFieldValue(tr.ent,"aw_ref")', view)
        # the aim report says what the ray meets and always lists the aimed row
        report = body('aw_inventory.c', 'void AW_PlacedAimReport(void){')
        self.assertIn('the view ray meets reference %u first', report)
        self.assertIn('if(shown>=12 && i!=best)continue;', report)

    def test_the_rules_file_is_built(self):
        self.assertIn('aw_activate_rules.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
