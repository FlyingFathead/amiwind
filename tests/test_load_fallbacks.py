# SPDX-License-Identifier: GPL-3.0-only
"""A place that cannot be reached or loaded never ends the game (SCENE-LOAD-FAIL-FALLBACK-67, DBG-TP-NOT-FOUND-BOX-67).

The rules (engine/aga/src/aw_loaderr.c: the kinds and codes, the OK box in the maintainer's form, the load menu's notice,
the console block, the map header check) run natively in tests/aga_loaderr_test.c. The production paths run natively
too: the scene's refusals, failed loads, the way back and the box (tests/aga_scene_test.c, test_aga_native_source), the
allocators' hook (tests/aga_heap_watcher_test.c), the brush loader's broken-map report (tests/aga_bsp_slice_load_test.c).
Here: the table of every way into a place (each reaches the one catcher), and the wiring the host fixtures leave out
(the hooks the game sets, Host_Map_f, the client's server info)."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return (SRC / name).read_text(encoding='utf-8', errors='replace')


def body(text, head):
    start = text.index(head)
    end = text.index('\n}\n', start)
    return text[start:end]


def strip_comments(text):
    return re.sub(r'/\*.*?\*/', '', text, flags=re.S)


# Every function of aw_scene.c that starts a scene load (load_scene), and how it reaches the player. A new caller
# fails test_every_scene_load_is_in_the_table until it is added here and to docs/LOAD_ERRORS.md.
SCENE_LOAD_CALLERS = {
    'map_teleport': 'dbg tp X Y [Z], the map marker, named outdoor places; a script\'s Position / PositionCell '
                    'outdoors; the jail marker (AW_MapTeleportAt)',
    'AW_SceneShot': 'dbg cam recall',
    'travel_ride': 'travel services (silt strider, boat, guild guide)',
    'AW_TravelKey': 'the town table\'s silt strider ride',
    'use_link': 'doors and load doors, a script\'s Activate of a load door',
    'AW_SceneTick': 'a door after its opening sound, a region crossing',
    'scene_command': 'dbg tp NAME, dbg scene NAME (towns, rooms, the ship, named places)',
    'hors_command': 'dbg aw hors 0',
    'hors_census': 'dbg aw hors (the census office exit door, DBG-HORS-AFTER-CENSUS-67)',
    'AW_SceneLoadRoom': 'a script\'s PositionCell into a room, the dbg tp list\'s rooms',
    'roulette_command': 'dbg door roulette',
}
# Every engine file that queues a raw "map" command: all reach Host_Map_f (or Host_Changelevel_f), whose
# AW_SceneMapBegin puts the load in flight, so an error ends that load and the load menu names it.
RAW_MAP_FILES = {'aw_gallery.c', 'aw_intro.c', 'aw_save.c', 'aw_scene.c', 'cl_demo.c', 'pr_cmds.c'}


def enclosing_functions(text, call):
    """The function each CALL( site of TEXT sits in (by the last function head before it)."""
    heads = [(m.start(), m.group(1)) for m in
             re.finditer(r'^(?:static\s+)?[A-Za-z_][\w \*]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{', text, re.M)]
    found = set()
    for m in re.finditer(r'(?<![\w.])%s\(' % re.escape(call), text):
        before = [name for at, name in heads if at < m.start()]
        found.add(before[-1] if before else '?')
    return found


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class Rules(unittest.TestCase):
    def test_codes_boxes_notices_console_and_header(self):
        native.NativeSourceTests().compile_run('aga_loaderr_test.c', [SRC / 'aw_loaderr.c'], cflags=UBSAN)


class EveryWayIn(unittest.TestCase):
    def test_every_scene_load_is_in_the_table(self):
        scene = strip_comments(code('aw_scene.c'))
        callers = enclosing_functions(scene, 'load_scene') - {'load_scene'}
        self.assertEqual(callers, set(SCENE_LOAD_CALLERS))
        page = (ROOT / 'docs' / 'LOAD_ERRORS.md').read_text(encoding='utf-8')
        for name in SCENE_LOAD_CALLERS:
            self.assertIn('`%s`' % name, page, name)

    def test_every_raw_map_command_reaches_host_map(self):
        files = set()
        for path in sorted(SRC.glob('*.c')):
            text = strip_comments(path.read_text(encoding='utf-8', errors='replace'))
            if re.search(r'(Cbuf_(?:Add|Insert)Text|Cmd_ExecuteString)\s*\(\s*(?:\(char \*\))?(?:va\()?"(?:map|changelevel2?) ', text) or \
               re.search(r'"map %s', text):
                files.add(path.name)
        files.discard('aw_remote.c')   # a state file line, not a command
        files.discard('host_cmd.c')    # Host_Map_f's own test-aid message
        self.assertEqual(files, RAW_MAP_FILES)
        page = (ROOT / 'docs' / 'LOAD_ERRORS.md').read_text(encoding='utf-8')
        for name in RAW_MAP_FILES:
            self.assertIn(name, page)
        host = strip_comments(code('host_cmd.c'))
        mapf = body(host, 'void Host_Map_f (void)')
        self.assertLess(mapf.index('AW_SceneMapRefuse (Cmd_Argv(1))'), mapf.index('AW_SceneMapBegin (name);'))
        self.assertLess(mapf.index('AW_SceneMapBegin (name);'), mapf.index('SV_SpawnServer (name);'))
        self.assertLess(mapf.index('AW_LoadFailSpawn (name);'), mapf.index('AW_SceneLoadFailed ("the map could not be spawned");'))
        change = body(host, 'void Host_Changelevel_f (void)')
        plain = change[change.index('#else'):]
        self.assertLess(plain.index('AW_SceneMapBegin (level);'), plain.index('SV_SpawnServer (level);'))
        self.assertIn('AW_SceneLoadFailed ("the map could not be spawned");', plain)
        # Host_EndGame and Host_Error end a load in flight there (the way back, or the load menu); Host_Error in play
        # loads the place again (NET-VIVEC-ENTITY-PACKET-OVERFLOW-66), and a step of the recovery chain still loading
        # goes on there (AW-RECOVER, tests/test_recover_in_play.py)
        self.assertEqual(code('host.c').count('AW_SceneLoadFailed (string);'), 1)
        self.assertEqual(code('host.c').count('AW_SceneHostError (string);'), 1)
        host_error = body(code('aw_scene.c'), 'void AW_SceneHostError(const char *why) {')
        self.assertIn('if(pending || map_loading || recover_step){AW_SceneLoadFailed(why);return;}', host_error)
        # the map arrived: no longer in flight
        spawn = body(code('aw_scene.c'), 'void AW_SceneSpawn(edict_t *p) {')
        self.assertIn('map_loading=0;', spawn)

    def test_every_dbg_tp_refusal_goes_through_one_path(self):
        scene = strip_comments(code('aw_scene.c'))
        for line in ('Con_Printf("Unknown destination: %s.\\n",Cmd_Argv(1));',
                     'Con_Printf("Destination not on this disk: %s.\\n",r.label);',
                     'Con_Printf("Destination not on this disk: %s.\\n",s);',
                     'Con_Printf("%s: no map on this disk holds that point; player state unchanged.\\n",r.label);',
                     'Con_Printf("No entrance or start found for %s.\\n",s);'):
            at = scene.index(line)
            self.assertIn('tp_refused(', scene[at:at + 220], line)
        command = body(scene, 'static void teleport_command(void) {')
        self.assertEqual(command.count('point_refused(source);'), 3)   # coordinates, the map marker, Tel Uvirith
        refused = body(scene, 'static void tp_refused(')
        self.assertIn('refusal_show();', refused)
        show = body(scene, 'static void refusal_show(void) {')
        self.assertIn('load_box_wanted=1;', show)


class WhatEndsALoadInsteadOfTheGame(unittest.TestCase):
    def test_allocators_tell_the_hook_before_they_stop(self):
        zone = strip_comments(code('zone.c'))
        for fn, arena in (('void *Z_Malloc (int size)', '"zone"'), ('void *Hunk_AllocName (int size, char *name)', '"hunk"'),
                          ('cache_system_t *Cache_TryAlloc (int size, qboolean nobottom)', '"cache"'),
                          ('void *Cache_Alloc (cache_user_t *c, int size, char *name)', '"cache"')):
            text = body(zone, fn + '\n{')
            hook = text.index('if(aw_alloc_failed)aw_alloc_failed(' + arena)
            self.assertLess(hook, text.index('Sys_Error', hook), fn)

    def test_a_broken_map_is_told_before_the_game_would_stop(self):
        # the fatal path (sys_amiga.c Sys_Error, unchanged: the converted world's build keys read it whole) reaches the
        # heap audit's fatal-exit phase right after the input guard leaves; that phase calls the hook first
        error = strip_comments(body(code('sys_amiga.c'), 'void Sys_Error (char *error, ...)\n{'))
        self.assertLess(error.index('vsnprintf (text'), error.index('AW_InputGuardShutdown();'))
        self.assertLess(error.index('AW_InputGuardShutdown();'), error.index('AW_HeapAuditPhase(NULL,"fatal-exit");'))
        self.assertNotIn('aw_fatal_hook', error)
        phase = strip_comments(body(code('zone.c'), 'void AW_HeapAuditPhase(const char *scene,const char *phase) {'))
        hook = phase.index('if(aw_fatal_hook && phase && !strcmp(phase,"fatal-exit"))aw_fatal_hook();')
        self.assertLess(hook, phase.index('if(!hunk_base || hunk_size<=0)return;'))
        # the brush loader's own code stays as it was (its text keys the CHIM world; IMPERATIVE: an engine change never
        # re-keys the world); Mod_LoadModel marks its brush decodes, and the report leaves the loader as after a
        # finished load
        model = strip_comments(code('model.c'))
        brush = body(model, 'static void AW_BrushError(char *fmt,...)\n{')
        self.assertNotIn('AW_Map', brush)
        load = body(model, 'model_t *Mod_LoadModel (model_t *mod, qboolean crash)\n{')
        self.assertIn('AW_MapDecode(mod);\n    if(AW_TryStreamBrush(mod)){AW_MapDecode(NULL);return mod;}', load)
        self.assertLess(load.index('AW_MapDecode (mod);'), load.index('Mod_LoadBrushModel (mod, buf);'))
        self.assertLess(load.index('Mod_LoadBrushModel (mod, buf);'), load.index('AW_MapDecode (NULL);'))
        failure = body(model, 'int AW_MapFailure(aw_mapfail_t *out)\n{')
        self.assertIn('if(!mod || aw_brush_arena)return 0;', failure)
        self.assertIn('if(aw_bsp_file){fclose(aw_bsp_file);aw_bsp_file=NULL;}', failure)
        self.assertIn('mod->needload=NL_UNREFERENCED;', failure)
        self.assertIn('AW_MapDecode(NULL);', failure)
        if str(ROOT / 'tools') not in sys.path:
            sys.path.insert(0, str(ROOT / 'tools'))
        import engine_loader_policy
        ours = {'AW_MapFailure', 'AW_MapDecode', 'aw_map_decoding', 'aw_map_short_bytes'}
        self.assertFalse(ours & engine_loader_policy.BRUSH_EDGE_FUNCTIONS)
        names = {name for item in engine_loader_policy.brush_edge_items(code('model.c')) for name in item['defines']}
        self.assertFalse(names & ours, names & ours)

    def test_the_game_sets_every_hook_and_each_checks_the_load(self):
        loadfail = strip_comments(code('aw_loadfail.c'))
        self.assertIn('aw_alloc_failed=alloc_failed;aw_fatal_hook=fatal;', loadfail)
        self.assertIn('aw_load_precheck=precheck;aw_load_memory_free=memory_free;', loadfail)
        for fn in ('static void alloc_failed(', 'static void fatal('):
            text = body(loadfail, fn)
            self.assertLess(text.index('AW_SceneLoadInFlight()'), text.index('Host_Error('), fn)
            self.assertLess(text.index('AW_SceneLoadNote(&e);'), text.index('Host_Error('), fn)
        fatal = body(loadfail, 'static void fatal(')
        self.assertLess(fatal.index('AW_SceneLoadInFlight()'), fatal.index('AW_MapFailure(&m)'))
        # Sys_Error took the input guard away before the hook: it is back before the game goes on
        self.assertLess(fatal.index('AW_InputGuardInit();'), fatal.index('Host_Error('))
        # the time limit: a load without progress ends as a failed load
        timeout = body(loadfail, 'static void timeout_tick(void) {')
        self.assertIn('AW_LOADERR_TIMEOUT', timeout)
        self.assertIn('Host_Error("The load did not finish', timeout)
        self.assertIn('cvar_t aw_load_timeout={"aw_load_timeout","120"};', loadfail)
        # the box: one button, OK; no place to stay: the main menu and the load menu naming the error
        tick = body(loadfail, 'static void tick(void) {')
        self.assertIn('AW_MsgBoxShow(AW_SceneLoadBoxText(),buttons,1);', tick)
        self.assertIn('AW_SaveMenuNotice(AW_SceneLoadNoticeText());', tick)

    def test_the_client_never_stops_half_connected(self):
        info = strip_comments(body(code('cl_parse.c'), 'void CL_ParseServerInfo (void)'))
        self.assertIn('Host_Error ("Model %s not found", name);', info)
        for message in ('Server returned version', 'Bad maxclients', 'too many model precaches', 'too many sound precaches'):
            at = info.index(message)
            self.assertIn('Host_Error', info[at - 40:at], message)
        self.assertNotRegex(info, r'Con_Printf\s*\(\s*"Model %s not found')

    def test_the_test_aid_and_its_documentation(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        line = next(l for l in catalogue.splitlines() if l.startswith('PLAYTESTING|loadfail|aw_load_fail|'))
        for word in ('error', 'memory', 'lump', 'hang', 'timeout'):
            self.assertIn(word, line)
        page = (ROOT / 'docs' / 'LOAD_ERRORS.md').read_text(encoding='utf-8')
        for code_name in ('LF%d' % k for k in range(1, 10)):
            self.assertIn(code_name, page)
        self.assertIn('engine/aga/src/aw_loaderr.c', (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        self.assertIn('docs/LOAD_ERRORS.md', (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))

    def test_the_emergency_purge_is_wired(self):
        # MEMORY-EMERGENCY-PURGE-64: the game binds the purge and the room's memory report; the purge is every
        # releaser of re-makeable memory with one line of figures, and the scene asks it before the way back of a load
        # that failed for memory; the retry's rule and its order are host-tested (aga_loaderr_test.c, aga_scene_test.c)
        loadfail = strip_comments(code('aw_loadfail.c'))
        self.assertIn('aw_scene_memory_purge=memory_purge;chim_room_short=room_short;', loadfail)
        self.assertIn('Cmd_AddCommand("aw_mempurge",mem_purge_command);', loadfail)
        purge = body(loadfail, 'static long memory_purge(const char *map) {')
        self.assertLess(purge.index('if(!aw_mem_purge.value)'), purge.index('AW_FastReleaseAll ("the emergency purge")'))
        self.assertIn('Con_Printf("Memory purge for %s:', purge)
        self.assertIn('static cvar_t aw_mem_purge={"aw_mem_purge","1"};', loadfail)   # on by default, not saved
        self.assertIn('if(purge_test_armed)purge_test_fail();', body(loadfail, 'int AW_LoadFailTestArm(void) {'))
        scene = strip_comments(code('aw_scene.c'))
        failed = body(scene, 'void AW_SceneLoadFailed(const char *why) {')
        retry = failed.index('if(lerr.kind==AW_LOADERR_MEMORY && mem_retry_after_purge())return;')
        self.assertLess(retry, failed.index('recover_from(1,&back);', retry))   # before the way back
        self.assertGreater(retry, failed.index('if(load_recovering){'))          # never for a step of the chain
        world = strip_comments((SRC / 'chim' / 'chim_world.c').read_text(encoding='utf-8', errors='replace'))
        refuse = body(world, 'static void RefuseRoom (const char *name, const char *why)\n{')
        self.assertLess(refuse.index('chim_room_short (name, need, have);'), refuse.index('Host_Error'))
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        line = next(l for l in catalogue.splitlines() if l.startswith('PLAYTESTING|mempurge|aw_mempurge|'))
        for word in ('on', 'off', 'test'):
            self.assertIn(word, line)
        self.assertIn('dbg mempurge test', (ROOT / 'docs' / 'LOAD_ERRORS.md').read_text(encoding='utf-8'))
        self.assertIn('tests/sessions/memory_purge.txt', (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
