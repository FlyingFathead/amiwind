# SPDX-License-Identifier: GPL-3.0-only
"""A script's read and write of another object's variables (MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66).

`"heart_test".countHits` compiles to GETM / SETM / SETMS with the object's row in the OBJS section (u32 reference, u16
id, u16 script, u16 placed, u16 kind: tools/mwscript/awms.py). The interpreter read the script at the id's offset, so
every such read gave 0 and every write was lost (Dagoth Ur's shield never followed the Heart's countHits). Here a
synthetic master is compiled by the builder's own compiler and writer, the object rows are checked (the id is not the
script, so the old offset cannot find it), and the real interpreter runs it (tests/aga_mwvm_member_test.c): a read, a
whole-number, a fraction and a short write across two objects with different scripts, a script's own variable by its
name (the global instance), and the target parked while it is read and written. Synthetic data only; the native part
runs in the Linux gate."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# src before tools (TEST-WORKER-SYSPATH-32, seen again in v0.0.66-dev11): tools/mwad.py would otherwise shadow the src/mwad package for every
# module the discovery imports after this one in the same process
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript import awms  # noqa: E402
from test_mwscript import record, sub, scpt, glob, cell_exterior  # noqa: E402

SCRIPTS = {
    # names first in the file so the object ids and the scripts get different numbers
    'FillerOne': 'Begin FillerOne\nshort a\nset a to 1\nset Unused to a\nEnd',
    'FillerTwo': 'Begin FillerTwo\nshort b\nset b to 2\nset Unused to b\nEnd',
    'HeartTest': '''Begin HeartTest
short countHits
long total
float rate
short started
if ( started == 0 )
    set started to 1
    set countHits to 3
endif
End''',
    'DagothTest': '''Begin DagothTest
short seen
short stage
long totalSeen
float rateSeen
short levelSeen
short hitsSeen
if ( stage == 0 )
    if ( "heart_test".countHits == 3 )
        set seen to "heart_test".countHits
        set "heart_test".total to 70000
        set "heart_test".rate to 1.5
        set "heart_test".countHits to 5
        set "KeeperTest".level to 4
        set stage to 1
    endif
elseif ( stage == 1 )
    set totalSeen to "heart_test".total
    set rateSeen to "heart_test".rate
    set hitsSeen to "heart_test".countHits
    set levelSeen to "KeeperTest".level
    set stage to 2
elseif ( stage == 2 )
    if ( ParkNow == 1 )
        set "heart_test".total to 9
        set "heart_test".countHits to "heart_test".countHits + 1
        set stage to 3
    endif
endif
End''',
    # never placed, never started: its variable is reached by its name (row kind 1)
    'KeeperTest': 'Begin KeeperTest\nshort level\nEnd',
}
HEART, DAGOTH = 501, 502


def compiled():
    tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-member-'))
    try:
        out = [record('TES3', sub('HEDR', b'\0' * 300)), glob('ParkNow', 's', 0), glob('Unused', 's', 0)]
        out += [scpt(name, text) for name, text in SCRIPTS.items()]
        out += [record('ACTI', sub('NAME', 'filler_obj'), sub('SCRI', 'FillerOne')),
                record('ACTI', sub('NAME', 'heart_test'), sub('SCRI', 'HeartTest')),
                record('ACTI', sub('NAME', 'dagoth_test'), sub('SCRI', 'DagothTest'))]
        out.append(cell_exterior(0, 0, [(500, 'filler_obj', (16, 0, 0)), (HEART, 'heart_test', (0, 0, 0)),
                                        (DAGOTH, 'dagoth_test', (8, 0, 0))]))
        (tmp / 'Morrowind.esm').write_bytes(b''.join(out))
        data = GameData().load(tmp)
        prog, comp = compile_program(data, None, handwritten=(), rooms={})
        raw, _ = awms.write(prog, comp, bindings(prog), {'ops_per_run': 500})
        return prog, comp, raw
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def slot(prog, script, name):
    return prog.script_locals[script][name.casefold()][1]


class MemberRowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.comp, cls.raw = compiled()

    def test_the_reader_compiles_to_member_operations(self):
        code = self.comp[self.prog.scripts.index['dagothtest']].code
        ops = [name for _, name, _ in awms.decode(code)]
        self.assertGreaterEqual(ops.count('GETM'), 6)      # countHits, total, rate, countHits, level, countHits
        self.assertGreaterEqual(ops.count('SETM'), 3)      # total (long), rate (float), total again
        self.assertGreaterEqual(ops.count('SETMS'), 3)     # countHits (short) twice, level (short)

    def test_the_rows_id_is_not_its_script(self):
        f = awms.read(self.raw)
        rows = [struct.unpack_from('>IHHHH', f['OBJS'], 12 * k) for k in range(f['OBJS_rows'])]
        names = awms.strings(f)
        by_id = {names[r[1]].casefold(): r for r in rows}
        heart = by_id['heart_test']
        self.assertEqual(heart[0], HEART)
        self.assertEqual(heart[2], self.prog.scripts.index['hearttest'])
        self.assertEqual(heart[4], 0)
        # the old read took the id (a string index) as the script: here it is not HeartTest, so it found nothing
        self.assertNotEqual(heart[1], heart[2])
        keeper = by_id['keepertest']
        self.assertEqual((keeper[2], keeper[4]), (self.prog.scripts.index['keepertest'], 1))
        self.assertNotEqual(keeper[1], keeper[2])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class MemberInterpreterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.comp, raw = compiled()
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-member-native-'))
        (cls.tmp / 'test.awm').write_bytes(raw)
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(ROOT / 'tests/aga_mwvm_member_test.c'), str(src / 'aw_mwvm.c'),
                                '-o', str(cls.tmp / 'member')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(cls.tmp / 'member'), str(cls.tmp / 'test.awm'), str(HEART), str(DAGOTH),
                              str(cls.prog.scripts.index['keepertest']), str(cls.prog.globals.index['parknow'])],
                             capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        cls.out = run.stdout.splitlines()
        cls.phase = {}
        name = None
        for line in cls.out:
            if line.startswith('== '):
                name = line[3:]
                cls.phase[name] = {}
            elif name and line.split()[0] in ('heart', 'dagoth', 'keeper'):
                cls.phase[name][line.split()[0]] = line.split()[1:]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def heart(self, phase, name):
        return self.phase[phase]['heart'][slot(self.prog, 'hearttest', name)]

    def dagoth(self, phase, name):
        return self.phase[phase]['dagoth'][slot(self.prog, 'dagothtest', name)]

    def test_the_slots_the_harness_prints(self):
        # the harness prints HeartTest's slot 2 and DagothTest's slot 3 as fractions: rate and rateSeen
        self.assertEqual(slot(self.prog, 'hearttest', 'rate'), 2)
        self.assertEqual(slot(self.prog, 'dagothtest', 'rateseen'), 3)

    def test_a_read_and_the_writes_across_two_objects(self):
        self.assertIn('attached 3', self.out)
        self.assertFalse([l for l in self.out if l.startswith('warn')], self.out)
        # GETM: the heart's own 3, read by the reader
        self.assertEqual(self.dagoth('attached', 'seen'), '3')
        # SETM (a whole number past a short and a fraction) and SETMS (a short), written into the heart's locals
        self.assertEqual(self.heart('attached', 'total'), '70000')
        self.assertEqual(self.heart('attached', 'rate'), '1.50')
        self.assertEqual(self.heart('attached', 'countHits'), '5')
        # and read back by the reader on its next run
        self.assertEqual(self.dagoth('attached', 'totalSeen'), '70000')
        self.assertEqual(self.dagoth('attached', 'rateSeen'), '1.50')
        self.assertEqual(self.dagoth('attached', 'hitsSeen'), '5')
        self.assertEqual(self.dagoth('attached', 'stage'), '2')

    def test_a_scripts_own_variable_by_its_name(self):
        # "KeeperTest".level: the script's global instance (not started), its own variable 4, read back as 4
        self.assertEqual(self.phase['attached']['keeper'], ['4', 'running', '0'])
        self.assertEqual(self.dagoth('attached', 'levelSeen'), '4')

    def test_a_parked_target_is_read_and_written(self):
        self.assertIn('detach 1', self.out)
        # the heart's values parked: the reader wrote 9 into total and read 5 + 1 into countHits there
        self.assertEqual(self.heart('parked', 'total'), '9')
        self.assertEqual(self.heart('parked', 'countHits'), '6')
        self.assertEqual(self.dagoth('parked', 'stage'), '3')
        # back in its place, the heart keeps them (its own script does not set them again: started is 1)
        self.assertIn('back 1', self.out)
        self.assertEqual(self.heart('back', 'total'), '9')
        self.assertEqual(self.heart('back', 'countHits'), '6')
        self.assertEqual(self.heart('back', 'started'), '1')

    def test_the_interpreter_reads_the_rows_script(self):
        # AW_MwvmObjectScript and the member operations read the same field (one set of readers, aw_mwvm.c)
        vm = (ROOT / 'engine/aga/src/aw_mwvm.c').read_text(encoding='utf-8')
        member = vm[vm.index('static aw_mwcell_t *member('):]
        member = member[:member.index('\n}\n')]
        self.assertIn('int script=obj_script(object)', member)
        self.assertNotIn('U16(r+4)', member)
        self.assertEqual(vm.count('U16(OBJ_ROW(k)+6)'), 1)
        self.assertIn('int AW_MwvmObjectScript(int k){return ON && k>=0 && k<vm.nobjs?obj_script(k):AWM_NONE;}', vm)


if __name__ == '__main__':
    unittest.main()
