# SPDX-License-Identifier: GPL-3.0-only
"""The fists in third person (PLAYER-PUNCH-THIRDPERSON-39, TP-DRAW-WEAPON-LAGS-67): raising, striking and lowering the
bare hands play the original's handtohand group on the assembled body (equip, the attack by type, unequip), on the
first-person hands' clock, as a drawn weapon plays its own (OpenMW 0.51 character.cpp updateWeaponState, read not
copied: the hand-to-hand weapon type's group like any weapon's). Since the assembled body (61b64c83f, v0.0.59-dev5)
the baked body's hand layers were not there and the stance pick took real weapons only, so the fists had no
third-person draw, punch or lower: the swing was heard while the body did not move. The group choice itself:
tests/aga_animpick_test.c (fails on that pick). These checks fail on that code."""
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


class Fists(unittest.TestCase):
    def test_the_bare_hands_rising_striking_and_lowering_take_the_hand_to_hand_stance(self):
        stance = body(code('aw_view.c'), 'static int body_stance_frame(')
        self.assertIn('if(in.weapon==AW_PW_NONE && (hand==1 || hand==3 || hand==4))in.weapon=AW_PW_HANDTOHAND;', stance)
        # before the pick, after the weapon in the right hand (a drawn weapon keeps its own group)
        self.assertLess(stance.index('AW_InventoryEquippedWeaponType()'), stance.index('in.weapon=AW_PW_HANDTOHAND'))
        self.assertLess(stance.index('in.weapon=AW_PW_HANDTOHAND'), stance.index('AW_PickPlayerBody(&in,&s)'))
        # the draw, the strike and the lowering follow the hands' clock
        for clip in ('AW_HAND_DRAW', 'AW_HAND_LOWER', 'AW_HAND_PUNCH'):
            self.assertIn('hand_fraction(p,%s)' % clip, stance)

    def test_the_pick_takes_the_bare_hands_as_a_stance(self):
        rules = (SRC / 'aw_animpick_rules.inc').read_text(encoding='latin-1')
        state = body(rules, 'int AW_PickPlayerState(')
        self.assertIn('weapon==AW_PW_HANDTOHAND', state)


if __name__ == '__main__':
    unittest.main()
