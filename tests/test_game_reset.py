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

    def test_new_game_keeps_the_opening_restricted(self):
        # OPENING-VANITY-CAMERA-64: on the ship and the pier, before the race, no view switch and no idle orbit
        native.NativeSourceTests().compile_run('aga_opening_view_test.c',
                                               [SRC / 'aw_reset.c', SRC / 'aw_story.c', SRC / 'aw_state.c'], cflags=UBSAN)


class OpeningStaysRestricted(unittest.TestCase):
    """OPENING-VANITY-CAMERA-64: no reset module after "story and globals" resets the story or the save again (the
    scene module did, in its restart form, so a New Game's opening ran unrestricted: the idle orbit on the ship)."""

    def test_no_later_reset_touches_the_story(self):
        import re
        loadfail = code('aw_loadfail.c')
        order = re.findall(r'AW_ResetRegister\("([^"]+)",(\w+),', loadfail)
        names = [n for n, _ in order]
        self.assertEqual(names[0], 'story and globals')
        bodies = {f: re.search(r'static void %s\(int new_game\)\{(.*?)\}' % f, loadfail, re.S).group(1) for _, f in order}
        for name, fn in order[1:]:
            self.assertNotIn('AW_StoryReset', bodies[fn], name)
        scene = code('aw_scene.c')
        body = scene[scene.index('void AW_SceneLoadReset(void) {'):]
        body = re.sub(r'/\*.*?\*/', '', body[:body.index('\n}\n')], flags=re.S)
        self.assertNotIn('AW_StoryReset', body)
        self.assertNotIn('AW_SaveReset', body)
        view = code('aw_view.c')
        frame = view[view.index('void AW_ViewFrame(void) {'):]
        self.assertLess(frame.index('if(!AW_StoryViewAllowed()){'), frame.index('AW_ViewIdle(&view,&rules,'))

    def test_each_module_touches_only_its_own_state(self):
        # every registered reset, followed one level into what it calls (across the engine's files): the story's,
        # the save's and the character's state are written only by their own module
        import re
        sources = {p.name: re.sub(r'/\*.*?\*/', '', p.read_text(encoding='utf-8', errors='replace'), flags=re.S)
                   for p in SRC.glob('*.c')}
        def body(name):
            for text in sources.values():
                m = re.search(r'\n(?:static\s+)?(?:void|int|unsigned long)\s+%s\s*\([^)]*\)\s*\{' % re.escape(name), text)
                if m:
                    start = m.end(); depth = 1; i = start
                    while depth and i < len(text):
                        depth += {'{': 1, '}': -1}.get(text[i], 0); i += 1
                    return text[start:i]
            return ''
        owned = {'story and globals': (r'\baw_story\s*[.=]|memset\(&aw_story\b', r'\bAW_StoryReset\s*\(',
                                       r'\bAW_StateReset\s*\('),
                 'world change list': (r'\bAW_SaveReset\s*\(', r'\bAW_LedgerClear\s*\('),
                 'character': (r'\baw_character\s*[.=]|memset\(&aw_character\b', r'\bAW_CharacterReset\s*\(')}
        modules = []
        for text in sources.values():
            modules += re.findall(r'AW_ResetRegister\("([^"]+)",\s*(\w+)', text)
        self.assertIn(('story and globals', 'reset_story'), modules)
        found = []
        for name, fn in modules:
            outer = body(fn)
            texts = [outer] + [body(callee) for callee in set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', outer))
                               if callee not in ('if', 'for', 'while', 'switch', 'return', 'sizeof', fn)]
            for owner, patterns in owned.items():
                if owner == name:
                    continue
                for pattern in patterns:
                    if any(re.search(pattern, t) for t in texts):
                        found.append('%s writes the state of %s (%s)' % (name, owner, pattern))
        self.assertEqual(found, [])

    def test_the_boot_mark_is_interleaved(self):
        loadfail = code('aw_loadfail.c')
        mark = loadfail[loadfail.index('void AW_ResetBootMark(void){'):]
        mark = mark[:mark.index('\n}\n')]
        self.assertIn('AW_ResetMarkBootInterleaved(1);AW_ResetAll(0);', mark)
        self.assertNotIn('AW_ResetMarkBoot()', mark)


class CharGenStateIsOneValue(unittest.TestCase):
    """OPENING-REGRESSION-64: the engine's CharGenState (aw_state, set by AW_StoryReset) and the interpreter's global of
    that name (read by the scripts and the dialogue filters) are kept as one value: synced every tick before any script
    runs, and pushed again after a New Game reset or a save's globals."""

    def test_sync_runs_before_the_scripts_and_after_every_restart(self):
        host = code('aw_mwhost.c')
        tick = host[host.index('void AW_MwscriptTick(float dt){'):]
        self.assertLess(tick.index('chargen_sync();'), tick.index('attach_map();'))
        self.assertLess(tick.index('chargen_sync();'), tick.index('AW_MwvmInstanceCount()'))
        sync = host[host.index('static void chargen_sync(void){'):host.index('void AW_MwscriptTick(float dt){')]
        self.assertIn('AW_StateGet(&aw_state,AW_GLOBAL,"CharGenState")', sync)
        self.assertIn('AW_MwvmGlobalSetBits(chargen_global', sync)
        self.assertIn('AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",script)', sync)
        reset = host[host.index('void AW_MwscriptNewGameReset(void){'):]
        self.assertIn('chargen_synced=0x7fffffff;', reset[:reset.index('\n}\n')])
        imp = host[host.index('static void script_import(const aw_ledger_t *l){'):]
        self.assertIn('chargen_synced=0x7fffffff;', imp[:imp.index('\n}\n')])


class DockGuardReachesHisPost(unittest.TestCase):
    """OPENING-REGRESSION-64: after the race menu the dock guard's walk to his post beside the office door is tried
    again when it is held up (it was given up for good, leaving him on the pier), a bounded number of times, the count
    reset with the map; at the post he faces the pier and the ship."""

    def test_post_walk_retries_and_faces_the_pier(self):
        opening = code('aw_opening.c')
        tick = opening[opening.index('}else if(aw_story.dock==-1){'):]
        tick = tick[:tick.index('/* at his post he stands')]
        self.assertIn('post_retries<30', tick)
        self.assertIn('route_failed=0;', tick)
        self.assertLess(tick.index('post_retries<30'), tick.index('dock_route(1);'))
        self.assertIn('g->v.angles[1]=225;', tick)
        spawn = opening[opening.index('void AW_OpeningSpawn(void)'):]
        self.assertIn('post_retries=0;', spawn[:spawn.index('\n}\n')])


class CensusTypeAmiwind(unittest.TestCase):
    """OPENING-REGRESSION-64: one setting, census type (aw_census_type: 0 amiwind, the default; 1 legacy; 2 original),
    the older census legacy kept as an alias. The amiwind hybrid brings back AmiWind's registration around the
    original's scripts: the clerk starts his talk by himself through his own script's activation and faces the player,
    who is held until the review is done; his Say lines show in the speech box; nothing in the office is taken or used
    before the papers' stage, everything after it. The scripts' own parts stay (menus, papers, door guard, captain)."""

    def test_one_setting_default_amiwind_and_the_alias(self):
        opening = code('aw_opening.c')
        self.assertIn('cvar_t aw_census_type={"aw_census_type","0"};', opening)
        self.assertIn('int AW_CensusLegacy(void){return AW_CensusType()==1;}', opening)
        self.assertIn('Cvar_SetValue("aw_census_type",Q_atoi(Cmd_Argv(1))?1.f:2.f);', opening)
        self.assertNotIn('cvar_t aw_census_legacy', opening)
        debug = code('aw_debug.c')
        self.assertIn('Cvar_RegisterVariable(&aw_census_type);', debug)
        self.assertIn('Cmd_AddCommand("aw_census_legacy",AW_CensusLegacyCommand);', debug)
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('|census type|aw_census_type_set|', catalogue)
        self.assertIn('|census legacy|aw_census_legacy|', catalogue)

    def test_the_clerk_starts_his_talk_and_holds_the_player(self):
        opening = code('aw_opening.c')
        block = opening[opening.index('    if(AW_CensusAmiwind()){'):opening.index('    if(!AW_CensusLegacy()){\n        /* the clerk')]
        self.assertIn('near_actor(6)<25 && aw_opening_activate', block)
        self.assertIn('aw_story.census==0 && aw_story.stage>=AW_STAGE_CLASS && aw_story.stage<AW_STAGE_PAPERS', block)
        self.assertIn('aw_story.census=10;', block)
        self.assertIn('clerk->v.angles[1]=Q_atan2(', block)
        # the hold: census 10 is inside AW_OpeningLocked's census range, and the review's end sets -1
        self.assertIn('return aw_story.census>=10 && aw_story.census<=17;', opening)
        self.assertIn('show_papers();aw_story.census=-1;', opening)
        self.assertIn('aw_opening_activate=object_intercept;', code('aw_mwhost.c'))

    def test_say_lines_show_in_the_speech_box(self):
        host = code('aw_mwhost.c')
        say = host[host.index('static void host_say('):host.index('static int host_say_done(')]
        self.assertIn('read_string(text,line,sizeof(line))', say)
        self.assertIn('AW_UIVoiceSubtitle(', say)
        self.assertLess(say.index('AW_UIVoiceSubtitle('), say.index('S_StartSound('))
        # without a sample the line's time is still recorded for SayDone (the script's pacing)
        self.assertIn('AW_MsgBoxSeconds(line)', say)
        self.assertIn('says[slot].until=(float)(realtime+seconds);', say)

    def test_nothing_taken_before_the_papers_stage(self):
        inv = code('aw_inventory.c')
        use = inv[inv.index('static int placed_use(void){'):]
        use = use[:use.index('\n}\n')]
        self.assertLess(use.index('aw_census_take_refused()'), use.index('container_open('))
        self.assertLess(use.index('aw_census_take_refused()'), use.index('take_row(row)'))
        opening = code('aw_opening.c')
        rule = opening[opening.index('int AW_OpeningTakeRefused(void){'):]
        rule = rule[:rule.index('\n}\n')]
        self.assertIn('AW_CensusAmiwind()', rule)
        self.assertIn('aw_story.stage<AW_STAGE_PAPERS', rule)
        self.assertIn('aw_census_take_refused=AW_OpeningTakeRefused;', code('aw_debug.c'))
        # every take route: the use key itself refuses before the scene's uses and the game code's impulse 201,
        # people (the clerk) excepted
        use = code('cl_input.c')
        use = use[use.index('void IN_AWUseDown(void) {'):]
        use = use[:use.index('\n}\n')]
        gate = use.index('aw_census_take_refused && aw_census_take_refused() && !AW_SceneNpcAimed()')
        self.assertLess(gate, use.index('AW_SceneUse()'))
        self.assertLess(gate, use.index('in_impulse = 201'))


class EnableDrawsAgain(unittest.TestCase):
    """CENSUS-PAPERS-INVISIBLE-65: a script's Disable then Enable of a placed object draws it again, also when another
    rule had hidden its edict first (the papers): both hide paths keep the model from the edict's own model name."""

    def test_both_hide_paths_keep_a_drawable_model(self):
        host = code('aw_mwhost.c')
        shown = host[host.index('static void shown_state(edict_t *e,float *model,float *solid){'):]
        shown = shown[:shown.index('\n}\n')]
        self.assertIn('SV_ModelIndex(', shown)
        self.assertIn("name[0]=='*'?SOLID_BSP:SOLID_BBOX", shown)
        for fn in ('static void ledger_hide(uint32_t ref){', 'static void object_hide(object_t *o){'):
            body = host[host.index(fn):]
            body = body[:body.index('\n}\n')]
            self.assertIn('shown_state(e,', body, fn)


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
