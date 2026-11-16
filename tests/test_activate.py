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
        self.assertIn("if(row->kind=='I' && row->live && view_ref && row->reference==view_ref){", placed)
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
