# SPDX-License-Identifier: GPL-3.0-only
"""The sneak key and the sneaking body (PLAYER-SNEAK-NOT-HELD-69).

1. The key toggles: one press of the sneak key starts sneaking, the next press ends it (aw_sneak_toggle 1, saved, the
   default; 0 = sneak while the key is held, as since SNEAK-58 in v0.0.58 and as the original's PC default). Rule from
   OpenMW 0.53 files/data/scripts/omw/input/playercontrols.lua (the ToggleSneak trigger flips the sneak on each press
   while movement is allowed) and settings.lua (toggleSneak), read not copied. The state itself and its rules:
   tests/aga_move_test.c; the Options row: tests/aga_menu_test.c.
2. The third-person body plays its sneak gaits at the speed over the sneak animation's own speed (OpenMW 0.53
   character.cpp refreshMovementAnims; the original's third-person sneak gait moves 33.5452 original units/s,
   character.cpp:745-747). It played them at the speed over the WALK's own speed, 4.6 times too slowly at a sneak's
   pace: the body glided. The rate rule: tests/aga_animpick_test.c.
These checks fail on the code before the fix."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
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


class SneakKey(unittest.TestCase):
    def test_a_fresh_press_in_play_toggles_the_sneak(self):
        down = body(code('cl_input.c'), 'void IN_SneakDown(void)')
        # the button's state before the press: a key held down (its repeats) is no second press
        self.assertIn('int was=in_sneak.state&1;', down)
        self.assertLess(down.index('int was=in_sneak.state&1;'), down.index('KeyDown(&in_sneak);'))
        self.assertIn('if(!was && (in_sneak.state&1) && key_dest==key_game && AW_ControlAllowed(AW_CONTROL_PLAYER))'
                      'AW_MoveSneakPress();', down)
        # the key's release changes no toggled sneak
        up = body(code('cl_input.c'), 'void IN_SneakUp(void)')
        self.assertNotIn('AW_MoveSneak', up)

    def test_the_sneak_reads_the_toggled_state_or_the_held_key(self):
        move = code('aw_move.c')
        self.assertIn('static cvar_t sneak_toggle={"aw_sneak_toggle","1",true};', move)
        self.assertIn('Cvar_RegisterVariable(&sneak_toggle);', body(move, 'void AW_MoveInit(void)'))
        self.assertIn('return sneak_toggle.value?sneak_on:(in_sneak.state&1)!=0;', body(move, 'static int sneak_key(void)'))
        self.assertIn('sneak_key() || aw_move_force_sneak', body(move, 'int AW_MoveSneaking(void)'))
        press = body(move, 'void AW_MoveSneakPress(void)')
        self.assertIn('if(!sneak_toggle.value){sneak_on=0;return;}', press)
        self.assertIn('MOVETYPE_NOCLIP)return;', press)     # in debug noclip the key is fast flight
        self.assertIn('sneak_on=!sneak_on;', press)

    def test_new_game_clears_the_toggled_sneak(self):
        loadfail = code('aw_loadfail.c')
        self.assertIn('AW_ResetRegister("the toggled sneak",reset_sneak,digest_sneak);', loadfail)
        self.assertIn('AW_MoveSneakSet(0);', body(loadfail, 'static void reset_sneak(int new_game)'))
        self.assertIn('AW_MoveSneakOn()', body(loadfail, 'static unsigned long digest_sneak(void)'))

    def test_the_options_page_and_the_console_show_one_value(self):
        menu = code('aw_menu.c')
        self.assertIn('Cvar_SetValue("aw_sneak_toggle",Cvar_VariableValue("aw_sneak_toggle")?0:1);',
                      body(menu, 'static void combat_toggle(int row)'))
        self.assertIn('"Sneak key: Toggle":"Sneak key: Hold"', body(menu, 'static void combat_line(int row,char *line)'))

    def test_the_key_stays_ctrl(self):
        keymaps = (ROOT / 'config/keymaps.cfg').read_text(encoding='ascii')
        self.assertIn('bind "CTRL" +aw_sneak', keymaps)


class SneakingBody(unittest.TestCase):
    def test_a_sneak_gait_plays_at_the_sneak_animations_own_rate(self):
        view = code('aw_view.c')
        stance = body(view, 'static int body_stance_frame(')
        self.assertIn('if(s.sneak && s.move!=AW_PM_NONE)rate=AW_PickSneakRate(speed)*aw_anim_kit_speed;', stance)
        # the rate is set before the frame advances by it
        self.assertLess(stance.index('AW_PickSneakRate(speed)'), stance.index('dt*stance.rate'))
        # the body's own ground speed reaches it
        self.assertIn('body_stance_frame(p,group,air>=0,dt,rate,speed)', body(view, 'entity_t *AW_ViewBody(entity_t *ent)'))

    def test_the_body_reads_the_players_own_velocity(self):
        # PLAYER-GAIT-RATE-VELOCITY-STEPS-69: cl.velocity is the server's copy in steps of 16 units (sv_main.c
        # velocity/16, cl_parse.c x16): a sneak at 40.7 read as 32. The body's speed is the local edict's own velocity.
        view = code('aw_view.c')
        body_fn = body(view, 'entity_t *AW_ViewBody(entity_t *ent)')
        self.assertIn('const float *v=p?p->v.velocity:cl.velocity;', body_fn)
        self.assertIn('speed=(float)sqrt(v[0]*v[0]+v[1]*v[1]+(p && p->v.waterlevel>=2?v[2]*v[2]:0));', body_fn)
        self.assertNotIn('speed=(float)sqrt(cl.velocity[0]', body_fn)
        self.assertLess(body_fn.index('const float *v='), body_fn.index('AW_AnimPlayerMoveGroup(&body_anim,speed'))
        # the copy the server sends really is in steps of 16 (the reason)
        self.assertIn('MSG_WriteChar (msg, ent->v.velocity[i]/16);', code('sv_main.c'))
        self.assertIn('cl.mvelocity[0][i] = MSG_ReadChar()*16;', code('cl_parse.c'))

    def test_the_sneak_animations_own_speed_is_the_originals(self):
        head = (SRC / 'aw_animpick.h').read_text(encoding='latin-1')
        # 33.5452 original units/s (OpenMW 0.53 character.cpp:745-747) at the world's 0.25 scale
        m = re.search(r'#define AW_PICK_SNEAK_SPEED ([0-9.]+)f', head)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(float(m.group(1)), 33.5452 * .25, places=3)


if __name__ == '__main__':
    unittest.main()
