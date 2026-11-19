# SPDX-License-Identifier: GPL-3.0-only
"""DBG-SPAWN-MENU-67: dbg spawn opens a list box like dbg tp's with every person and creature the build has a model for
(find, their names, the buttons All / NPCs / Creatures, a line of the selected one's properties, the switch "spawn in
with base attributes", on by default); the chosen one appears in front of the player, as the game makes it (its stats,
behaviour, items and script) or, with the switch off, as its model only. dbg despawn is the red-crosshair pick of dbg
kill whose click removes the aimed one; dbg despawn all removes every spawned one.

The list's rules run natively (tests/aga_dbgspawn_test.c); the base reader runs on a real actor table
(tests/test_aw_actors_native.py), the pick in tests/aga_companion_test.c, the console routes in tests/aga_console_test.c.
The contracts below keep the parts joined."""
import os
import re
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def body(text, start):
    """The function that starts with START, up to its closing brace at the start of a line (a brace inside a string
    literal does not end it)."""
    i = text.index(start)
    return text[i:text.index('\n}\n', i) + 2]


class DbgSpawnRulesNative(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
    def test_labels_order_details_and_words(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_dbgspawn_test.c', [SRC / 'aw_dbgspawn.c'],
                                               defines=['AW_DBGSPAWN_RULES_ONLY'],
                                               cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])


class DbgSpawnContracts(unittest.TestCase):
    def test_the_commands_are_in_the_catalogue_and_reach_the_actor_command(self):
        rows = {l.split('|')[1]: l.split('|') for l in (ROOT / 'config' / 'debug-commands.txt').read_text(
            encoding='utf-8').splitlines() if l.count('|') == 3}
        self.assertEqual(rows['spawn'][2], 'chim')
        self.assertEqual(rows['despawn'][2], 'chim')
        self.assertIn('spawn in with base attributes', rows['spawn'][3])
        self.assertIn('red crosshair', rows['despawn'][3])
        console = code('aw_console.c')
        self.assertIn('strcpy(out+used," actors spawn");used+=13;', console)
        self.assertIn('" actors despawnpick\\n":" actors despawn all\\n"', console)
        actors = body(code('aw_actors.c'), 'static void Command (void)')
        self.assertIn('AW_SpawnCommand (Cmd_Argc () > 3 ? Cmd_Argv (3) : NULL, Cmd_Argc () > 4 ? Cmd_Argv (4) : NULL);', actors)
        self.assertIn('AW_CompanionDespawnMode ();', actors)
        self.assertIn('AW_MwscriptDespawnAll ();', actors)

    def test_spawned_keys_have_their_own_block_never_spawned_again(self):
        h = code('aw_actors.h')
        value = lambda name: int(re.search(r'#define %s (0x[0-9A-F]+)U' % name, h).group(1), 16)
        spawned, slots = value('AW_ACTORS_SPAWNED'), value('AW_ACTORS_SPAWNED_SLOTS')
        self.assertGreaterEqual(spawned, value('AW_ACTORS_SUMMONED') + value('AW_ACTORS_SUMMONED_SLOTS'))
        self.assertLessEqual(spawned + slots, value('AW_ACTORS_PLACED'))      # content file index 14, as the summons
        actors = code('aw_actors.c')
        place = body(actors, 'int AW_ActorsPlaceRow (unsigned reference')
        self.assertIn('int spawned = reference >= AW_ACTORS_SPAWNED && reference < AW_ACTORS_SPAWNED + AW_ACTORS_SPAWNED_SLOTS;', place)
        self.assertIn('c->follow = summoned;', place)                          # a spawned one does not follow
        self.assertIn('AW_ACTORS_SPAWNED', body(actors, 'void AW_ActorsPlacedForget (unsigned reference)'))
        tick = body(actors, 'void AW_ActorsPlacedTick (int (*spawn)(unsigned reference))')
        self.assertNotIn('AW_ACTORS_SPAWNED', tick)                             # only the script-placed block comes back

    def test_the_spawn_places_like_a_summon_and_runs_the_records_script(self):
        spawn = body(code('aw_mwhost.c'), 'int AW_MwscriptSpawn(const char *id,int full)')
        self.assertIn('text=AW_ActorsBaseText(id,&n)', spawn)
        self.assertIn('place_spot(base,yaw,SPAWN_DISTANCE,0,1,local);', spawn)    # safePlaceObject, as summon_spawn
        self.assertIn('AW_ActorsPlaceRow(key,local,yaw+180)?AW_ActorsSpawnVisitor(', spawn)   # facing the player
        self.assertIn('AW_MwvmLevelledScript(AW_MwvmTextHash(folded,i),&script) || bound_script(', spawn)
        self.assertIn('attach_script(key,script,', spawn)
        # the placeholder: out of every actor system, no script, no row
        self.assertIn('e->v.classname=placeholder_class;e->v.think=0;e->v.nextthink=0;e->v.movetype=MOVETYPE_NONE;', spawn)
        self.assertLess(spawn.index('if(full){'), spawn.index('placeholder_class=ED_NewString("aw_dbg_placeholder")'))
        host = code('aw_mwhost.c')
        self.assertIn('aw_companion_despawn=spawn_remove;aw_companion_placeholder=placeholder_edict;',
                      body(host, 'void AW_MwscriptInit(void)'))
        remove = body(host, 'static void spawn_remove(edict_t *e)')
        self.assertLess(remove.index('AW_MwvmDetach(key)'), remove.index('AW_ActorsRemove(e)'))   # a game actor's script parked
        self.assertIn('if(spawned_key(key)){AW_ActorsPlacedForget(key);AW_MwvmForget(key);}', remove)

    def test_the_despawn_pick_is_the_kill_pick(self):
        comp = code('aw_companion.c')
        act = body(comp, 'static void pick_act(edict_t *e)')
        self.assertLess(act.index('if(pick.despawn)'), act.index('if(!pick.kill){pick_npc(e);return;}'))
        self.assertIn('if(aw_companion_despawn)aw_companion_despawn(e);', act)
        self.assertIn('if(pick.kill || pick.despawn){', body(comp, 'int AW_CompanionPickAim(void)'))
        mode = body(comp, 'void AW_CompanionDespawnMode(void)')
        self.assertIn('pick.on=1;pick.despawn=1;pick.kill=0;', mode)

    def test_the_box_holds_the_list_only_while_open(self):
        box = code('aw_dbgspawn.c')
        self.assertIn('s.detail=detail;s.check="spawn in with base attributes";s.checked=&spawn_full;', box)
        self.assertIn('static int spawn_full=1;', box)                          # on by default
        self.assertIn('static void closed(void *ctx){(void)ctx;rows_free();}', box)
        self.assertIn('n=AW_ActorsBaseEach(take,NULL);', box)
        listbox = code('aw_listbox.c')
        self.assertIn("if(k==' ' && spec.check && spec.checked)*spec.checked=!*spec.checked;", listbox)
        self.assertIn('static int list_h(void){int h=footer_y()-4-extra_h()-list_y();', listbox)

    def test_built_into_the_engine_and_the_release(self):
        make = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn(' aw_dbgspawn.c', make)
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        for name in ('engine/aga/src/aw_dbgspawn.c', 'engine/aga/src/aw_dbgspawn.h', 'tests/aga_dbgspawn_test.c',
                     'tests/test_dbg_spawn.py'):
            self.assertIn('"%s"' % name, files)


if __name__ == '__main__':
    unittest.main()
