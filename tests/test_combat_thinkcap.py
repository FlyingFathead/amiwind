# SPDX-License-Identifier: GPL-3.0-only
"""The fight's think cap and the account of where a fight's time goes (MWSCRIPT-STARTCOMBAT-FOUR-FIGHTERS-68, slice 3).

Measured in play with six fighters a greeting starts at the player: the mean think is cheap (0.3 to 0.5 ms), single
thinks reached 80 and 111 ms, and one frame spent 297 ms in the combat layer, of which the thinks were the smaller
part. Fighters started in one tick share their think time, so one frame in every five runs all their thinks.

The change: `aw_combat_think_cap N` lets at most N fighters think in a frame, in turn, and more when a fighter would
wait past the original's reaction time (OpenMW 0.51 aitimer.hpp AI_REACTION_TIME, 0.25 s); off by default, so the
fights run as before until the comparison in play decides. And `dbg combat` names the worst frame of the encounter
by its parts, the worst think by its fighter, and the worst frame of fight starts, each with its disk wait.

The behaviour runs natively (tests/aga_combat_thinkcap_test.c around the combat fixture's synthetic server).
AMIWIND_RUNTIME_SOURCE selects another engine tree: against the engine before the change the fixture fails at its
checks R1 to R5, A0b, B1, B3, C1 and C2."""
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


def compile_and_run(test):
    with tempfile.TemporaryDirectory(prefix='amiwind-thinkcap-') as tmp:
        tmp = Path(tmp)
        native.tree_project_version().generate_native(ROOT / 'VERSION', tmp)
        exe = tmp / 'check'
        sources = [SRC / n for n in ('aw_combat.c', 'aw_combat_rules.c', 'aw_move_rules.c', 'aw_npcpath.c', 'mathlib.c',
                                     'aw_anim.c', 'aw_cast_rules.c', 'aw_effects.c', 'aw_format.c')]
        cmd = [COMPILER, '-fsanitize=undefined', '-fno-sanitize-recover=all', '-DAW_ANIM_HOST_TEST', '-std=gnu89',
               '-ffunction-sections', '-fdata-sections', '-include', str(ROOT / 'tests/aga_test_files.h'),
               '-Wl,--gc-sections', '-I' + str(tmp), '-I' + str(SRC), '-I' + str(ROOT / 'tests'),
               str(ROOT / 'tests/aga_combat_thinkcap_test.c'), *[str(p) for p in sources],
               str(ROOT / 'tests/aga_hook_stubs.c'), '-lm', '-o', str(exe)]
        built = subprocess.run(cmd, capture_output=True, text=True)
        test.assertEqual(built.returncode, 0, built.stdout + built.stderr)
        return subprocess.run([str(exe)], cwd=tmp, capture_output=True, text=True, timeout=120)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(COMPILER, 'a host C compiler is required')
class ThinkCapNativeTests(unittest.TestCase):
    def test_the_cap_spreads_the_thinks_and_is_off_by_default(self):
        run = compile_and_run(self)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        for line in ('PASS  R4 sixteen at a 100 ms frame: seven, so nobody waits past 0.25 s',
                     'PASS  A0 the cap is off by default',
                     'PASS  A1 control: all six think in the frame after the start',
                     'PASS  B1 two think in the frame after the start',
                     'PASS  B2 every fighter has thought within three frames',
                     'PASS  B3 no frame runs more than two thinks',
                     'PASS  B4 over a second every fighter thinks as often as before',
                     'PASS  C1 five of the six think in a frame: the share grows past the cap',
                     'PASS  D1 all six think in one frame again',
                     # AMBIENT-SOUND-READ-IN-FRAME-68: against the engine before it, E0 to E3 fail
                     'PASS  E0 the fight\'s sounds have a loader hook',
                     'PASS  E1 every fighter\'s and the player\'s ability list is asked at the start, before any blow',
                     'PASS  E2 each of the fight\'s sounds is loaded at the start',
                     'PASS  E3 no sound is loaded by a frame of the fight'):
            self.assertIn(line, run.stdout)
        self.assertIn('VERDICT: 21 passed, 0 failed', run.stdout)


class ThinkCapContractTests(unittest.TestCase):
    def test_the_cap_is_one_unsaved_setting_and_holds_only_the_think(self):
        combat = code('aw_combat.c')
        self.assertIn('static cvar_t think_cap={"aw_combat_think_cap","0"};', combat)       # off, not saved
        self.assertIn('Cvar_RegisterVariable(&think_cap);', combat)
        physics = function(combat, 'void AW_CombatPhysics(void) {')
        # a held think keeps its time (next_think is not moved), so its turn comes with its true step
        self.assertIn('if(sv.time>=s->next_think && !(allow>>i&1))thinks_held++;', physics)
        # the swing's strike, the cast's release and the animation are outside the cap: they run every frame
        self.assertLess(physics.index('npc_strike(s,p);'), physics.index('thinks_held++;'))
        self.assertLess(physics.index('cast_release(s);'), physics.index('thinks_held++;'))
        self.assertLess(physics.index('thinks_held++;'), physics.index('animate(s);'))
        # a seed replays a fight: the turns start from the first slot with every encounter
        self.assertIn('think_from=0;', function(combat, 'static void begin_encounter(void) {'))
        # declared in the file: aw_combat.h is keyed by the CHIM world stage
        self.assertNotIn('AW_CombatThinkShare', (SRC / 'aw_combat.h').read_text(encoding='utf-8'))

    def test_dbg_combat_says_where_the_time_went(self):
        report = function(code('aw_combat.c'), 'static void report(void) {')
        for words in ('Worst fight frame: %.1f ms at f%ld (disk wait %.1f ms)', 'Worst think: %.1f ms (disk wait %.1f ms) by %s',
                      'Worst frame of fight starts (since the area loaded)', 'Think cap: '):
            self.assertIn(words, report)
        combat = code('aw_combat.c')
        # the sheet read and the engage are both on the fight starts' account
        self.assertIn('start_cost(Sys_FloatTime()-t0,disk_wait()-d0,1);',
                      function(combat, 'int AW_CombatActorLoad(const char *id,aw_fighter_t *out) {'))
        self.assertEqual(function(combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
                         .count('start_cost(Sys_FloatTime()-t0,disk_wait()-d0,0);'), 2)

    def test_what_a_blow_reads_is_read_before_the_blows(self):
        # AMBIENT-SOUND-READ-IN-FRAME-68: the worst fight frames of the v0.0.68-dev9 session were the blows' disk waits
        combat = code('aw_combat.c')
        engage = function(combat, 'int AW_CombatEngage(edict_t *e,const aw_fighter_t *fighter,const char *layout) {')
        # the fight's start reads the fighter's and the player's ability lists and looks at the fight's sounds,
        # before its first voice line, on the fight starts' account
        self.assertIn('fight_warm(e);', engage)
        self.assertLess(engage.index('fight_warm(e);'), engage.index('voice(e,AW_VOICE_START);'))
        self.assertLess(engage.index('fight_warm(e);'), engage.rindex('start_cost('))
        warm = function(combat, 'static void fight_warm(edict_t *e) {')
        self.assertIn('aw_combat_effect_magnitude(e,AW_EFFECT_PARALYZE)', warm)
        self.assertIn('aw_combat_effect_magnitude(p,AW_EFFECT_PARALYZE)', warm)
        self.assertIn('fight_sounds_warm();', warm)
        # the area's first sheet (read at the area load) loads the sounds; a new area looks again
        load = function(combat, 'int AW_CombatActorLoad(const char *id,aw_fighter_t *out) {')
        self.assertIn('if(ok && !sounds_warmed)fight_sounds_warm();', load)
        self.assertLess(load.index('fight_sounds_warm();'), load.index('start_cost('))
        self.assertIn('sounds_warmed=0;', function(combat, 'void AW_CombatSceneSpawn(void) {'))
        # the hook is declared in the file: aw_combat.h is keyed by the CHIM world stage
        self.assertNotIn('aw_combat_sound_warm', (SRC / 'aw_combat.h').read_text(encoding='utf-8'))
        anim = code('aw_anim.c')
        self.assertIn('aw_combat_sound_warm=combat_sound_warm;', function(anim, 'void AW_AnimInit(void) {'))
        # the host keeps a whole list per actor (one read answers every effect of a blow), not eight single answers
        host = code('aw_mwhost.c')
        self.assertIn('return AW_ActorPassiveKept(a,ref,effect,AW_EffectsGeneration()+creation_generation);',
                      function(host, 'static float passive_of(const aw_actor_t *a,uint32_t ref,int effect){'))
        self.assertNotIn('PASSIVE_MEMO', host)
        # a bark's line found in the pool once is not looked up on disk again
        self.assertIn('if(!pool_has_line(hash,path))return 0;', function(anim, 'int AW_VoicePlay(edict_t *e,const unsigned char hash[8]) {'))
        self.assertIn('Before the blows: ', function(combat, 'static void report(void) {'))

    def test_the_setting_is_in_the_combat_page(self):
        self.assertIn('`aw_combat_think_cap`', (ROOT / 'docs/COMBAT.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
