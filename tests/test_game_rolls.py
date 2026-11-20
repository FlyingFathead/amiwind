# SPDX-License-Identifier: GPL-3.0-only
"""Game rolls (REST-CUT-TOO-OFTEN-67, engine/aga/src/aw_roll.h, docs/RESTING.md "The roll").

On the v0.0.67 release image 7 of 8 twelve-hour wilderness rests were cut where the original's rule gives one in four.
The roll was rand()%hours from the C library (newlib in the SDK: a 64-bit state, the top 31 bits returned), and
nothing seeded it: every boot started from the same state, and so did the fights' per-encounter seeds and the
scripts' Random. These tests hold the fix: every roll that decides a game outcome goes through AW_Roll (one draw, its
top bits), the generator and the other two streams start from the machine's clock once a boot, a recording still
replays the same rolls, and nothing of it reaches a file the world stages key whole.

The native fixture models newlib's rand from the library's own code and measures the cut rate over many boots and
boot paths. The rate is near one in four with the old roll too (newlib is good in every bit); what fails on the old
engine is the seeding and the remainder rolls (the contracts below), and, on a C library that keeps low bits, the rate.
"""
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
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

# Files whose remainder rolls only place, colour or time effects and sounds (particles, embers, flames, light
# radii, a sound's start offset): no game outcome. Every other engine file takes its rolls from AW_Roll.
EFFECT_ONLY = frozenset(('r_part.c', 'cl_tent.c', 'cl_main.c', 'cl_parse.c', 'aw_magic.c', 'aw_guard_torch.c',
                         'aw_torch.c', 'aw_lava.c', 'snd_dma.c'))
ROLL_FILES = ('aw_wait.c', 'aw_alchemy.c', 'aw_anim.c', 'aw_animkit.c', 'aw_cast.c', 'aw_dialwin.c', 'aw_glut.c',
              'aw_mwhost.c', 'sv_move.c', 'pr_cmds.c')
REMAINDER = re.compile(r'\brand\s*\(\s*\)\s*[%&]')


def code(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def body(name, start):
    """The body of the DEFINITION that starts with START (a prototype, START followed by ';', is skipped)."""
    text = code(SRC / name)
    found = re.search(re.escape(start) + r'\s*\{', text)
    if not found:
        raise AssertionError('%s: %s not found' % (name, start))
    brace = found.end() - 1
    depth = 0
    for i in range(brace, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[brace:i + 1]
    raise AssertionError('%s: %s has no end' % (name, start))


def newlib_draws(state, count):
    """newlib's rand (lib_a-rand.o of the SDK's libm020/libm881/libc.a): the state, then COUNT outputs."""
    out = []
    for _ in range(count):
        state = (state * 0x5851F42D4C957F2D + 1) & ((1 << 64) - 1)
        out.append((state >> 32) & 0x7FFFFFFF)
    return out


def encounter_seed(boot, encounter):
    """aw_combat.c begin_encounter's per-encounter seed (aw_combat_seed 0, the recorder off)."""
    seed = (0x41C64E6D ^ ((boot * 2246822519) & 0xFFFFFFFF) ^ (encounter * 2654435761)) & 0xFFFFFF
    return seed or 1


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class GameRollNativeTests(unittest.TestCase):
    def test_one_draw_each_rate_over_boots_boot_seed_recording_and_low_bits(self):
        native.NativeSourceTests().compile_run('aga_game_roll_test.c', [SRC / 'aw_rest_rules.c'], cflags=UBSAN)


class GameRollModelTests(unittest.TestCase):
    def test_the_model_is_the_librarys_own(self):
        # the library's first-call path stores the state 0x5851F42D_4C957F2E and returns 0x5851F42D (1481765933)
        first = newlib_draws(1, 3)
        self.assertEqual(first[0], 0x5851F42D)
        self.assertEqual(first, [1481765933, 1085377743, 1270216262])

    def test_the_old_fixed_streams_stay_for_boot_seed_zero(self):
        # the host tests never set a boot seed: the fights keep the seeds every boot had before (encounters 1, 2, 3)
        self.assertEqual([encounter_seed(0, n) for n in (1, 2, 3)], [15808476, 11058447, 6300542])
        # a boot seed moves every one of them
        for boot in (1, 0x2545F491, 0xFFFFFFFF):
            with self.subTest(boot=boot):
                self.assertTrue(all(encounter_seed(boot, n) != encounter_seed(0, n) for n in (1, 2, 3)))


class GameRollSourceTests(unittest.TestCase):
    def test_no_remainder_roll_decides_a_game_outcome(self):
        found = []
        for path in sorted(SRC.rglob('*.c')):
            if path.name in EFFECT_ONLY:
                continue
            for line in code(path).splitlines():
                if REMAINDER.search(line):
                    found.append('%s: %s' % (path.relative_to(SRC), line.strip()))
        self.assertEqual(found, [], 'take game rolls from AW_Roll (aw_roll.h): one draw, its top bits')
        for name in ROLL_FILES:
            with self.subTest(name=name):
                text = code(SRC / name)
                self.assertIn('#include "aw_roll.h"', (SRC / name).read_text(encoding='utf-8', errors='replace'))
                self.assertRegex(text, r'\bAW_Roll\s*\(')

    def test_the_helper_takes_one_draw_and_its_top_bits(self):
        roll = code(SRC / 'aw_roll.h')
        helper = roll[roll.find('static inline int AW_Roll'):]
        self.assertEqual(len(re.findall(r'\brand\s*\(', helper)), 1)
        self.assertLess(helper.find('rand()'), helper.find('if(n<2)return 0;'))   # drawn even for 0 and 1
        self.assertIn('/((unsigned long long)RAND_MAX+1ULL)', helper)

    def test_the_rest_roll_and_its_log_lines(self):
        run = body('aw_wait.c', 'static void rest_run(int wanted)')
        self.assertIn('rest_roll=rest_sleeping && rest_list[0] && rest_data?AW_Roll(wanted):-1;', run)
        self.assertIn('AW_RestInterruptAt(&rest_settings,wanted,rest_roll)', run)
        finish = body('aw_wait.c', 'static void rest_finish(int woken)')
        # the cut's line stays as the proofs read it; the roll follows on its own line
        self.assertIn('Con_Printf("rest: %s (after %ld of %ld h, sleep list %s)\\n"', finish)
        self.assertIn('rest_roll_line(roll,sizeof(roll));Con_Printf("rest: %s\\n",roll);', finish)
        self.assertLess(finish.find('sleep list %s)\\n"'), finish.find('Con_Printf("rest: %s\\n",roll);'))
        self.assertIn('"not interrupted"', finish)
        self.assertIn('"roll %d of 0..%d, a cut below %d"', code(SRC / 'aw_wait.c'))

    def test_one_boot_seed_from_the_clock_for_every_stream(self):
        init = body('host.c', 'void Host_Init (quakeparms_t *parms)')
        self.assertLess(init.find('AW_ResetBootMark ();'), init.find('boot_seed ();'))
        self.assertLess(init.find('boot_seed ();'), init.find('host_initialized = true;'))
        self.assertLess(init.find('Cbuf_InsertText ("exec quake.rc\\n");'), init.find('boot_seed ();'))
        seed = body('host.c', 'static void boot_seed (void)')
        for call in ('AW_ClockSeed ()', 'srand ((unsigned)h);', 'AW_CombatBootSeed (h);', 'AW_MwvmBootSeed (h);',
                     '"Random: boot seed %lu'):
            self.assertIn(call, seed)
        clock = body('amiga_stubs.c', 'unsigned long AW_ClockSeed(void)')
        self.assertIn('DateStamp(&stamp);', clock)
        self.assertIn('ReadEClock(&eclock);', clock)
        # aw_seed N still sets the C library's generator for a test
        self.assertRegex(body('aw_quickchar.c', 'static void seed_command(void)'), r'srand\s*\(')

    def test_the_seed_stays_out_of_the_files_the_world_keys_whole(self):
        # BUILD-CHIM-KEY-SYS-AMIGA-WHOLE-67: sys_amiga.c is keyed whole into the CHIM stages; the seed lives elsewhere
        platform = code(SRC / 'sys_amiga.c')
        for name in ('boot_seed', 'AW_ClockSeed', 'AW_CombatBootSeed', 'AW_MwvmBootSeed', 'srand'):
            self.assertNotIn(name, platform)
        reviewed = (ROOT / 'tests' / 'test_stage_key_engine_defines.py').read_text(encoding='utf-8')
        whole = reviewed[reviewed.find('WHOLE_ALLOWED'):reviewed.find('))', reviewed.find('WHOLE_ALLOWED'))]
        for name in (*ROLL_FILES, 'aw_roll.h', 'host.c', 'amiga_stubs.c', 'aw_combat.c', 'aw_mwvm.c', 'aw_recorder.c'):
            with self.subTest(name=name):
                self.assertNotIn('engine/aga/src/' + name, whole)

    def test_the_fights_and_the_scripts_random_start_from_the_boot_seed(self):
        begin = body('aw_combat.c', 'static void begin_encounter(void)')
        self.assertLess(begin.find('recorder_seed'), begin.find('encounters+1'))
        self.assertIn('if(!seed){seed=(0x41c64e6dUL^((boot_seed*2246822519UL)&0xffffffffUL)^((encounters+1)*2654435761UL))'
                      '&0xffffffUL;if(!seed)seed=1;}', begin)
        self.assertIn('void AW_CombatBootSeed(unsigned long seed) {boot_seed=seed&0xffffffffUL;}', code(SRC / 'aw_combat.c'))
        vm = code(SRC / 'aw_mwvm.c')
        self.assertIn('static uint32_t start_value(void){return start_rng?start_rng:0x2545F491u;}', vm)
        self.assertIn('void AW_MwvmBootSeed(unsigned long seed){boot_rng=start_rng=(uint32_t)seed;}', vm)
        self.assertIn('void AW_MwvmStartSeed(unsigned long seed){start_rng=seed?(uint32_t)seed:boot_rng;}', vm)
        self.assertIn('vm.rng=start_value();vm.loaded=1;', body(
            'aw_mwvm.c', 'int AW_MwvmLoad(const unsigned char *data,unsigned long bytes,const aw_mwvm_host_t *host)'))

    def test_a_recording_replays_whatever_the_boot_seeded(self):
        streams = body('aw_recorder.c', 'static void seed_streams(void)')
        self.assertIn('AW_MwvmSeed(stream_seed(0xC0DE0002U));', streams)
        self.assertIn('AW_MwvmStartSeed(stream_seed(0xC0DE0002U));', streams)
        self.assertIn('AW_MwvmStartSeed(0);', body('aw_recorder.c', 'static void release(void)'))
        self.assertRegex(body('aw_recorder.c', 'static void frame_seed(unsigned long n)'), r'srand\s*\(')
        self.assertRegex(body('host.c', 'void _Host_Frame (float time)'),
                         r'if\s*\(\s*!AW_RecorderActive\s*\(\s*\)\s*\)\s*rand\s*\(\s*\)\s*;')


if __name__ == '__main__':
    unittest.main()
