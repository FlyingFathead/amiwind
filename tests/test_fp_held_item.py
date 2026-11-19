# SPDX-License-Identifier: GPL-3.0-only
"""The held item in the hand in first person (FP-TORCH-HAND-REGRESSION-67, register FP-TORCH-OUT-OF-HAND-67): one
placement for both hands, each item on its own hand's bone of the first-person arms it is drawn with, and no offset
from the view (aw_hand_models.h AW_HandItemPlace). Since cd67bdcf (v0.0.61) a held light was also moved 4 units
forward along the view, while the arms from parts it rides were not: on the v0.0.67-dev2 image its grip sat 4.00 units
from the shield bone and 2.97 from the left hand bone (the torch's nearest vertex 4.19 from the hand, the lantern's
3.17, a candle's 1.89; without the push 1.71, 0.13 and 0.07, as in third person: 1.93, 0.16, 0.18). These checks fail
on that placement."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
SRC = ROOT / 'engine/aga/src'


def code(name):
    text = (SRC / name).read_text(encoding='latin-1')
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def body(text, head):
    """The braces' body of the C function whose definition starts with HEAD."""
    start = text.index(head)
    at = text.index('{', start)
    depth = 0
    for i in range(at, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if not depth:
            return text[at:i + 1]
    raise ValueError('unbalanced ' + head)


class OnePlacement(unittest.TestCase):
    def test_the_light_is_placed_on_the_left_hand_bone_and_nothing_else(self):
        hands = code('aw_hand_models.c')
        light = body(hands, 'int AW_HandLightItemApply(void)')
        self.assertIn('hand_item_on_bone(AW_HAND_LEFT,l->offset,light_pose,light_pose+3)', light)
        # no other change to the light's place: no push along the view, no second composition
        self.assertNotRegex(light, r'light_pose\[[^\]]*\]\s*[-+*/]?=')
        self.assertNotIn('AngleVectors', light)
        self.assertNotIn('AW_BlockCompose', light)
        for name in os.listdir(SRC):
            if name.endswith(('.c', '.h')):
                self.assertNotIn('AW_HAND_LIGHT_FORWARD', code(name), name)

    def test_the_weapon_on_the_arms_from_parts_takes_the_same_placement(self):
        hands = code('aw_hand_models.c')
        weapon = body(hands, 'int AW_HandWeaponItemApply(void)')
        self.assertIn('hand_item_on_bone(AW_HAND_RIGHT,NULL,origin,angles)', weapon)
        self.assertIn('weapon_parts=1;', hands)                       # set where the weapon rides the parts
        place = body(hands, 'static int hand_item_on_bone(')
        self.assertIn('aw_hand_parts_bone_tag(hand,tag)', place)
        self.assertIn('AW_HandItemPlace(cl.viewent.origin,cl.viewent.angles,tag,carried,origin,angles);', place)

    def test_the_bone_is_the_arms_own_at_the_frame_drawn(self):
        view = code('aw_view.c')
        tag = body(view, 'static int hand_parts_bone_tag(int hand,float tag[6])')
        self.assertIn('hand==AW_HAND_LEFT?hparts.shield_bone:hparts.weapon_bone', tag)
        self.assertIn('AW_SkelPose(hparts_table,(float)hparts_frame,world)', tag)
        self.assertIn('scale[0]=scale[1]=w*.25f;scale[2]=h*.25f;', tag)
        self.assertIn('aw_hand_parts_bone_tag=hand_parts_bone_tag;', view)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class GripOnTheBone(unittest.TestCase):
    def test_the_grip_lands_on_the_bone_for_every_view_and_pose(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(
            self, 'aga_held_item_test.c', [SRC / 'aw_hand_models.c', SRC / 'mathlib.c'],
            defines=['AW_BLOCK_HOST_TEST'], cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])


if __name__ == '__main__':
    unittest.main()
