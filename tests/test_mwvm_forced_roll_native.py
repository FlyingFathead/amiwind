# SPDX-License-Identifier: GPL-3.0-only
"""dbg dbattack's sure roll and GetPCSleep in the real interpreter (DBG-DBATTACK-67, GETPCSLEEP-NOT-CARRIED-OUT-67).

A script shaped as Tribunal's dbAttackScript (asleep: one roll per sleep; a roll at or under its odds: WakeUpPC, the
assassin's PlaceAtPC, DBAttack 1) is compiled by the builder's own compiler and writer from a synthetic master and run
by the real interpreter (tests/aga_mwvm_forced_roll_test.c), its host answering GetPCSleep with a whole number, 1 while
a rest passes. With the game's roll about one rest in five brings the attack (odds 20 of 100); with the roll made sure
for that script (aw_mwvm.c AW_MwvmForceRandom, what dbg dbattack sets for its one rest) every rest does, and the roll
reaches the placement. Before v0.0.67 the host wrote GetPCSleep as a fraction, so the script never saw the sleep.
Synthetic data only; the native part runs in the Linux gate."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# src before tools (TEST-WORKER-SYSPATH-32)
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms  # noqa: E402
from test_mwscript import record, sub, scpt, glob  # noqa: E402

SCRIPT = '''Begin DBTest
float dbchance
short sleepOnce
short attacks
if ( GetPCSleep == 1 )
    if ( sleepOnce == 1 )
        return
    endif
    set sleepOnce to 1
    set dbchance to Random 100
    if ( dbchance <= 20 )
        WakeUpPC
        PlaceAtPC "db_assassin_test" 1 128 1
        set attacks to ( attacks + 1 )
        set DBAttack to 1
    endif
else
    set sleepOnce to 0
endif
End DBTest
'''


def compiled():
    tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-forced-'))
    try:
        out = [record('TES3', sub('HEDR', b'\0' * 300)), glob('DBAttack', 's', 0), scpt('DBTest', SCRIPT),
               record('NPC_', sub('NAME', 'db_assassin_test'), sub('FNAM', 'Dark Brotherhood Assassin'))]
        (tmp / 'Morrowind.esm').write_bytes(b''.join(out))
        data = GameData().load(tmp)
        prog, comp = compile_program(data, None, handwritten=(), rooms={})
        raw, _ = awms.write(prog, comp, bindings(prog), {'ops_per_run': 500})
        return prog, comp, raw
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class ForcedRollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.comp, raw = compiled()
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-forced-native-'))
        (cls.tmp / 'test.awm').write_bytes(raw)
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(ROOT / 'tests/aga_mwvm_forced_roll_test.c'), str(src / 'aw_mwvm.c'),
                                '-o', str(cls.tmp / 'forced')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(cls.tmp / 'forced'), str(cls.tmp / 'test.awm'),
                              str(cls.prog.scripts.index['dbtest']), str(cls.prog.globals.index['dbattack'])],
                             capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        cls.out = run.stdout
        cls.rows = {m.group(1): [int(v) for v in m.groups()[1:]] for m in re.finditer(
            r'^(game|sure) rests (\d+) wakes (\d+) places (\d+) dbattack (\d+) forced (\d+)$', run.stdout, re.M)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_script_compiles_whole(self):
        dbtest = next(c for c in self.comp if c.name.casefold() == 'dbtest')
        self.assertEqual(dbtest.notyet, [])
        self.assertNotIn('warn', self.out)

    def test_the_games_roll_brings_the_attack_on_some_rests(self):
        rests, wakes, places, dbattack, forced = self.rows['game']
        self.assertEqual(rests, 200)
        self.assertEqual(wakes, places)                       # each attack wakes and places once
        self.assertTrue(10 <= wakes <= 80, wakes)             # odds 21 of 100: about 42 of 200
        self.assertEqual((dbattack, forced), (1, 0))

    def test_the_sure_roll_brings_it_on_every_rest(self):
        rests, wakes, places, dbattack, forced = self.rows['sure']
        self.assertEqual((rests, wakes, places, dbattack, forced), (200, 200, 200, 1, 1))
        reads, rolls = map(int, re.search(r'^reads (\d+) forced_rolls (\d+)$', self.out, re.M).groups())
        self.assertEqual(rolls, 200)                          # one sure roll a rest
        self.assertGreaterEqual(reads, 400 * 4)               # GetPCSleep read every frame of every rest


if __name__ == '__main__':
    unittest.main()
