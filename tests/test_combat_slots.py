# SPDX-License-Identifier: GPL-3.0-only
"""A script's StartCombat beyond four fighters (MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68).

The original has no limit on the actors fighting at once (OpenMW 0.51 aiextensions.cpp OpStartCombat ->
mechanicsmanagerimp.cpp startCombat stacks an AiCombat package on the actor). The game's scripts start six actors at
the player in one tick, and fifteen against each other in the Skaal village attack. The combat layer had four fight
slots: the fifth StartCombat was refused, a third pair of actors never fought, and a dead actor's body could not be
laid down while four fought. It has sixteen now (aw_combat.c FIGHTS); aw_combat_slots lowers the slots in use for a
comparison.

The map gate keeps edicts free for four fighters' held weapon and shield (tools/map_engine_limits.py runtime_edicts
reads aw_combat.c SLOTS, which stays 4, so no map's edict room and no world key changes); a fighter past those draws
its items only while the map has edicts to spare beyond everything kept.

The behaviour runs natively: aw_mwhost.c's own to_fighter and host_combat are cut out of the file (file-static in an
engine file too large to link alone) into a slice tests/aga_combat_slots_test.c includes, around the combat fixture's
synthetic server. AMIWIND_RUNTIME_SOURCE selects another engine tree: against the engine before the change the same
fixture fails at its checks A2, A3, D1 and E1."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT / 'engine/aga')))
SRC = ENGINE / 'src'
COMPILER = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))


def function(text, head):
    """The C definition starting at HEAD, to its closing brace at column 0."""
    at = text.index(head)
    return text[at:text.index('\n}\n', at) + 3]


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8', errors='replace'), flags=re.S)


ORDERS = '/* --- the fight orders (MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68, slice 2).'
HOST_COMBAT = 'static void host_combat(int instance,int target,int verb,int other){'


def host_slice(text):
    """to_fighter and host_combat; with the kept orders (slice 2) everything from their heading to host_combat's end
    (order_set, fight_start, fight_order, fight_orders, orders_calmed) and fight_resume, and AW_SLICE_ORDERS says so.
    An engine tree from before them gives the two functions alone, and the fixture fails at its checks."""
    head = '/* cut from aw_mwhost.c by tests/test_combat_slots.py */\n'
    fighter = function(text, 'static void to_fighter(const aw_actor_t *a,aw_fighter_t *f){')
    if ORDERS not in text:
        return head + fighter + function(text, HOST_COMBAT)
    at = text.index(ORDERS)
    return (head + '#define AW_SLICE_ORDERS 1\n' + fighter
            + text[at:text.index('\n}\n', text.index(HOST_COMBAT, at)) + 3]
            + function(text, 'static int fight_resume(edict_t *e){'))


def compile_and_run(test):
    with tempfile.TemporaryDirectory(prefix='amiwind-combatslots-') as tmp:
        tmp = Path(tmp)
        native.tree_project_version().generate_native(ROOT / 'VERSION', tmp)
        (tmp / 'host_combat_slice.c').write_text(
            host_slice((SRC / 'aw_mwhost.c').read_text(encoding='utf-8', errors='replace')), encoding='utf-8')
        exe = tmp / 'check'
        sources = [SRC / n for n in ('aw_combat.c', 'aw_combat_rules.c', 'aw_move_rules.c', 'aw_npcpath.c', 'mathlib.c',
                                     'aw_anim.c', 'aw_cast_rules.c', 'aw_effects.c', 'aw_format.c')]
        cmd = [COMPILER, '-fsanitize=undefined', '-fno-sanitize-recover=all', '-DAW_ANIM_HOST_TEST', '-std=gnu89',
               '-ffunction-sections', '-fdata-sections', '-include', str(ROOT / 'tests/aga_test_files.h'),
               '-Wl,--gc-sections', '-I' + str(tmp), '-I' + str(SRC), '-I' + str(ROOT / 'tests'),
               str(ROOT / 'tests/aga_combat_slots_test.c'), *[str(p) for p in sources],
               str(ROOT / 'tests/aga_hook_stubs.c'), '-lm', '-o', str(exe)]
        built = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        return subprocess.run([str(exe)], cwd=tmp, capture_output=True, text=True, timeout=120)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class CombatSlotsNativeTests(unittest.TestCase):
    def test_six_at_the_player_three_pairs_a_body_and_the_comparison_cap(self):
        run = compile_and_run(self)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for line in ('PASS  A3 all six fight the player at once', 'PASS  D1 the third pair fights too',
                     'PASS  E1 a dead body is laid down while four fight',
                     'PASS  F1 with four slots the fifth and sixth are refused',
                     'PASS  G2 a fifth draws none while fewer than 76 edicts are spare',
                     # slice 2: the kept orders
                     'PASS  B1 the fifth and sixth keep their order against the player on their records',
                     'PASS  B4 the nearer waiting order is taken up once a slot frees',
                     'PASS  C1 a StartCombat on an actor that is not loaded is kept on its record',
                     'PASS  C3 it fights within a second of loading near the player',
                     'PASS  C4 an order waits while its actor is beyond the actors\' processing range',
                     'PASS  R2 the change list\'s kept fight starts again against the other actor, not the player',
                     'PASS  R3 with its target not loaded it does not turn on the player',
                     'PASS  R5 an order whose target died ends',
                     'PASS  H1 after the calm nobody is marked as fighting'):
            self.assertIn(line, run.stdout)
        self.assertIn('VERDICT: 43 passed, 0 failed', run.stdout)


class CombatSlotsContractTests(unittest.TestCase):
    def test_sixteen_fight_slots_and_the_map_gate_value_unchanged(self):
        combat = code('aw_combat.c')
        self.assertIn('#define FIGHTS 16', combat)
        self.assertIn('static slot_t slots[FIGHTS];', combat)
        self.assertIn('AW_COMBAT_FIGHTERS_MAX>=FIGHTS?1:-1', combat)
        # the map gate's reader and the world keys: the value they read stays (BUILD-ENGINE-SOURCE-KEY-BROAD-36)
        import engine_limits
        import map_engine_limits
        self.assertEqual(engine_limits.define('aw_combat.c', 'SLOTS'), 4)
        self.assertEqual(map_engine_limits.runtime_edicts(), 74)
        self.assertIn('#define ITEMS_KEPT (2+SLOTS*AW_ITEMS_KINDS+AW_INVENTORY_DROPS+AW_ITEMS_CARRIERS)', combat)
        # no loop or table is still sized by the four
        self.assertEqual(re.findall(r'\bSLOTS\b', combat).count('SLOTS'), 4, 'the define, ITEMS_KEPT and the two tests of the rule')

    def test_a_fighter_past_the_kept_edicts_asks_before_it_draws_its_items(self):
        engage = function(code('aw_combat.c'), 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        self.assertIn('if(!items_spare())items_left_out++;\n    else AW_ItemsShow(e,s->item);', engage)
        spare = function(code('aw_combat.c'), 'static int items_spare(void) {')
        self.assertIn('if(n<SLOTS)return 1;', spare)            # the first four: no edict scan
        self.assertIn('if(e->free && (e->freetime<2 || sv.time-e->freetime>.5))spare++;', spare)   # ED_Alloc's rule
        self.assertIn('e->freetime < 2 || sv.time - e->freetime > 0.5',
                      (SRC / 'pr_edict.c').read_text(encoding='utf-8', errors='replace'))

    def test_the_cap_is_one_cvar_and_every_caller_asks_the_slots(self):
        combat = code('aw_combat.c')
        self.assertIn('static cvar_t slots_cvar={"aw_combat_slots","16"};', combat)
        self.assertIn('Cvar_RegisterVariable(&slots_cvar);', combat)
        self.assertIn('if(!Q_strcasecmp(a,"slots") && Cmd_Argc()<=3){', combat)
        engage = function(combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        self.assertIn('if(used>=cap){full_refused++;', engage)
        # the two callers that tested a literal four against the player's hostiles ask the slots themselves
        self.assertIn('if(AW_CombatSlotsFree()<=0)return 0;}',
                      function(code('aw_mwhost.c'), 'static int crime_attack(edict_t *e,int fight){'))
        self.assertNotIn('AW_CombatHostiles()>=4', code('aw_mwhost.c'))
        ambient = code('aw_ambient.c')
        self.assertIn('if(AW_CombatSlotsFree()<=0){st.aggro_full++;return;}', ambient)
        self.assertNotIn('FIGHT_SLOTS', ambient)
        # declared by its callers: aw_combat.h is keyed by the CHIM world stage
        self.assertNotIn('AW_CombatSlotsFree', (SRC / 'aw_combat.h').read_text(encoding='utf-8'))

    def test_the_kept_orders_are_wired_into_the_tick_the_save_and_the_reset(self):
        host = code('aw_mwhost.c')
        tick = function(host, 'void AW_MwscriptTick(float dt){')
        self.assertLess(tick.index('join_fights(dt);'), tick.index('fight_orders(dt);'))
        # every one-shot fight start writes the order with its target; no caller sets the flag by hand any more
        self.assertEqual(host.count('|=AWL_COMBAT'), 0)
        self.assertEqual(host.count('&=~AWL_COMBAT'), 0)
        combat = function(host, HOST_COMBAT)
        self.assertIn('if(!a || e==sv_player){actor_misses++;return;}', combat)     # an actor not loaded is no miss
        self.assertIn('fight_order(a,e,o,b);', combat)
        self.assertIn('fight_order(a,e,NULL,NULL);', combat)
        self.assertIn('AW_ActorOrder(a,0);', combat)                                # StopCombat
        start = function(host, 'static int fight_start(aw_actor_t *a,edict_t *e,edict_t *o,aw_actor_t *b){')
        # the slots are asked before a sheet is read from disk (STARTCOMBAT-SHEET-READ-BEFORE-SLOT-68)
        self.assertLess(start.index('AW_CombatSlotsFree()'), start.index('AW_CombatActorLoad('))
        self.assertIn('order_set(a,AW_ACTOR_PLAYER_REF);combat_starts++;',
                      function(host, 'static int crime_attack(edict_t *e,int fight){'))
        self.assertIn('AW_ActorOrder(a,0);', function(host, 'static void crime_calm(edict_t *e){'))
        self.assertIn('order_set(a,ref_of_edict(x));', function(host, 'static void join_against(edict_t *e,edict_t *x){'))
        # the hooks: the calm (DBG-COMBAT-CALM-LEAVES-HOSTILE-MARK-68) and the change list's kept fight
        # (COMBAT-RESUMED-FIGHT-TARGETS-PLAYER-68)
        self.assertIn('aw_combat_calmed=orders_calmed;', host)
        self.assertIn('aw_actors_fight_resume=fight_resume;', host)
        calm = code('aw_combat.c')
        self.assertEqual(calm.count('if(aw_combat_calmed)aw_combat_calmed();'), 2)    # dbg combat calm, dbg combat off
        actors = code('aw_actors.c')
        self.assertEqual(actors.count('c->fight && FightResume ('), 2)                # SpawnOne, ApplyLoaded
        self.assertIn('return aw_actors_fight_resume ? aw_actors_fight_resume (ent) : AW_CombatTestEngage (ent, 0);',
                      actors)
        # a load and a New Game: the session's counts start again, the first pass looks at the records the save gave;
        # the New Game check counts the orders
        imp = function(host, 'static void actors_import(const unsigned char *data,int bytes){')
        self.assertIn('orders_kept=orders_taken=orders_dropped=0;orders_cursor=0;orders_clock=0;orders_live=1;', imp)
        self.assertIn('AW_ActorOrderCount()', function(host, 'unsigned long AW_MwscriptDigest(void){'))
        # declared by their users: aw_combat.h is keyed by the CHIM world stage, aw_actors.h stays as it was
        for header in ('aw_combat.h', 'aw_actors.h'):
            text = (SRC / header).read_text(encoding='utf-8')
            self.assertNotIn('aw_combat_calmed', text)
            self.assertNotIn('aw_actors_fight_resume', text)

    def test_the_command_is_in_the_debug_menu_and_the_docs(self):
        for path, words in (('config/debug-commands.txt', ' / slots N / calm]'),
                            ('docs/AMIWIND_CONSOLE_COMMANDS.md', ' / slots N / calm]'),
                            ('docs/COMBAT.md', '`dbg combat slots N`')):
            with self.subTest(path=path):
                self.assertIn(words, (ROOT / path).read_text(encoding='utf-8'))
        self.assertIn(b'aw_combat_slots 16\n', __import__('build_aga').ACTOR_LOGIC_LINES)


if __name__ == '__main__':
    unittest.main()
