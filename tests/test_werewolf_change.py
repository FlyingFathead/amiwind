# SPDX-License-Identifier: GPL-3.0-only
"""The player's change into the werewolf and back, and the werewolf drawn (WEREWOLF-BODY-63,
WEREWOLF-TRANSFORM-RULES-PARTIAL-68, v0.0.68). Rules from OpenMW 0.51 (read, not copied): mwmechanics/
mechanicsmanagerimp.cpp setWerewolf 1880-1937, mwworld/inventorystore.cpp unequipAll, mwworld/class.cpp showsInInventory
289-295, mwrender/npcanimation.cpp updateNpcBase 469-519 and getBodyParts 1160-1195.

Natively: the werewolf's look from the recipe (tests/aga_werewolf_look_test.c), the change on the game state
(tests/aga_werewolf_change_test.c: items off, the hidden robe added and worn, the temporary effects ended, the stats
kept and set, back again, 50 changes, the save, New Game) and the real aw_view.c part sets swapped and let go by number
(tests/aga_werewolf_parts_test.c on a slice of aw_view.c: the model table's slots, the pinned bytes and the cache after 50
changes as before the first; an image without the werewolf's rows keeps the player's own body). Then the wiring the
native tests cannot reach: every route runs the one change, the windows refused, dbg werewolf, New Game. Each fails on
the engine before v0.0.68: the change did only the stats and the unequip, and nothing drew the werewolf."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))
sys.path.insert(2, str(Path(__file__).resolve().parent))

import test_aga_native_source as native  # noqa: E402

SRC = ROOT / 'engine/aga/src'
SANITIZE = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all']
COMPILER = shutil.which('cc')


def code(name):
    return (SRC / name).read_text(encoding='utf-8', errors='replace')


def body(text, head):
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


def between(text, start, end):
    at = text.index(start)
    return text[at:text.index(end, at)]


def view_slice(view):
    """aw_view.c's part sets as one C text: the body's statics, the part sets and their release (from the assembled
    body's parts to the end of hand_parts_ready), then AW_ViewPartsUnload and parts_race_check."""
    statics = between(view, 'static aw_parts_body_t parts;\n', 'static void body_layers_read(')
    sets = between(view, "/* ---- the assembled body's parts ---- */",
                   "/* aw_hand_models.c (aw_hand_parts_apply): the view model becomes the first part")
    unload = view[view.index('void AW_ViewPartsUnload(void) {'):]
    unload = unload[:unload.index('static void parts_race_check(const char *race,int female) {')]
    check = body(view, 'static void parts_race_check(const char *race,int female) {')
    return '/* cut from aw_view.c by tests/test_werewolf_change.py */\n' + statics + sets + unload + check


def run_view_slice(case):
    """tests/aga_werewolf_parts_test.c on the real aw_view.c slice: built and run, its output (CASE asserts both)."""
    with tempfile.TemporaryDirectory(prefix='aw-werewolf-parts-') as tmp:
        tmp = Path(tmp)
        (tmp / 'view_parts_slice.c').write_text(view_slice(code('aw_view.c')), encoding='utf-8')
        exe = tmp / 'check'
        cmd = [COMPILER, '-std=gnu89', '-O1', '-g', '-Wall', '-Wno-unused-function', '-Wno-unused-variable',
               *SANITIZE, '-I' + str(tmp), '-I' + str(SRC), str(ROOT / 'tests/aga_werewolf_parts_test.c'),
               str(SRC / 'aw_player_parts.c'), str(SRC / 'aw_state.c'), '-lm', '-o', str(exe)]
        built = subprocess.run(cmd, capture_output=True, text=True)
        case.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        run = subprocess.run([str(exe)], cwd=str(tmp), capture_output=True, text=True, timeout=120)
        case.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run.stdout


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class WerewolfNative(unittest.TestCase):
    def test_the_look_is_the_recipes_werewolf(self):
        # (a) and (e): the w skeleton, its table and one part, no head, hair or item; an older recipe has none
        native.NativeSourceTests.compile_run(self, 'aga_werewolf_look_test.c', [SRC / 'aw_player_parts.c'],
                                             cflags=SANITIZE)

    def test_the_change_on_the_state(self):
        # (b), (c) and (d): the change both ways, 50 changes, the save and New Game
        native.NativeSourceTests.compile_run(
            self, 'aga_werewolf_change_test.c',
            [SRC / n for n in ('aw_were_rules.c', 'aw_inventory.c', 'aw_state.c', 'aw_effects.c', 'aw_player_parts.c',
                               'aw_forced_rules.c')],
            defines=['AW_INVENTORY_RULES_ONLY'], cflags=SANITIZE)

    def test_the_view_lets_the_previous_set_go(self):
        # (c) and (e) on the real aw_view.c code: by number, after 50 changes on and off
        out = run_view_slice(self)
        self.assertIn('after 51 changes on and off: model table 5 slots in use (5 player parts)', out)
        self.assertIn('(e) without the werewolf rows: the own sets stay (3 and 2 parts), 0 released', out)
        # WEREWOLF-BODY-63 and WEREWOLF-TABLES-STAY-LOADED-68 (wolffix): the arms asked only while the hands are up,
        # each route many times; the tables given back at every change back; a frame that draws neither set
        self.assertIn('(f) 4 routes x 30 changes: the arms the werewolf\'s on every change, the own after every '
                      'change back', out)
        self.assertIn('the werewolf\'s tables given back 171 times, loaded again 171 times', out)
        self.assertIn('(g) a frame that draws neither set: the werewolf\'s set let go at the next frame', out)
        self.assertIn('(h) a model still on the werewolf\'s table: kept once, given back at the next change back', out)
        # NPC-WEREWOLF-NO-MODEL-66 (wolfnpc): the turned NPCs share the set (section (i); tests/test_werewolf_npc.py)
        self.assertIn('(i) 50 changes with the player turning too', out)

    def test_the_table_store_gives_one_table_back(self):
        # WEREWOLF-TABLES-STAY-LOADED-68 on the real aw_skel_load.c and the builder's own tables: 51 loads and give-backs,
        # the index, the frames read and the open files as before; the same slot; the view goes with its table
        import skeletal_actor as S
        import creature_tables as T
        from test_skeletal_actor import Chain
        bones = S.bone_order(Chain.parents, ['fore'])
        parents = [-1 if Chain.parents[b] is None else bones.index(Chain.parents[b]) for b in bones]
        times = S.table_frames(0.0, 9.9, rate=10.0)
        rot, pos = S.sample_table(Chain(), bones, times)
        q, p, scale = S.quantise_table(rot, pos)
        self.assertEqual(len(times), 100)
        wolf = S.write_table(parents, {'idle': (0, 49), 'f:idle': (50, 99)}, q, p, scale,
                             keys=[('start', 0, 0), ('stop', 0, 49), ('start', 1, 50), ('stop', 1, 99)])
        human = S.write_table(parents, {'idle': (0, 20), 'walkforward': (21, 40)}, q[:41], p[:41], scale,
                              keys=[('start', 0, 0), ('stop', 0, 20), ('start', 1, 21), ('stop', 1, 40)])
        own = S.write_table(parents, {'idle': (0, 12)}, q[::-1][:13].copy(), p[::-1][:13].copy(), scale,
                            keys=[('start', 0, 0), ('stop', 0, 12)])
        with tempfile.TemporaryDirectory(prefix='aw-werewolf-tables-') as tmp:
            (Path(tmp) / 'progs').mkdir()
            (Path(tmp) / 'progs/wolf.awsk').write_bytes(wolf)
            (Path(tmp) / 'progs/human.awsk').write_bytes(human)
            (Path(tmp) / 'progs/beast.awsk').write_bytes(T.to_appended(own, 'progs/human.awsk'))
            native.NativeSourceTests.compile_run(self, 'aga_skel_release_test.c',
                                                 [SRC / 'aw_skel.c', SRC / 'aw_skel_load.c'],
                                                 cflags=SANITIZE + ['-Wl,--wrap=fclose'], arguments=[tmp])


class WerewolfWiring(unittest.TestCase):
    """What the native tests cannot reach: every route runs the one change, the windows refused while it holds, the
    draw takes the werewolf from the robe slot, dbg werewolf, New Game."""

    def test_every_route_runs_the_one_change(self):
        host = code('aw_mwhost.c')
        case = between(host, 'case AWF_BECOMEWEREWOLF:case AWF_UNDOWEREWOLF:case AWF_ISWEREWOLF:{',
                       'case AWF_SETWEREWOLFACROBATICS:{')
        self.assertIn('were_player_change(set,numbers,count);', case)
        self.assertNotIn('p->attr_base[i]=', case)                         # the stats live in the one rule now
        change = body(host, 'static void were_player_change(int set,const aw_mwcell_t *numbers,int count){')
        for needle in ('if(were.player==set)return;', 'aw_magic_readied=0;', 'AW_InventoryRead(AW_WERE_ROBE,&robe)',
                       'AW_WereChange(&were,set,&aw_state,have_robe?&robe:NULL,p,n,count,&were_last);',
                       'player_store(p);', 'aw_move_werewolf=were.player;'):
            self.assertIn(needle, change)
        # the typed BecomeWerewolf (console_werewolf), the typed UndoWerewolf (the function table) and dbg werewolf
        self.assertIn('host_call(k,who,AWF_BECOMEWEREWOLF,numbers,have?CONSOLE_WERE_ROWS-1:0,strings,0,&result);', host)
        dbg = body(host, 'static void werewolf_command(void){')
        self.assertIn('console_werewolf(-1,AW_MWVM_PLAYER,AW_MWCON_BECOMEWEREWOLF,"",answer,sizeof(answer));', dbg)
        self.assertIn('host_call(-1,AW_MWVM_PLAYER,AWF_UNDOWEREWOLF,numbers,0,strings,0,&result);', dbg)
        self.assertIn('if(!Q_strcasecmp(a,"werewolf")){werewolf_command();return;}', body(host, 'static void status(void){'))
        rules = code('aw_were_rules.c')
        for needle in ('AW_InventoryUnequip(s,id);', 'AW_InventoryEquipSlot(s,robe,AW_SLOT_ROBE)',
                       'AW_ItemAdd(s,AW_WERE_ROBE,-1)', 'AW_EffectsPurgeTemporary(player)'):
            self.assertIn(needle, rules)
        self.assertIn('aw_were_rules.c', (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8'))

    def test_the_windows_stay_shut_and_the_robe_is_not_listed(self):
        ui = code('aw_worldui.c')
        self.assertIn('svs.clients[0].edict->v.health<=0 || werewolf_now())return;', body(ui, 'void AW_InventoryOpen(void){'))
        self.assertIn('if(menu==AW_MENU_MAGIC && werewolf_now())return 0;', ui)
        self.assertIn('aw_worldui_werewolf=were_form;', code('aw_mwhost.c'))
        self.assertIn('if(AW_WERE_ROBE_ID(id))continue;', code('aw_cstrip.c'))
        self.assertIn('if(AW_WERE_ROBE_ID(wares[i].id))continue;', code('aw_dialwin.c'))

    def test_the_draw_follows_the_robe_slot(self):
        view = code('aw_view.c')
        for head in ('static int parts_ready(const char *race,int female) {',
                     'static int hand_parts_ready(const char *race,int female) {'):
            fn = body(view, head)
            self.assertLess(fn.index('race=look_race(race,female);'), fn.index('parts_race_check(race,female);'))
            self.assertIn('&& !were;s++)', fn)                             # the werewolf wears nothing
        self.assertIn('AW_PartsWerewolfWorn(aw_state.inventory.equipped[AW_SLOT_ROBE])', view)
        self.assertIn('|| parts_were)return;', body(view, 'static void parts_draws(edict_t *p) {'))
        ready = body(view, 'static int body_ready(void) {')
        self.assertIn('if(were)carried=0;', ready)
        self.assertIn('aw_hand_werewolf=hand_werewolf;', view)
        hands = body(code('aw_hand_models.c'), 'int AW_HandModelsApply(void)\n{')
        self.assertLess(hands.index('aw_hand_werewolf()'), hands.index('view=AW_HandView('))
        self.assertIn('aw_hand_parts_apply(race,female,0,cl.viewent.frame)', hands)
        parts = code('aw_player_parts.c')
        self.assertIn("a.p[0] >= 'a' && a.p[0] <= 'z'", parts)

    def test_every_frame_checks_the_look_and_the_tables_go_with_the_set(self):
        # wolffix (WEREWOLF-BODY-63, WEREWOLF-TABLES-STAY-LOADED-68): the look checked once a frame before anything is
        # drawn (a frame that draws neither set still lets the previous one go); out of the werewolf its tables are
        # given back after its parts; the status names a set only when one is assembled, and why the arms are not
        view = code('aw_view.c')
        frame = body(view, 'void AW_ViewFrame(void) {')
        self.assertLess(frame.index('were_look_frame();'), frame.index('p=local_player();'))
        unload = body(view, 'void AW_ViewPartsUnload(void) {')
        self.assertLess(unload.index('for(i=0;i<g;i++)part_drop(gone[i]);'), unload.index('were_tables_release();'))
        self.assertIn('if(!were_look(aw_character.valid && aw_character.female?1:0))were_tables_release();', unload)
        self.assertIn('parts_table=hparts_table=NULL;', unload)
        self.assertIn('AW_SkelTableRelease(were_tables[k],table_in_use)', view)
        status = body(view, 'void AW_ViewWerewolfStatus(void) {')
        self.assertIn('arms: none assembled now', status)
        self.assertIn('the hands are put away: assembled when the claws or fists are readied in first person', status)
        self.assertNotIn('arms: %d parts on %s (%s)\\n",body_parts', status)
        load = code('aw_skel_load.c')
        self.assertIn('long AW_SkelTableRelease (const char *name, int (*in_use) (const aw_skel_table_t *t))', load)
        self.assertIn('tables[i].released = 0;', body(load, 'const aw_skel_table_t *AW_SkelTableFor (const char *name)\n{'))
        # no header changed: the store's new entry is declared where it is used (aw_skel.h is in the reach of stages
        # that read the engine's limits, tools/build_cache.py C_HEADER_READERS)
        self.assertNotIn('AW_SkelTableRelease', code('aw_skel.h'))

    def test_new_game_and_the_save(self):
        host = code('aw_mwhost.c')
        reset = body(host, 'static void forced_reset(void){')
        self.assertIn('memset(&were,0,sizeof(were));', reset)
        self.assertIn('memset(&were_last,0,sizeof(were_last));', reset)
        self.assertIn('forced_reset();', body(host, 'static void actors_import(const unsigned char *data,int bytes){'))
        self.assertIn('actors_import(NULL,0);', body(host, 'void AW_MwscriptNewGameReset(void){'))
        self.assertIn('were.player?1:0', body(host, 'unsigned long AW_MwscriptDigest(void){'))
        self.assertIn('ACTOR_PART(were_export(out+n+s+t,capacity-n-s-t-8),"the werewolf state");', host)

    def test_dbg_werewolf_is_listed(self):
        rows = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8').splitlines()
        row = [r for r in rows if r.startswith('PLAYTESTING|werewolf|aw_mwscript_status|')]
        self.assertEqual(len(row), 1)
        self.assertTrue(row[0].split('|', 3)[3].startswith('[on / off; no argument: the status]'))
        self.assertLessEqual(len(row[0]), 382)
        console = code('aw_console.c')
        self.assertIn('strcpy(out+used," werewolf");used+=9;', console)
        self.assertIn('dbg werewolf', (ROOT / 'docs/AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8'))
        files = (ROOT / 'tools/release-files.json').read_text(encoding='utf-8')
        for name in ('engine/aga/src/aw_were_rules.c', 'engine/aga/src/aw_were_rules.h',
                     'tests/aga_werewolf_change_test.c', 'tests/aga_werewolf_look_test.c',
                     'tests/aga_werewolf_parts_test.c', 'tests/aga_skel_release_test.c', 'tests/test_werewolf_change.py'):
            self.assertIn('"%s"' % name, files)


if __name__ == '__main__':
    unittest.main()
