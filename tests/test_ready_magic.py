# SPDX-License-Identifier: GPL-3.0-only
"""READY-MAGIC-SHOWS-WEAPON-65: R readies magic as the spell stance (empty hands up, no weapon), F the weapon; the two
are exclusive, as in the original. The pure rule is host-built; the engine wiring is checked in the source."""
from pathlib import Path
import os
import shutil
import unittest
import test_aga_native_source as native

SRC = Path(__file__).resolve().parents[1] / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


class ReadyMagicStance(unittest.TestCase):
    compile_run = native.NativeSourceTests.compile_run

    @unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
    @unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
    def test_weapon_and_magic_keys_are_exclusive_stances(self):
        # with the pure part of aw_hand_models.c (AW_HandView, AW_HandCarriesLeft; mathlib.c for its block view math)
        self.compile_run('aga_ready_magic_test.c', [SRC / 'aw_hands.c', SRC / 'aw_hand_models.c', SRC / 'mathlib.c'],
                         defines=['AW_HANDS_HOST_TEST', 'AW_BLOCK_HOST_TEST'],
                         cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_readied_magic_ignores_what_is_equipped(self):
        # v0.0.66 (decided for the project, 14 November 2026): R shows the open hands whatever is equipped. The arms are
        # chosen by AW_HandView, magic first (v0.0.66-dev1 checked the lit torch and a held light before the spell
        # stance, so with either in the left hand R showed the right hand's fist); the torch and a held light are put
        # away while magic is ready (not drawn, no light cast), the shield too (the guard and the third-person body)
        hands, torch, view = code('aw_hand_models.c'), code('aw_torch.c'), code('aw_view.c')
        # LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67: the light's view while it is held, lit or put out by V
        self.assertIn('view=AW_HandView(spell_shown(),AW_TorchEquipped(),AW_HeldLightShown()!=NULL);', hands)
        self.assertIn('equipped=view==AW_HAND_VIEW_TORCH;', hands)
        self.assertIn('if(view==AW_HAND_VIEW_LIGHT){', hands)
        self.assertIn('if(view==AW_HAND_VIEW_SPELL && aw_hand_parts_apply(race,female,AW_HAND_SPELL_STANCE+spell_range(),frame)){',
                      hands)
        self.assertIn('if(view==AW_HAND_VIEW_SPELL && spell_arms(index)){', hands)
        self.assertNotIn('if(!equipped && AW_HeldLight()){', hands)
        # the order in the function: the view is chosen before any stance is drawn
        apply = hands[hands.index('int AW_HandModelsApply(void)'):]
        self.assertLess(apply.index('view=AW_HandView('), apply.index('aw_hand_parts_apply(race,female,AW_HAND_LIGHT_STANCE'))
        # the shield guard yields to readied magic
        block = hands[hands.index('int AW_HandBlockApply(void)'):hands.index('int AW_HandBlockItemApply(void)')]
        self.assertIn('if(aw_hand_weapon_hidden && !AW_HandCarriesLeft(aw_hand_weapon_hidden())){', block)
        self.assertLess(block.index('AW_HandCarriesLeft'), block.index('AW_TorchEquipped()'))
        # the carried light is put away at its one gate (the torch's arms, the light stance, the flames, the light)
        lit = torch[torch.index('static int light_lit(void)'):torch.index('int AW_TorchEquipped(void)')]
        self.assertIn('if(aw_torch_put_away && aw_torch_put_away())return 0;', lit)
        self.assertIn('int (*aw_torch_put_away)(void);', torch)
        self.assertIn('The light is put away while magic is ready', torch)
        self.assertIn('extern int (*aw_torch_put_away)(void);', code('aw_torch.h'))
        # magic ready first (1); LIGHT-AND-WEAPON-REPLACE-EACH-OTHER-67 adds a drawn two-handed weapon (2)
        start = view.index('static int left_put_away(void) {')
        away = view[start:view.index('\n}', start)]
        self.assertIn('if(!AW_HandCarriesLeft(aw_magic_readied))return 1;', away)
        self.assertIn('aw_torch_put_away=left_put_away;', view)
        self.assertIn('!AW_HandCarriesLeft(aw_magic_readied) || (drawn && right && AW_TWO_HANDED(right->weapon))', view)

    def test_engine_uses_the_one_rule(self):
        cast = code('aw_cast.c')
        self.assertIn('#define ready aw_magic_readied', cast)
        self.assertIn('AW_HandReadyPress(AW_READY_MAGIC_KEY,&g,&ready);', cast)
        self.assertIn('AW_ResetRegister("cast ready",ready_reset,NULL);', cast)
        self.assertIn('AW_HandReadyPress(AW_READY_WEAPON_KEY,&g,&aw_magic_readied);', code('aw_hands.c'))
        # the first-person weapon is not drawn in the spell stance; third person and the stance picker likewise
        self.assertIn('if(aw_hand_weapon_hidden && aw_hand_weapon_hidden())return 0;', code('aw_hand_models.c'))
        view = code('aw_view.c')
        self.assertIn('aw_hand_weapon_hidden=weapon_hidden;', view)
        self.assertIn('drawn=goal && AW_HandShowsWeapon(goal->_float==1,aw_magic_readied);', view)
        # PLAYER-CASTING-59: the third-person stance is the original's spell stance, the cast by the spell's range
        self.assertIn('aw_magic_readied?AW_PW_SPELL:AW_InventoryEquippedWeaponType()', view)
        self.assertIn('if(aw_magic_readied)s.range=', view)
        self.assertIn('AW_HandShowsWeapon(goal->_float==1,aw_magic_readied) && !(torch', code('aw_mwhost.c'))
        # with magic ready the attack button is the cast, taken before the fight sees it
        self.assertIn('if(!held)cast_now();', cast)

    def test_first_person_spell_stance_and_the_release(self):
        # PLAYER-CASTING-59: the arms from parts at the spell stance of the range (AW_HAND_SPELL_STANCE + range),
        # the baked arms' <stem>_sp.mdl, the hands' cast started by the cast and the spell sent at the release
        hands, cast = code('aw_hand_models.c'), code('aw_cast.c')
        self.assertIn('aw_hand_parts_apply(race,female,AW_HAND_SPELL_STANCE+spell_range(),frame)', hands)
        self.assertIn('strcpy(path+n-4,"_sp.mdl");', hands)
        self.assertIn('delay=AW_HandsCastStart()?AW_HandCastReleaseNow(0):0;', cast)
        self.assertIn('if(pending && sv.time>=release_at)cast_release();', cast)
        self.assertIn('pending=0;release_at=0;memset(looks,0,sizeof(looks));aw_magic_cast_range=AW_RANGE_TARGET;', cast)   # New Game resets it
        self.assertIn('aw_magic_cast_range=(int)spell.e[0].range;', cast)
        header = code('aw_hand_models.h')
        self.assertIn('#define AW_HAND_SPELL_STANCE 8', header)
        self.assertIn('#define AW_HAND_CAST_RELEASE_FRAME 6', header)
        import sys
        sys.path.insert(0, str(SRC.parents[2] / 'tools'))
        import prepare_hands
        self.assertEqual(prepare_hands.SPELL_RELEASE_FRAME, 6)


if __name__ == '__main__':
    unittest.main()
