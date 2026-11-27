# SPDX-License-Identifier: GPL-3.0-only
"""NPC-WEAPON-GRIP-WRONG-69: a held weapon, shield or torch is on the hand of the frame its actor is sent with.

The fight, the walk and the idle think set an actor's frame inside the layout's engine groups and pose its items from
it; just before the server sends the entities, the state pick moves every skeletal actor's frame into the group of its
weapon (aw_animkit.c AW_AnimPickPreSend) and gives the driver's frame back after the send. Since that pick came in
(v0.0.54) the body was drawn at the picked frame while its weapon stayed where the hand of the driver's frame was: up
to an arm's length off, for every weapon class. The items are now posed again at the frame that goes out
(aw_items.c AW_ItemsPreSend, called between the pick and the send). The original hangs the weapon on its bone's node,
so it moves with the bone every frame (OpenMW apps/openmw/mwrender/npcanimation.cpp, actoranimation.cpp attachMesh)."""
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

import test_aga_native_source as native  # noqa: E402

UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class SentFrameNativeTests(unittest.TestCase):
    def test_every_weapon_class_keeps_its_grip_on_the_hand_of_the_sent_frame(self):
        # one server frame per attack, idle and run frame of each class (one-handed, two-handed close and wide, bow,
        # crossbow, thrown): the order before the fix leaves the weapon over a unit off its hand in every class, the
        # sent-frame pose under 0.01 units; the rule's own cases; the stance groups without the storm arm
        native.NativeSourceTests().compile_run('aga_items_sent_frame_test.c', [SRC / 'aw_items.c'],
                                               defines=('AW_ITEMS_HOST_TEST',), cflags=UBSAN)


class SentFrameWiringTests(unittest.TestCase):
    def test_the_send_poses_the_items_after_the_pick_and_before_the_frames_come_back(self):
        send = body((SRC / 'sv_main.c').read_text(encoding='utf-8'), 'void SV_SendClientMessages (void)')
        pick, items, back = (send.index(part) for part in ('AW_AnimPickPreSend ();', 'AW_ItemsPreSend ();',
                                                           'AW_AnimPickPostSend ();'))
        self.assertLess(pick, items)
        self.assertLess(items, send.index('SV_UpdateToReliableMessages ();'))      # before any client is written
        self.assertLess(items, back)

    def test_every_shown_set_and_every_carried_light_is_followed(self):
        items = code('aw_items.c')
        presend = body(items, 'void AW_ItemsPreSend(void) {')
        # every set between its show and its hide, by the rule the fixture runs; a set that cannot be posed is hidden
        self.assertIn('AW_ItemsStale(shown[i].frame,shown[i].at,(int)a->v.frame,a->v.origin,a->v.angles[1])', presend)
        self.assertIn('AW_ItemsUpdate(a,items);', presend)
        self.assertIn('AW_ItemsStale(carrier_posed[i].frame,carrier_posed[i].at,(int)a->v.frame,a->v.origin,'
                      'a->v.angles[1])', presend)
        self.assertIn('carried_pose(i);', presend)
        show = body(items, 'int AW_ItemsShow(edict_t *actor,edict_t *out[AW_ITEMS_KINDS]) {')
        self.assertIn('shown[shown_count].items=out;', show)
        self.assertIn('shown_drop(items);', body(items, 'void AW_ItemsHide(edict_t *items[AW_ITEMS_KINDS]) {'))
        update = body(items, 'void AW_ItemsUpdate(edict_t *actor,edict_t *items[AW_ITEMS_KINDS]) {')
        self.assertIn('posed_at(actor,&shown[k].frame,shown[k].at);', update)      # what each set was posed at
        # a new server and a new world start with no set (the edicts of the last one are gone)
        self.assertIn('shown_count=0;memset(shown,0,sizeof(shown));', body(items, 'void AW_ItemsSceneReset(void) {'))
        self.assertIn('shown_count=0;', body(items, 'static void level_check(void) {'))
        # as many sets as can be shown: the fight's slots and the animation stage's cast
        combat = (SRC / 'aw_combat.c').read_text(encoding='utf-8')
        slots = int(re.search(r'^#define FIGHTS (\d+)', combat, re.M).group(1))
        shown = int(re.search(r'^#define AW_ITEMS_SHOWN (\d+)', (SRC / 'aw_items.c').read_text(encoding='utf-8'),
                              re.M).group(1))
        self.assertGreaterEqual(shown, slots + 8)

    def test_no_storm_arm_in_a_weapon_stance_group(self):
        storm = body(code('aw_items.c'), 'static int storm_frame(const aw_skel_table_t *tab,int frame) {')
        self.assertLess(storm.index('if(AW_ItemsStanceGroup(stance))break;'), storm.index('"idle",4'))

    def test_the_pick_status_reports_the_sets_posed_again(self):
        self.assertIn('AW_ItemsPreSendCount(&sets,&lights,&far_units,&shown_now);', code('aw_animkit.c'))


if __name__ == '__main__':
    unittest.main()
