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
        self.compile_run('aga_ready_magic_test.c', [SRC / 'aw_hands.c'], defines=['AW_HANDS_HOST_TEST'],
                         cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

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
        self.assertIn('aw_magic_readied?-1:AW_InventoryEquippedWeaponType()', view)
        self.assertIn('AW_HandShowsWeapon(goal->_float==1,aw_magic_readied) && !(torch', code('aw_mwhost.c'))
        # with magic ready the attack button is the cast, taken before the fight sees it
        self.assertIn('if(!held)cast_now();', cast)


if __name__ == '__main__':
    unittest.main()
