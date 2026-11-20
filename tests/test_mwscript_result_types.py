# SPDX-License-Identifier: GPL-3.0-only
"""The value the engine's script host hands back has the type the compiler gave the function (GETPCSLEEP-NOT-CARRIED-OUT-67).

The compiler (tools/mwscript/functions.py, codegen.py notyet) declares each function's result: 'f' a fraction, any
other a whole number; the script's comparisons and sums read the value as declared. The host (engine/aga/src/
aw_mwhost.c) writes result->f or result->i. A mismatch reads the other field's bits: GetPCSleep wrote a fraction until
v0.0.67, so a script's whole-number "GetPCSleep == 1" read 1065353216 and never held (the Dark Brotherhood attack of
Tribunal's dbAttackScript never came). This walks every host case and every "function==AWF_X" result of the host and
fails on any function whose result field is not the declared one.

The rest's side of the same bug: the hours of a rest pass over the frames (aw_wait.c AW_RestTick, called every frame from
host.c before the scripts run, also while the world is held under the window), so a script sees GetPCSleep 1 in at
least one frame of every rest (OpenMW 0.51 waitdialog.hpp getSleeping, timeadvancer.cpp); the rules themselves run
natively in tests/aga_wait_test.c (test_aga_native_source)."""
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):          # src first on the path (TEST-WORKER-SYSPATH-32)
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from mwscript.functions import FUNCTIONS  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def field(ret):
    """The result field a declared return letter is read from."""
    return 'f' if ret == 'f' else 'i'


def host_results(text):
    """[(function names, the fields written)] of every host case group of TEXT that writes a result (its body up to the
    next case label or the end of its switch), and of every 'function==AWF_X' test followed by a result write."""
    out = []
    parts = re.split(r'((?:case AWF_\w+:\s*)+)', text)
    for k in range(1, len(parts), 2):
        labels = [m.lower() for m in re.findall(r'case AWF_(\w+):', parts[k])]
        body = re.split(r'\n\}\n', parts[k + 1] if k + 1 < len(parts) else '')[0]
        writes = set(re.findall(r'result->(i|f)\s*=', body))
        if writes:
            out.append((labels, writes))
    for m in re.finditer(r'function==AWF_(\w+)\)\s*\{?\s*result->(i|f)\s*=', text):
        out.append(([m.group(1).lower()], {m.group(2)}))
    return out


def mismatches(text):
    """The host results whose field differs from what the compiler declares: a lone function writing the other field,
    or a group writing a field none of its value functions declares, or missing one they declare."""
    bad = []
    for names, writes in host_results(text):
        declared = {n: FUNCTIONS[n].ret for n in names if n in FUNCTIONS}
        want = {field(r) for r in declared.values() if r != '-'}
        if len(names) == 1 and want and writes != want:
            bad.append((names[0], declared.get(names[0]), sorted(writes)))
        elif len(names) > 1 and want and (writes - want or want - writes):
            bad.append((','.join(names), sorted(declared.items()), sorted(writes)))
    return bad


class HostResultTypes(unittest.TestCase):
    def test_every_host_result_has_the_compilers_type(self):
        text = code('aw_mwhost.c')
        self.assertGreater(len(host_results(text)), 40)      # the walk reaches the host's cases
        self.assertEqual(mismatches(text), [])

    def test_the_walk_catches_the_old_getpcsleep(self):
        # the regression guard on the v0.0.66 form: a whole-number function written as a fraction fails
        old = 'switch(function){\n    case AWF_GETPCSLEEP:result->f=(float)AW_RestSleeping();return AW_MWVM_CALL_READ;\n}\n'
        self.assertEqual(mismatches(old), [('getpcsleep', 'l', ['f'])])
        self.assertEqual(FUNCTIONS['getpcsleep'].ret, 'l')
        self.assertIn('result->i=AW_RestSleeping();return AW_MWVM_CALL_READ;', code('aw_mwhost.c'))


def _sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def _record(tag, *subs):
    payload = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(payload), 0, 0) + payload


def _scpt(name, text):
    head = name.encode('cp1252').ljust(32, b'\0') + struct.pack('<5I', 0, 0, 0, 0, 0)
    return _record('SCPT', _sub('SCHD', head), _sub('SCTX', text.encode('cp1252')))


class SleepReadCompiles(unittest.TestCase):
    def test_getpcsleep_is_a_whole_volatile_read_carried_out(self):
        # the compiler's side (a synthetic master, no game data): GetPCSleep goes to the host as a whole-number value
        # (flags 0x80, no 0x40) and is carried out; reading it makes the script VOLATILE (v0.0.67: the hours of a rest
        # pass over a few frames without the state generation moving, so a quiet reader would sleep through them)
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program
        from mwscript.codegen import SCRIPT_VOLATILE, SCRIPT_NOTYET
        from mwscript.functions import FUNCTION_NUMBERS
        from mwscript import awms
        text = ('Begin SleepWatch\nshort woke\nif ( GetPCSleep == 1 )\n\tif ( woke == 0 )\n\t\tWakeUpPC\n'
                '\t\tset woke to 1\n\tendif\nendif\nEnd SleepWatch\n')
        tmp = Path(tempfile.mkdtemp(prefix='aw-sleep-read-'))
        try:
            (tmp / 'Morrowind.esm').write_bytes(_record('TES3', _sub('HEDR', b'\0' * 300)) + _scpt('SleepWatch', text))
            data = GameData().load(tmp)
            _prog, compiled = compile_program(data, None)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        watch = next(c for c in compiled if c.name == 'SleepWatch')
        self.assertEqual(watch.notyet, [])
        self.assertFalse(watch.flags & SCRIPT_NOTYET)
        self.assertTrue(watch.flags & SCRIPT_VOLATILE)
        calls = [a for _, n, a in awms.decode(watch.code) if n == 'NOTYET']
        self.assertEqual([a[0] for a in calls], [FUNCTION_NUMBERS['getpcsleep'], FUNCTION_NUMBERS['wakeuppc']])
        self.assertEqual(calls[0][2], 0x80)                  # a value, a whole number, no numbers handed over
        self.assertEqual(calls[1][2], 0)                     # WakeUpPC: no value


class RestInterruption(unittest.TestCase):
    def test_a_rest_cut_short_brings_the_regions_creature(self):
        # REST-CUT-NO-CREATURE-67 (OpenMW 0.51 waitdialog.cpp onWaitingInterrupted, worldimp.cpp spawnRandomCreature):
        # before v0.0.67 nothing set aw_rest_spawn, so a rest cut short brought no creature. The engine's host sets it
        # to rest_creature: one pick of the sleep list at the player's level from the actor table, 220 units in front
        # of the player as a summon appears, its record's script attached; the interruption's line also goes to the log
        host = code('aw_mwhost.c')
        self.assertIn('aw_rest_spawn=rest_creature;', host)
        creature = host[host.index('static void rest_creature(const char *sleep_list){'):]
        creature = creature[:creature.index('\n}\n')]
        self.assertIn('#define REST_CREATURE_DISTANCE (220*0.25f)', host)
        self.assertIn('text=AW_ActorsLevelledText(sleep_list,key,&n,&hash)', creature)
        self.assertIn('place_spot(base,yaw,REST_CREATURE_DISTANCE,0,1,local);', creature)
        self.assertIn('AW_ActorsPlaceRow(key,local,yaw+180)?AW_ActorsSpawnVisitor(', creature)
        self.assertIn('AW_MwvmLevelledScript(hash,&script)', creature)
        wait = code('aw_wait.c')
        cut = wait[wait.index('    if(interrupted){'):]
        cut = cut[:cut.index('        return;\n    }')]
        self.assertIn('Con_Printf("rest: %s (after %ld of %ld h, sleep list %s)\\n"', cut)
        self.assertIn('if(aw_rest_spawn && rest_list[0])aw_rest_spawn(rest_list);', cut)


class RestHoursOverFrames(unittest.TestCase):
    def test_the_rest_ticks_every_frame_before_the_scripts(self):
        host = code('host.c')
        frame = host[host.index('aw_load_phase = "frame: ticks (save, intro, wait)";'):]
        tick = frame.index('        AW_RestTick();')
        self.assertNotIn('AW_ModalWorldFrozen', frame[frame.rindex('\n', 0, tick):tick + 20])   # not held with the world
        self.assertLess(tick, frame.index('AW_MwscriptTick('))
        self.assertIn('#include "aw_rest.h"', host)

    def test_getpcsleep_reads_the_hours_passing_not_the_open_window(self):
        wait = code('aw_wait.c')
        self.assertIn('int AW_RestSleeping(void){return modal==3 && rest_sleeping && rest_running;}', wait)
        run = wait[wait.index('static void rest_run(int wanted)'):wait.index('void AW_RestTick(void)')]
        self.assertNotIn('AW_ClockAdvance', run)              # Enter starts the hours, it does not pass them
        self.assertIn('rest_running=1;', run)
        tick = wait[wait.index('void AW_RestTick(void)'):wait.index('static void rest_finish(int woken)\n{')]
        self.assertIn('if(rest_done>=end){rest_finish(0);return;}', tick)   # the end comes a frame after the last hour
        self.assertIn('AW_ClockAdvance(3600000)', tick)
        wake = wait[wait.index('int AW_RestWake(void){'):]
        self.assertIn('if(rest_running)rest_finish(1);else close_modal();', wake[:wake.index('\n}\n')])


if __name__ == '__main__':
    unittest.main()
