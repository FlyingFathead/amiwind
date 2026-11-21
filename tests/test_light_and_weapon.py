# SPDX-License-Identifier: GPL-3.0-only
"""A carried light and a one-handed weapon held together (LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67; decided for the
project 2026-11-20): both are drawn, in first and third person and in the inventory picture, the light lit by default;
F readies both, V after F puts out or lights only the light (with a notice), and a two-handed weapon or readied magic
puts the light away, as the original (OpenMW 0.51, read not copied: mwclass/light.cpp canBeEquipped,
mwrender/actoranimation.cpp updateCarriedLeftVisible, mwrender/characterpreview.cpp).

Before: in first person the held light took the hands' place (the light stance of d98f71c1c, v0.0.61: the bare hands
with the left arm on the torch group) and the weapon was drawn only while the light was out; since 06e9c4a7 (v0.0.65,
TORCH-HAND-TO-HAND-64) F left the light out and an unlit light was not drawn at all; in third person a lit light took
the weapon's stance away (the weapon hung in an idle arm); the inventory picture drew only a shield in the left hand.
Every check below fails on that code. The behaviour of the hands and the light: tests/aga_torch_qc_test.c
(light_lit_by_default) and tests/aga_torch_test.c."""
import re
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


class FirstPerson(unittest.TestCase):
    def test_a_one_handed_weapon_and_the_light_are_drawn_together(self):
        apply = body(code('aw_hand_models.c'), 'int AW_HandModelsApply(void)')
        # the light's view follows the light held (lit or put out), not only the lit one
        self.assertIn('view=AW_HandView(spell_shown(),AW_TorchEquipped(),AW_HeldLightShown()!=NULL);', apply)
        both = apply[apply.index('if(view==AW_HAND_VIEW_LIGHT && aw_hand_parts_apply && aw_hand_parts_left_light'):]
        both = both[:both.index('weapon_visible=0;')]
        # the weapon's own stance, a one-handed one, with the left arm on the light stance; the weapon and the light both
        # ride that model (AW_HandWeaponItemApply and AW_HandLightItemApply draw on weapon_base and light_base)
        self.assertIn('hand_weapon(index,0)', both)
        self.assertIn('AW_HandStanceOneHanded(weapon_stance)', both)
        self.assertIn('aw_hand_parts_apply(race,female,stance,frame) && aw_hand_parts_left_light(frame)', both)
        self.assertIn('weapon_base=cl.viewent.model;', both)
        self.assertIn('light_visible=1;light_base=cl.viewent.model;', both)
        # it comes before the light stance alone (the bare hands with the light)
        self.assertLess(apply.index('aw_hand_parts_left_light(frame)'),
                        apply.index('aw_hand_parts_apply(race,female,AW_HAND_LIGHT_STANCE'))
        light = body(code('aw_hand_models.c'), 'int AW_HandLightItemApply(void)')
        self.assertIn('AW_HeldLightShown()', light)

    def test_the_left_arm_takes_the_light_stance_in_the_drawing_and_in_the_bone_tags(self):
        view = code('aw_view.c')
        left = body(view, 'static int hand_parts_left_light(int frame)')
        self.assertIn('AW_SkelLeftArmRoot(hparts_table,hparts.shield_bone,hparts.weapon_bone)', left)
        self.assertIn('hparts_left_layer=AW_HAND_LIGHT_STANCE*HAND_PART_FRAMES+frame;', left)
        self.assertIn('hparts_left_layer=-1;', body(view, 'static int hand_parts_apply('))   # one frame's layer only
        tag = body(view, 'static int hand_parts_bone_tag(')
        self.assertIn('AW_SkelPoseLayer(hparts_table,(float)hparts_frame,(float)hparts_left_layer,hparts_left_root,world);', tag)
        layer = body(view, 'static int player_light_layer(')
        self.assertIn('skel_table==(const void *)hparts_table', layer)
        self.assertIn('*layer_frame=(float)hparts_left_layer;*root=hparts_left_root;return 1;', layer)
        # the first-person case is not held back by the third-person camera test
        self.assertLess(layer.index('hparts_table'), layer.index('chase_active.value'))
        self.assertIn('aw_hand_parts_left_light=hand_parts_left_light;', view)


class ThirdPersonAndPicture(unittest.TestCase):
    def test_the_light_is_drawn_while_held_and_the_weapon_keeps_its_stance(self):
        view = code('aw_view.c')
        self.assertIn('light=AW_HeldLightShown();', body(view, 'static void parts_draws('))
        self.assertIn('held=AW_HeldLightShown()!=NULL;', body(view, 'static int player_light_layer('))
        # a lit light (aw_torch 1) no longer takes the stance, the fists or the hand layer away: only the baked torch body
        for head in ('static int body_stance_frame(', 'static int body_fists_ready(', 'static int body_hand_layer('):
            fn = body(view, head)
            self.assertNotIn('"aw_torch"', fn, head)
            self.assertIn('body_torch', fn, head)

    def test_a_two_handed_weapon_puts_the_light_away(self):
        away = body(code('aw_view.c'), 'static int left_put_away(void) {')
        self.assertIn('AW_TWO_HANDED(right.weapon)?2:0', away)
        self.assertIn('goal->_float==1', away)            # only while it is drawn
        torch = code('aw_torch.c')
        self.assertIn('a two-handed weapon is drawn', body(torch, 'static void toggle(void)'))

    def test_the_inventory_picture_holds_the_light(self):
        items = body(code('aw_view.c'), 'static int parts_inventory_items(')
        self.assertIn('if(kind && (item.flags&AW_INV_LIGHT))light=AW_HeldLightCarried();', items)
        self.assertIn('AW_BlockCompose(tag,base,light->offset,origins[n],angles[n]);', items)


class Keys(unittest.TestCase):
    def test_f_lights_the_light_and_v_after_f_says_what_it_did(self):
        torch = code('aw_torch.c')
        item = body(torch, 'static void item_torch(void)')
        self.assertIn('if(lit && raised && (!was_lit || !was_raised))v->_float=1;', item)
        self.assertIn('if(aw_torch_notice)aw_torch_notice(v->_float!=0);', body(torch, 'static void toggle(void)'))
        debug = code('aw_debug_torch.c')
        notice = body(debug, 'int AW_LightNoticeText(')
        self.assertIn('"Put out %s. (%s to re-ignite while unsheathed)"', notice)
        self.assertIn('"Re-ignited %s. (%s to put it out)"', notice)
        # the key from the player's binding of the light key, the text through the box pipeline
        shown = body(debug, 'static void light_notice(int lit)')
        self.assertIn('AW_TextBoundKeyForCommand("aw_torch")', shown)
        self.assertIn('AW_MsgBoxShow(text,NULL,0);', shown)
        self.assertIn('aw_torch_notice=light_notice;', debug)


if __name__ == '__main__':
    unittest.main()
