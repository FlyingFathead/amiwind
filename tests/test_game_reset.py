# SPDX-License-Identifier: GPL-3.0-only
"""New Game and dbg restartgame reset every game state through one registry (engine/aga/src/aw_reset.c), and a failed
load brings the player back (aw_scene.c AW_SceneLoadFailed, aw_loadfail.c): the registry's rules natively
(tests/aga_reset_test.c) and the engine's wiring."""
import os
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class RegistryRules(unittest.TestCase):
    def test_every_reset_runs_and_a_surviving_state_is_named(self):
        native.NativeSourceTests().compile_run('aga_reset_test.c', [SRC / 'aw_reset.c'], cflags=UBSAN)


class EngineWiring(unittest.TestCase):
    def test_new_game_and_restart_share_the_registry(self):
        intro = code('aw_intro.c')
        self.assertIn('if(aw_game_reset)aw_game_reset(1);', intro)
        loadfail = code('aw_loadfail.c')
        self.assertIn('aw_game_reset=game_reset;', loadfail)
        self.assertIn('game_reset(0);', loadfail)               # dbg restartgame
        for name in ('story and globals', 'character', 'world change list', 'scene loads', 'message boxes',
                     'scripts and actors'):
            self.assertIn('AW_ResetRegister("%s",' % name, loadfail)
        self.assertIn('AW_ResetBootMark ();', code('host.c'))
        self.assertIn('aw_reset.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        self.assertTrue((ROOT / 'docs' / 'GAME_STATE_RESET.md').is_file())

    def test_new_game_reloads_the_scripts(self):
        # the menu New Game kept the interpreter's instances of the game before (the Census office's lights out, its
        # items not to be taken): the reset loads the interpreter again and resets what a save load resets
        host = code('aw_mwhost.c')
        body = host[host.index('void AW_MwscriptNewGameReset(void)'):]
        body = body[:body.index('\n}\n')]
        self.assertIn('actors_import(NULL,0);', body)
        self.assertIn('AW_MwvmLoad(resident,resident_bytes,&host)', body)
        self.assertIn('map_model=script_model=NULL;', body)

    def test_a_failed_load_goes_back(self):
        host = code('host.c')
        self.assertEqual(host.count('AW_SceneLoadFailed (string);'), 2)        # Host_Error and Host_EndGame
        self.assertIn('AW_SceneLoadFailed ("the map could not be spawned");', code('host_cmd.c'))
        scene = code('aw_scene.c')
        self.assertIn('load_from_capture(p,tp_cmd?AW_LOAD_TELEPORT:no_followers?AW_LOAD_SCRIPT:AW_LOAD_DOOR);', scene)
        self.assertIn('"Unable to teleport, see debug console with F10."', scene)
        self.assertIn('map_jump=3;', scene[scene.index('void AW_SceneLoadFailed'):])
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('|restartgame|aw_restart_game|', catalogue)
        self.assertIn('|loadfail|aw_load_fail|', catalogue)

    def test_dbg_version(self):
        # DBG-VERSION-62: dbg ver / dbg version print VERSION, the image's build stamp and CHIM_VERSION
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('|ver|aw_version_info|', catalogue)
        self.assertIn('|version|aw_version_info|', catalogue)
        loadfail = code('aw_loadfail.c')
        self.assertIn('Cmd_AddCommand("aw_version_info",version_command);', loadfail)
        body = loadfail[loadfail.index('static void version_command'):]
        for part in ('AMIWIND_VERSION', 'CHIM_VERSION', '"build-stamp.txt"'):
            self.assertIn(part, body)
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('| `dbg ver` | `dbg version` |', page)


if __name__ == '__main__':
    unittest.main()
