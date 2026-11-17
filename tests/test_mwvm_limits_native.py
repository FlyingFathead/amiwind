# SPDX-License-Identifier: GPL-3.0-only
"""The script engine's tables sized by the build (EXPANSION-SCRIPT-LIMITS-66; MWVM-INSTANCES-256-66,
MWVM-PARKING-STORE-SMALL-66, MWSCRIPT-MEMBER-LOOKUP-COST-66, MWSCRIPT-MEMBER-QUIET-READER-66).

Up to v0.0.66-dev11 the interpreter had 256 attached instances, 4,096 local values, 2,816 parked objects and 9,216
parked values as constants: a map with more scripted placements (Raven Rock: 350) left the rest without their scripts,
and a long game lost values once the store was full. Now the builder counts the whole game (tools/mwscript/plan.py),
writes the counts into the file (CONF, 20 bytes) and the engine allocates exactly that at load; a count past the plan
is told to the host and counted, never a silent drop. Here synthetic masters are compiled by the builder's own compiler,
planner and writer, and the real interpreter runs them (tests/aga_mwvm_limits_test.c): a map of 300 scripted placements
runs every script; 3,000 objects with 12,000 values are parked over 30 map changes and come back intact, parked and
attached again; the values a save keeps go back after a reset; a quiet reader wakes when the object it reads changes its
own variable (the SHARED flag); a too-small plan is reported, not crashed; a forgotten reference starts clean; an older
file's 8-byte CONF gives the earlier constants. Synthetic data only; the native part runs in the Linux gate."""
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
# src before tools (TEST-WORKER-SYSPATH-32): tools/mwad.py would otherwise shadow the src/mwad package for the modules
# the discovery imports after this one
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript.codegen import SCRIPT_SHARED, SCRIPT_VOLATILE  # noqa: E402
from mwscript import awms, plan as planner  # noqa: E402
from test_mwscript import record, sub, scpt, glob, cell_exterior  # noqa: E402

COUNTER = 'Begin Counter\nshort done\nif ( done == 0 )\n    set done to 1\n    set Count to Count + 1\nendif\nEnd'
# every script does something another can see (a global), or the compiler would leave it out as inert
KEEPER = '''Begin Keeper
short a
long b
float c
short d
if ( a == 0 )
    set a to Seed
    set b to Seed * 1000
    set c to 0.5
    set d to 7
    set Marker to 1
endif
End'''
TARGET = 'Begin Target\nshort v\nif ( Go == 1 )\n    set v to 5\nendif\nEnd'
READER = 'Begin Reader\nshort seen\nset seen to "target_obj".v\nset Mirror to seen\nEnd'
MARKER = 'Begin Marker\nif ( Go == 1 )\n    set Marker to 1\nendif\nEnd'


def master(scripts, objects, cells, globals_=()):
    out = [record('TES3', sub('HEDR', b'\0' * 300))] + [glob(n, 's', 0) for n in globals_]
    out += [scpt(name, text) for name, text in scripts.items()]
    out += [record('ACTI', sub('NAME', ident), sub('SCRI', script)) for ident, script in objects]
    out += [cell_exterior(x, y, refs) for (x, y), refs in cells]
    return b''.join(out)


def compiled(master_bytes, conf=None):
    tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-limits-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master_bytes)
        data = GameData().load(tmp)
        prog, comp = compile_program(data, None, handwritten=(), rooms={})
        binds = bindings(prog, comp)
        p = planner.plan(prog, comp, binds, data)
        c = dict(awms.DEFAULT_CONF, ops_per_run=500, **{k: p[k] for k in ('instances', 'cells', 'parked', 'park_cells')})
        c.update(conf or {})
        raw, _ = awms.write(prog, comp, binds, c)
        return prog, comp, raw, p
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def big_map(count=300):
    """COUNT scripted placements in one 3 by 3 block (more than the old 256 instances)."""
    cells = {}
    for i in range(count):
        cells.setdefault((i % 3, (i // 3) % 3), []).append((1000 + i, 'ctr_%d' % (i % 7), (16 * i, 0, 0)))
    return master({'Counter': COUNTER}, [('ctr_%d' % k, 'Counter') for k in range(7)], list(cells.items()), ['Count'])


def many_maps(count=3000):
    """COUNT scripted placements with 4 values each, one a cell: 12,000 values over 3,000 objects (past the old 2,816
    objects and 9,216 values). Every 9 consecutive references stand in one 3 by 3 block of cells (a loaded map, the
    plan's unit): the harness attaches them 9 at a time, a map change each."""
    def cell(i):
        block, k = i // 9, i % 9
        return (3 * (block % 20) + k % 3, 3 * (block // 20) + k // 3)
    cells = [(cell(i), [(5000 + i, 'keep_%d' % (i % 5), (0, 0, 0))]) for i in range(count)]
    return master({'Keeper': KEEPER}, [('keep_%d' % k, 'Keeper') for k in range(5)], cells, ['Seed', 'Marker'])


BLOCK = 9   # the harness's chunk: one 3 by 3 block of many_maps


def shared_pair():
    return master({'Reader': READER, 'Target': TARGET}, [('reader_obj', 'Reader'), ('target_obj', 'Target')],
                  [((0, 0), [(7001, 'reader_obj', (0, 0, 0)), (7002, 'target_obj', (8, 0, 0))])], ['Go', 'Mirror'])


class PlanTests(unittest.TestCase):
    def test_the_plan_counts_the_busiest_map_and_every_object_with_values(self):
        prog, comp, raw, p = compiled(big_map(300))
        self.assertGreaterEqual(p['instances'], 300 + 2)          # the map's 300 + the scratch instances
        self.assertEqual(p['report']['busiest_map']['placed'], 300)
        self.assertGreaterEqual(p['cells'], 300)                   # one value each
        self.assertEqual(p['parked'], 300)                         # every one has a value to keep
        self.assertEqual(p['park_cells'], 300)
        prog, comp, raw, p = compiled(many_maps(3000))
        self.assertEqual(p['parked'], 3000)
        self.assertEqual(p['park_cells'], 12000)
        self.assertLess(p['instances'], 100)                       # a 3 by 3 block holds 9 of them
        self.assertGreaterEqual(p['instances'], 9 + 2)
        f = awms.read(raw)
        self.assertEqual(f['CONF_rows'], 1)
        self.assertEqual(len(f['CONF']), awms.CONF_BYTES)
        c = awms.conf_read(f['CONF'])
        self.assertEqual((c['parked'], c['park_cells']), (3000, 12000))
        self.assertEqual(c['ops_per_run'], 500)

    def test_a_script_without_values_is_not_parked(self):
        # an activator script with no variable keeps nothing (OpenMW's RefData::setLocals leaves its locals empty too)
        prog, comp, raw, p = compiled(master({'Marker': MARKER}, [('marker', 'Marker')],
                                             [((0, 0), [(9000 + i, 'marker', (8 * i, 0, 0)) for i in range(20)])],
                                             ['Go', 'Marker']))
        self.assertEqual((p['parked'], p['park_cells']), (0, 0))
        self.assertGreaterEqual(p['instances'], 20)

    def test_the_builder_refuses_what_the_engine_cannot_address(self):
        header = (ROOT / 'engine/aga/src/aw_mwvm.h').read_text(encoding='utf-8')
        maxima = {k: int(re.search(r'#define AW_MWVM_%s_MAX (\d+)' % k, header).group(1))
                  for k in ('INSTANCES', 'CELLS', 'PARKED', 'PARK_CELLS')}
        self.assertEqual(maxima, {'INSTANCES': planner.ENGINE_MAX_INSTANCES, 'CELLS': planner.ENGINE_MAX_CELLS,
                                  'PARKED': planner.ENGINE_MAX_PARKED, 'PARK_CELLS': planner.ENGINE_MAX_PARK_CELLS})
        defaults = {k: int(re.search(r'#define AW_MWVM_%s_DEFAULT (\d+)' % k, header).group(1))
                    for k in ('INSTANCES', 'CELLS', 'PARKED', 'PARK_CELLS')}
        self.assertEqual(defaults, {'INSTANCES': awms.DEFAULT_CONF['instances'], 'CELLS': awms.DEFAULT_CONF['cells'],
                                    'PARKED': awms.DEFAULT_CONF['parked'],
                                    'PARK_CELLS': awms.DEFAULT_CONF['park_cells']})
        with self.assertRaises(ValueError):
            planner.check_plan({'instances': planner.ENGINE_MAX_INSTANCES + 1, 'cells': 1, 'parked': 1, 'park_cells': 1})
        with self.assertRaises(ValueError):
            awms.conf_bytes(dict(awms.DEFAULT_CONF, park_cells=planner.ENGINE_MAX_PARK_CELLS + 1))
        # the host's allowances the plan counts with are the host's own numbers
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('#define HELD_MAX %d' % planner.HELD_MAX, host)
        self.assertIn('#define PLACE_COPIES %d' % planner.PLACE_COPIES, host)

    def test_the_stage_writes_the_plan(self):
        text = (ROOT / 'tools/prepare_mwscript.py').read_text(encoding='utf-8')
        self.assertIn("addons=tuple(MASTERS[1:])", text)             # every master's placements, not only what is bound
        self.assertIn("'tables': {k: sizes_plan[k]", text)

    def test_a_target_of_member_reads_is_shared_and_a_reader_is_not_volatile(self):
        prog, comp, raw, p = compiled(shared_pair())
        names = {c.name: c for c in comp}
        self.assertTrue(names['Target'].flags & SCRIPT_SHARED)
        self.assertFalse(names['Reader'].flags & SCRIPT_SHARED)
        self.assertFalse(names['Reader'].flags & SCRIPT_VOLATILE)   # it wakes on the change, it does not run every frame
        self.assertFalse(names['Target'].flags & SCRIPT_VOLATILE)
        header = (ROOT / 'engine/aga/src/aw_mwcode.h').read_text(encoding='utf-8')
        self.assertIn('#define AWS_SHARED %d' % SCRIPT_SHARED, header)

    def test_a_member_operation_is_one_step(self):
        # MWSCRIPT-MEMBER-LOOKUP-COST-66: the object row remembers its instance, the parked store has a hash; member()
        # walks neither table
        vm = (ROOT / 'engine/aga/src/aw_mwvm.c').read_text(encoding='utf-8')
        member = vm[vm.index('static aw_mwcell_t *member('):]
        member = member[:member.index('\n}\n')]
        self.assertIn('vm.obj_inst[object]', member)
        self.assertNotIn('for(k=0;k<vm.ninst;k++)', member)
        self.assertNotIn('for(i=0;i<vm.nparked;i++)', vm[vm.index('static parked_t *find_parked('):].split('\n}\n')[0])
        self.assertIn('hash_slot(ref)', vm)


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InterpreterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-mwvm-limits-native-'))
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(ROOT / 'tests/aga_mwvm_limits_test.c'), str(src / 'aw_mwvm.c'),
                                '-o', str(cls.tmp / 'limits')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_file(self, name, raw, mode, *args):
        path = self.tmp / (name + '.awm')
        path.write_bytes(raw)
        r = subprocess.run([str(self.tmp / 'limits'), str(path), mode] + [str(a) for a in args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.splitlines()
        values = {}
        for line in lines:
            parts = line.split()
            if parts:
                values.setdefault(parts[0], parts[1:])
        return lines, values

    def test_a_map_of_300_scripted_placements_runs_every_script(self):
        prog, comp, raw, p = compiled(big_map(300))
        lines, v = self.run_file('big', raw, 'attach', -1, -1, prog.globals.index['count'])
        self.assertEqual(v['attached'], ['300'])
        self.assertEqual(v['count'], ['300'])                        # every one of the 300 scripts ran
        self.assertEqual(v['refused'], ['0', '0', '0', '0'])
        self.assertEqual(v['full'], ['calls', '0'])
        self.assertFalse([l for l in lines if l.startswith('warn')], lines)
        self.assertEqual(v['plan'][0], str(p['instances']))

    def test_3000_parked_objects_with_12000_values_come_back_intact(self):
        prog, comp, raw, p = compiled(many_maps(3000))
        lines, v = self.run_file('many', raw, 'park', prog.globals.index['seed'], -1, -1, BLOCK)
        self.assertEqual(v['rows'], ['3000'])
        self.assertEqual(v['parked-check'], ['mismatches', '0'])      # every value read back parked
        self.assertEqual(v['back-check'], ['mismatches', '0'])        # and attached again
        self.assertEqual(v['refused'], ['0', '0', '0', '0'])
        self.assertEqual(v['usage'][2:], ['3000', '12000'])            # the store holds them all
        self.assertFalse([l for l in lines if l.startswith('warn')], lines)

    def test_the_values_a_save_keeps_go_back_after_a_reset(self):
        prog, comp, raw, p = compiled(many_maps(3000))
        lines, v = self.run_file('round', raw, 'roundtrip', prog.globals.index['seed'], -1, -1, BLOCK)
        self.assertEqual(v['kept'], ['12000', 'values'])              # a, b, c, d of every object (none is 0)
        self.assertNotEqual(v['reset-check'], ['mismatches', '0'])    # a new game: gone
        self.assertEqual(v['put'], ['12000'])
        self.assertEqual(v['loaded-check'], ['mismatches', '0'])      # a load: back
        self.assertEqual(v['back-check'], ['mismatches', '0'])

    def test_a_forgotten_reference_starts_clean(self):
        prog, comp, raw, p = compiled(many_maps(300))
        lines, v = self.run_file('forget', raw, 'forget', prog.globals.index['seed'], -1, -1, BLOCK)
        self.assertEqual(v['forget'], ['1'])
        self.assertEqual(v['after-forget'], ['found', '0'])
        self.assertEqual(v['forget-again'], ['0'])
        self.assertEqual(v['fresh'], ['a', '0'])                      # not the old chunk's 1
        self.assertEqual(v['ran'], ['a', '77'])
        self.assertEqual(v['refused'], ['0', '0', '0', '0'])

    def test_a_quiet_reader_wakes_when_the_object_it_reads_changes_its_own_variable(self):
        prog, comp, raw, p = compiled(shared_pair())
        lines, v = self.run_file('shared', raw, 'shared', -1, prog.globals.index['go'])
        self.assertEqual(v['attached'], ['2'])
        self.assertEqual(v['seen-before'], ['0'])
        self.assertEqual(v['seen-second-frame'], ['5'])               # the reader ran again after the target's change
        self.assertEqual(v['seen-later'], ['5'])

    def test_a_plan_too_small_is_told_to_the_host_and_counted(self):
        prog, comp, raw, p = compiled(big_map(300), conf={'instances': 10, 'cells': 400})
        lines, v = self.run_file('small', raw, 'full', -1, -1, prog.globals.index['count'])
        self.assertEqual(v['plan'][:2], ['10', '400'])
        self.assertEqual(v['attached'], ['10'])
        self.assertEqual(v['count'], ['10'])
        self.assertEqual(v['full'][:1], ['attached'])                 # the host's full(): "attached instances"
        self.assertEqual(v['refused'][0], '290')                       # every refusal counted
        self.assertFalse([l for l in lines if l.startswith('warn')], lines)   # told through full(), not warn()
        prog, comp, raw, p = compiled(many_maps(300), conf={'parked': 20, 'park_cells': 80})
        lines, v = self.run_file('smallpark', raw, 'park', prog.globals.index['seed'], -1, -1, BLOCK)
        self.assertEqual(v['full'][:2], ['parked', 'objects'])
        self.assertEqual(v['refused'][2], '280')

    def test_an_older_file_gets_the_earlier_constants(self):
        prog, comp, raw, p = compiled(big_map(20))
        f = awms.read(raw)
        # the directory's CONF length cut to the old 8 bytes: the engine reads only those
        raw = bytearray(raw)
        for i in range(struct.unpack_from('>H', raw, 6)[0]):
            if raw[16 + 16 * i:20 + 16 * i] == b'CONF':
                struct.pack_into('>I', raw, 16 + 16 * i + 12, 8)
        lines, v = self.run_file('older', bytes(raw), 'plan')
        self.assertEqual(v['plan'], ['256', '4096', '2816', '9216'])
        self.assertEqual(f['CONF_rows'], 1)


if __name__ == '__main__':
    unittest.main()
