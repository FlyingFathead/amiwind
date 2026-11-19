# SPDX-License-Identifier: GPL-3.0-only
"""The light test and the item tester, one tool (LIGHTTEST-MAP-67, DBG-CYCLEITEMS-67, docs/ITEM_CYCLING.md): dbg
lighttest enters the dark corridor with the game's scripts paused and nothing over the world but the held items' line,
dbg lighttest 1 walks it for 20 s with a look down at the hands; dbg cycleitems reads the holdable item index as
tools/holdable_items.py writes it, goes through every item in the maintainer's order (the hands empty, the item held,
the walk, its attack where it has one), checks the grip in every frame, and shows its line only while it runs."""
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
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='latin-1'), flags=re.S)


def body(text, start):
    at = text.index(start)
    return text[at:text.index('\n}\n', at)]


class Wiring(unittest.TestCase):
    def test_the_index_the_builder_writes_is_the_one_the_engine_reads(self):
        import holdable_items as H
        header = (SRC / 'aw_cycleitems.h').read_text(encoding='latin-1')
        self.assertIn('#define AW_HOLDABLE_PATH "%s"' % H.PATH, header)
        self.assertIn('memcmp(index_text,"%s\\n",6)' % H.FORMAT, code('aw_cycleitems.c'))
        # the actions with an attack are exactly the weapons' (holdable_items.WEAPONS)
        no_attack = {'none', 'block', 'pickprobe'}
        self.assertFalse(no_attack & {v[2] for v in H.WEAPONS.values()})
        for word in no_attack:
            self.assertIn('strcmp(h->action,"%s")' % word, code('aw_cycleitems.c'))

    def test_his_order_and_the_hooks(self):
        tester = code('aw_cycleitems.c')
        frame = body(tester, 'void AW_CycleItemsFrame(void)')
        order = [frame.index('case AW_CYCLE_%s:' % s) for s in ('EMPTY', 'HOLD', 'WALK', 'ACTION')]
        self.assertEqual(order, sorted(order))
        self.assertIn('measure();', frame)                                   # the grip in every frame
        self.assertIn('walk_begin();', frame[frame.index('case AW_CYCLE_HOLD:'):frame.index('case AW_CYCLE_WALK:')])
        self.assertIn('AW_GalleryLightTestCenter();', body(tester, 'static void begin_item(void)'))
        self.assertIn('AW_CycleItemsFrame();', code('aw_animkit.c'))
        self.assertIn('AW_CycleItemsInit();', code('aw_debug.c'))
        screen = code('screen.c')
        self.assertLess(screen.index('AW_FpsDraw();'), screen.index('AW_CycleItemsDraw();'))
        draw = body(tester, 'void AW_CycleItemsDraw(void)')
        self.assertIn('if(running)', draw)
        self.assertIn('else if(AW_LightTestActive() && held_text[0])', draw)  # never in normal play
        self.assertIn('else return;', draw)
        self.assertIn('aw_cycleitems.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))
        commands = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('PLAYTESTING|cycleitems|aw_cycleitems|', commands)
        self.assertIn('PLAYTESTING|lighttest|aw_lighttest|', commands)

    def test_the_walk_presses_forward_and_lets_go(self):
        tester = code('aw_cycleitems.c')
        self.assertIn('Cbuf_AddText("+forward\\n");', body(tester, 'static void walk_begin(void)'))
        self.assertIn('Cbuf_AddText("-forward\\n");', body(tester, 'static void walk_end(const char *why)'))
        walk = body(tester, 'static void walk_frame(void)')
        self.assertIn('if(t>=AW_LIGHTWALK_S){walk_end(NULL);return;}', walk)
        self.assertIn('cl.viewangles[PITCH]=AW_LightWalkPitch((float)t);', walk)
        self.assertIn('walk_end("ended: left the corridor")', walk)
        self.assertIn('Cmd_AddCommand("aw_lighttest",lighttest_command);', tester)

    def test_the_corridor_pauses_the_scripts_and_draws_nothing_over_the_world(self):
        tester = code('aw_cycleitems.c')
        self.assertIn('static cvar_t lighttest_scripts={"aw_lighttest_scripts","0"};', tester)
        self.assertIn('return AW_LightTestActive() && !lighttest_scripts.value;', tester)
        self.assertIn('aw_mwscript_paused=scripts_paused;', tester)
        tick = body(code('aw_mwhost.c'), 'void AW_MwscriptTick(float dt){')
        paused = tick.index('if(aw_mwscript_paused && aw_mwscript_paused()){AW_MsgBoxClear();')
        self.assertLess(tick.index('if(!mwscript.value)'), paused)
        self.assertLess(paused, tick.index('if(!load())return;'))      # before any script runs
        screen = code('screen.c')
        self.assertIn('AW_LightTestActive ()', body(screen, 'static int SCR_AWFullView (void)'))
        update = screen[screen.index('int clean = AW_LightTestActive ();'):screen.index('AW_CycleItemsDraw();')]
        for guarded in ('AW_DebugOverlaysEnabled() && !clean', 'if (!AW_PhotoModeActive())\n                SCR_DrawPause ();', 'if (!clean)\n            SCR_CheckDrawCenterString ();',
                        'if (!over_window && !clean) {', 'if (!clean)\n            AW_FpsDraw();'):
            self.assertIn(guarded, update)
        self.assertIn('clean = clean || AW_LightTestActive ();', code('view.c'))   # no crosshair
        # the full view: no status bar, no character stats
        self.assertIn('if (!vanity)\n            Sbar_Draw ();', update)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class Native(unittest.TestCase):
    def test_rows_actions_lines_and_the_walk(self):
        import test_aga_native_source as native
        native.NativeSourceTests.compile_run(
            self, 'aga_cycleitems_test.c', [SRC / 'aw_cycleitems.c'], defines=['AW_CYCLE_HOST_TEST'],
            cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_the_whole_files_compile(self):
        # the engine side of the tool too, not only its pure part (gate 11686 stopped on an if/else around a braced
        # macro in the walk's end): every file it touches, syntax only, with the engine's headers
        import tempfile
        import subprocess
        import test_aga_native_source as native
        with tempfile.TemporaryDirectory() as tmp:
            native.tree_project_version().generate_native(ROOT / 'VERSION', Path(tmp))
            for name in ('aw_cycleitems.c', 'aw_gallery.c', 'screen.c', 'view.c', 'aw_mwhost.c'):
                r = subprocess.run(['cc', '-fsyntax-only', '-std=gnu89', '-include', str(ROOT / 'tests/aga_test_files.h'),
                                    '-I' + tmp, '-I' + str(SRC), str(SRC / name)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, '%s:\n%s' % (name, r.stderr[-3000:]))


if __name__ == '__main__':
    unittest.main()
