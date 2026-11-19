# SPDX-License-Identifier: GPL-3.0-only
"""No error in play ends the game (SCENE-LOAD-FAIL-FALLBACK-67, the maintainer's P0 of 17 November 2026): every
Host_Error in play, every load that fails and an allocation that fails in play go down one chain until the player is in
play again: the place again at the last good position, else the newest autosave, else the previous map, and only then
the load menu (engine/aga/src/aw_scene.c; the chain itself in tests/aga_scene_test.c, the box texts in
tests/aga_loaderr_test.c, the state file in tests/aga_remote_test.c). Here: the wiring the fixtures leave out: the test
aids dbg hosterror and dbg loadfail, the save hooks, the counters and the engine smoke failing a run on an error that
was not forced."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8', errors='replace')


def strip_comments(text):
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


class Wiring(unittest.TestCase):
    def test_every_error_in_play_takes_the_chain(self):
        host = strip_comments(body(code('host.c'), 'void Host_Error (char *error, ...)'))
        self.assertLess(host.index('CL_Disconnect ();'), host.index('AW_SceneHostError (string);'))
        self.assertLess(host.index('AW_SceneHostError (string);'), host.index('longjmp (host_abortserver, 1);'))
        scene = strip_comments(code('aw_scene.c'))
        error = body(scene, 'void AW_SceneHostError(const char *why)')
        self.assertIn('if(pending || map_loading || recover_step){AW_SceneLoadFailed(why);return;}', error)
        self.assertIn('if(!play_now || !play_spot.valid)return;', error)   # the menus: as before
        self.assertIn('recover_from(from,&spot);', error)
        failed = body(scene, 'void AW_SceneLoadFailed(const char *why)')
        self.assertIn('recover_from(recover_step+1,NULL);', failed)      # a step that failed: the next one
        self.assertIn('if(aw_scene_save_drop)aw_scene_save_drop();', failed)   # a failed saved game never applied later
        chain = body(scene, 'static void recover_from(int from,const spot_t *spot)')
        for step in ('Recovery 1 of 3', 'Recovery 2 of 3', 'Recovery 3 of 3', 'the load menu'):
            self.assertIn(step, chain)
        self.assertIn('play_spot_take(p);', scene)
        self.assertIn('if(recover_step==2 && !pending)recover_arrived(p);', scene)   # the autosave's arrival
        # an allocation that fails in play goes the same way, before the allocator's Sys_Error
        loadfail = strip_comments(code('aw_loadfail.c'))
        self.assertIn('if(AW_SceneInPlay())alloc_failed_in_play(arena,name,need,have);',
                      body(loadfail, 'static void alloc_failed('))
        self.assertIn('Host_Error("Not enough memory in play:', body(loadfail, 'static void alloc_failed_in_play('))

    def test_the_save_hooks(self):
        loadfail = strip_comments(code('aw_loadfail.c'))
        self.assertIn('aw_scene_autosave_load=AW_SaveRecoverAutosave;', loadfail)
        self.assertIn('aw_scene_save_drop=AW_SaveLoadDrop;', loadfail)
        save = strip_comments(code('aw_save.c'))
        recover = body(save, 'int AW_SaveRecoverAutosave(char *label,int size)')
        self.assertIn('for(slot=5;slot<=20;slot++)', recover)          # the autosave slots only
        self.assertIn('return AW_SaveRead(profile,best)==1;', recover)
        self.assertIn('void AW_SaveLoadDrop(void){if(loading){loading=0;pending_drop();}}', save)

    def test_the_test_aids(self):
        loadfail = strip_comments(code('aw_loadfail.c'))
        self.assertIn('Cmd_AddCommand("aw_host_error",hosterror_command);', loadfail)
        self.assertIn('aw_scene_error_forced=1;', body(loadfail, 'int AW_LoadFailTestArm(void)'))
        step = strip_comments(code('aw_mwhost.c'))
        hook = 'if(aw_mwhost_step_error){script_depth++;aw_mwhost_step_error();script_depth--;}'
        self.assertLess(step.index(hook), step.index('script_depth++;AW_MwvmTick(dt,player);script_depth--;'))
        parse = strip_comments(body(code('cl_parse.c'), 'void CL_ParseServerMessage (void)'))
        self.assertLess(parse.index('cl_parse_force_error ();'), parse.index('CL_ParseMessage ();'))
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertTrue(any(l.startswith('PLAYTESTING|hosterror|aw_host_error|') for l in catalogue.splitlines()))
        session = (ROOT / 'tests' / 'sessions' / 'recover_in_play.txt').read_text(encoding='utf-8')
        for line in ('cmd aw_host_error script', 'cmd aw_host_error client', 'cmd aw_load_fail 2'):
            self.assertIn(line, session)

    def test_errors_are_counted_and_a_run_with_one_fails(self):
        self.assertIn('fprintf(f,"errors %d\\nerrors_forced %d\\nnet_dropped %d\\n",', code('aw_remote.c'))
        sys.path.insert(0, str(ROOT / 'tools'))
        import engine_smoke
        self.assertIn('e=$(st errors); [ -n "$e" ] && [ "$e" != 0 ] && set -- "FAIL', engine_smoke.PROBE)
        self.assertIn('d=$(st net_dropped); [ -n "$d" ] && [ "$d" != 0 ] && set -- "FAIL', engine_smoke.PROBE)
        self.assertNotIn('st errors_forced', engine_smoke.PROBE)    # the test aids' errors never fail a run

    def test_the_documentation(self):
        page = (ROOT / 'docs' / 'LOAD_ERRORS.md').read_text(encoding='utf-8')
        for words in ('## No error in play ends the game', 'the last autosave', 'the previous map', 'dbg hosterror',
                      'errors_forced', 'DEBUG.TXT'):
            self.assertIn(words, page)


if __name__ == '__main__':
    unittest.main()
