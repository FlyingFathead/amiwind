# SPDX-License-Identifier: GPL-3.0-only
"""A new game starts the original's run-once scripts (NPC-STORY-DISABLED-AT-START-42, v0.0.62).

Main's `if ( CharGenState == 1 )` block names the scripts a new game starts once (Startup, whose Disable lines hold
the Dreamers and the falling mage back, and VampireCheck); the builder writes them as the NEWG section, the build
check refuses a file whose new game would not reach its disables, and the engine's interpreter starts them once on
AW_MwvmNewGame. Synthetic master only (no game data); the native part runs in the Linux gate."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

from mwscript.gamedata import GameData, new_game_scripts, unconditional_disables  # noqa: E402
from mwscript.compiler import compile_program, bindings  # noqa: E402
from mwscript.codegen import SCRIPT_HANDWRITTEN, SCRIPT_NOTYET  # noqa: E402
from mwscript.opcodes import OPCODES  # noqa: E402
from mwscript import awms, newgame  # noqa: E402
from test_mwscript import record, sub, scpt, glob, cell_exterior, HARNESS  # noqa: E402

MAIN = '''begin Main
; this script starts when the game is run
if ( MenuMode == 0 )
\tSet Random100 to Random, 101
endif
StartScript Elsewhere
if  ( CharGenState == 1 )\t\t; a new game
\tStartScript Startup
\tStartScript VampireCheck
\tif ( ScriptRunning, CharGen == 0 )
\t\tStartScript CharGen
\tendif
endif
end'''

STARTUP = '''begin Startup
short testVar
;for a quest
"sleeper_01"->Disable
scaffold_x->Disable  ; a comment
"twice_obj"->disable
"nowhere_obj"->Disable
if ( testVar == 5 )
\t"cond_obj"->Disable
endif
StopScript Startup
set testVar to 1
End'''

SCRIPTS = {
    'Main': MAIN, 'Startup': STARTUP,
    'VampireCheck': 'begin VampireCheck\nshort x\nset x to 1\nset VampCount to 2\nend',
    'CharGen': 'begin CharGen\nset CharGenState to -1\nend',
    'Elsewhere': 'begin Elsewhere\nend',
    'SleeperEnable': '''begin SleeperEnable
short test
Set test to GetJournalIndex QA_Dream
if ( GetDisabled == 0 )
\tReturn
endif
if ( test == 50 )
\tEnable
\tReturn
endif
End''',
    # the falling mage's journal: Fall compiles to nothing (OpenMW OpFall does nothing)
    'FallingTest': 'begin FallingTest\n"sleeper_01"->Fall\nFall\n"scaffold_x"->Disable\nend',
}


def master(scripts=SCRIPTS):
    out = [record('TES3', sub('HEDR', b'\0' * 300))]
    out += [glob('CharGenState', 's', 0), glob('Random100', 's', 0), glob('VampCount', 's', 0)]
    out += [record('DIAL', sub('NAME', 'QA_Dream'), sub('DATA', b'\x04'))]
    out += [scpt(n, t) for n, t in scripts.items()]
    out += [record('ACTI', sub('NAME', 'sleeper_01'), sub('SCRI', 'SleeperEnable')),
            record('ACTI', sub('NAME', 'scaffold_x')), record('ACTI', sub('NAME', 'twice_obj')),
            record('ACTI', sub('NAME', 'nowhere_obj')), record('ACTI', sub('NAME', 'cond_obj')),
            record('BOOK', sub('NAME', 'journal_x'), sub('SCRI', 'FallingTest'))]
    out.append(cell_exterior(-2, -8, [(201, 'sleeper_01', (0, 0, 0)), (202, 'scaffold_x', (8, 0, 0)),
                                      (203, 'twice_obj', (16, 0, 0)), (204, 'twice_obj', (24, 0, 0)),
                                      (205, 'cond_obj', (32, 0, 0)), (206, 'journal_x', (40, 0, 0))]))
    return b''.join(out)


def compiled_program(scripts=SCRIPTS):
    tmp = Path(tempfile.mkdtemp(prefix='aw-newgame-'))
    try:
        (tmp / 'Morrowind.esm').write_bytes(master(scripts))
        data = GameData().load(tmp)
        prog, compiled = compile_program(data, None, handwritten=('chargen*',), rooms={})
        return prog, compiled, data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class NewGameWeatherTests(unittest.TestCase):
    # v0.0.63 (OPENING-WEATHER-NOT-CLOUDY-63): CharGen's ChangeWeather, carried by AmiWind's own opening, becomes an
    # NGWE row the engine sets at a new game; a script that runs (not hand-written) sets its own, no row
    def test_carried_chargen_weather_is_a_row(self):
        from mwscript.gamedata import new_game_weather
        self.assertEqual(new_game_weather('begin CharGen\nChangeWeather "Bitter Coast Region" 1 ;cloudy\n'
                                          'ChangeWeather, Foo 9\nChangeWeather Bar x\nend'),
                         [('bitter coast region', 1), ('foo', 9)])
        scripts = dict(SCRIPTS, CharGen='begin CharGen\nChangeWeather "Bitter Coast Region" 1\n'
                                         'set CharGenState to 10\nend')
        prog, compiled, data = compiled_program(scripts)
        data.base_regions = {'ascadian isles region', 'bitter coast region'}
        self.assertEqual(awms.new_game_weather_rows(prog, compiled), [(1, 1)])   # sorted: ascadian 0, bitter 1
        prog2, compiled2 = compile_program(data, None, handwritten=(), rooms={})
        self.assertEqual(awms.new_game_weather_rows(prog2, compiled2), [])       # CharGen runs: its own call
        self.assertIn('NGWE', awms.RESIDENT)
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('AW_MwvmSection("NGWE"', host)
        self.assertIn('new_game_weather();', host)


class LaterMasterScriptTests(unittest.TestCase):
    # MWSCRIPT-LATER-MASTER-SCRIPT-61 (v0.0.63): a Morrowind.esm placement whose record a later master gives a script
    # is bound with that script (the blue candle bulbs and Tribunal's fab_attack_disable)
    def test_a_later_masters_script_binds_the_placement(self):
        tmp = Path(tempfile.mkdtemp(prefix='aw-latermaster-'))
        try:
            mw = [record('TES3', sub('HEDR', b'\0' * 300)), record('LIGH', sub('NAME', 'lamp_x')),
                  cell_exterior(1, 2, [(301, 'lamp_x', (0, 0, 0))])]
            tr = [record('TES3', sub('HEDR', b'\0' * 300)), scpt('LampScript', 'begin LampScript\nDisable\nend'),
                  record('LIGH', sub('NAME', 'lamp_x'), sub('SCRI', 'LampScript'))]
            (tmp / 'Morrowind.esm').write_bytes(b''.join(mw))
            (tmp / 'Tribunal.esm').write_bytes(b''.join(tr))
            data = GameData().load(tmp)
            refs = [r for r in data.references if r['reference'] == 301]
            self.assertEqual(len(refs), 1)
            self.assertEqual(refs[0]['script'], 'lampscript')
            self.assertEqual(refs[0]['type'], 'LIGH')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class AddonBindingTests(unittest.TestCase):
    # MWSCRIPT-ADDON-ATTACH-62 (v0.0.63): an add-on's own placement is keyed by its load-order index (2^22 a master),
    # a Morrowind.esm reference an add-on cell repeats (top byte 1: its first MAST) is not bound twice; the add-on
    # placements are bound only for the add-on worlds asked for
    def test_addon_placements_keyed_and_bound_on_request(self):
        from mwscript.gamedata import ADDON_KEY_STRIDE
        from mwscript.compiler import bindings
        tmp = Path(tempfile.mkdtemp(prefix='aw-addonbind-'))
        try:
            mw = [record('TES3', sub('HEDR', b'\0' * 300)), record('LIGH', sub('NAME', 'lamp_x')),
                  cell_exterior(1, 2, [(301, 'lamp_x', (0, 0, 0))])]
            tr = [record('TES3', sub('HEDR', b'\0' * 300), sub('MAST', 'Morrowind.esm'), sub('DATA', b'\0' * 8)),
                  scpt('LampScript', 'begin LampScript\nDisable\nend'),
                  record('LIGH', sub('NAME', 'lamp_x'), sub('SCRI', 'LampScript')),
                  cell_exterior(3, 4, [(77, 'lamp_x', (1, 2, 3)), ((1 << 24) | 301, 'lamp_x', (0, 0, 0)),
                                       ((5 << 24) | 9, 'lamp_x', (0, 0, 0))])]
            (tmp / 'Morrowind.esm').write_bytes(b''.join(mw))
            (tmp / 'Tribunal.esm').write_bytes(b''.join(tr))
            data = GameData().load(tmp)
            self.assertEqual(data.master_lists['Tribunal.esm'], ['Morrowind.esm'])
            self.assertEqual([r['reference'] for r in data.references], [301])
            self.assertEqual([(r['reference'], r['script'], r['master']) for r in data.addon_references],
                             [(ADDON_KEY_STRIDE + 77, 'lampscript', 'Tribunal.esm')])
            self.assertEqual(data.addon_refs_unkeyed, 1)              # top byte 5: no such master
            self.assertLess(3 * ADDON_KEY_STRIDE, 1 << 24)            # exact in the engine's float aw_ref
            self.assertEqual(data.addon_key('Bloodmoon.esm', 12), 2 * ADDON_KEY_STRIDE + 12)
            prog, _ = compile_program(data, None, handwritten=(), rooms={})
            self.assertEqual([r['reference'] for r in bindings(prog)], [301])
            self.assertEqual([r['reference'] for r in bindings(prog, addons=('Tribunal.esm',))],
                             [301, ADDON_KEY_STRIDE + 77])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ReaderTests(unittest.TestCase):
    def test_main_block_only(self):
        # the scripts under CharGenState == 1 at any depth inside it; a StartScript outside the block is not one
        self.assertEqual(new_game_scripts(MAIN), ['startup', 'vampirecheck', 'chargen'])
        self.assertEqual(new_game_scripts('begin Main\nStartScript Startup\nend'), [])
        self.assertEqual(new_game_scripts('begin Main\nif ( CharGenState == 1 )\nStartScript "A b"\nendif\n'
                                          'StartScript C\nend'), ['a b'])

    def test_unconditional_disables(self):
        self.assertEqual(unconditional_disables(STARTUP), ['sleeper_01', 'scaffold_x', 'twice_obj', 'nowhere_obj'])


class BuildCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prog, cls.compiled, cls.data = compiled_program()

    def test_new_game_scripts_and_the_check(self):
        self.assertEqual(self.data.new_game, ['startup', 'vampirecheck', 'chargen'])
        r = newgame.check(self.prog, self.compiled)
        runnable = {s['name']: s['runnable'] for s in r['scripts']}
        self.assertEqual(runnable, {'startup': True, 'vampirecheck': True, 'chargen': False})
        self.assertTrue(self.compiled[self.prog.scripts.index['chargen']].flags & SCRIPT_HANDWRITTEN)
        c = r['counts']
        self.assertEqual((c['disabled'], c['placed_once'], c['resolved'], c['placed_more_than_once'], c['not_placed']),
                         (4, 2, 2, 1, 1))
        rows = {d['id']: d for d in r['disabled']}
        self.assertEqual(rows['sleeper_01']['reference'], 201)
        self.assertNotIn('cond_obj', rows)                         # under an if: not a run-once disable

    def test_the_check_refuses(self):
        # Main without its new-game block: nothing would hold the story characters back
        scripts = dict(SCRIPTS, Main='begin Main\nStartScript Startup\nend')
        prog, compiled, _ = compiled_program(scripts)
        with self.assertRaises(ValueError) as caught:
            newgame.check(prog, compiled)
        self.assertIn('NEWG', str(caught.exception))
        # a reference placed once whose Disable is not bound to it
        prog, compiled, _ = compiled_program()
        row = prog.objects.rows[prog.objects.index['sleeper_01']]
        row['reference'] = 0
        with self.assertRaises(ValueError) as caught:
            newgame.check(prog, compiled)
        self.assertIn('sleeper_01', str(caught.exception))

    def test_the_file_holds_newg(self):
        f = awms.read(awms.write(self.prog, self.compiled, bindings(self.prog))[0])
        self.assertIn('NEWG', awms.RESIDENT)
        rows = [struct.unpack_from('>H', f['NEWG'], 2 * i)[0] for i in range(f['NEWG_rows'])]
        self.assertEqual(rows, [self.prog.scripts.index[n] for n in ('startup', 'vampirecheck', 'chargen')])
        self.assertEqual(f['STRT_rows'], 0)                        # Main's new game scripts are no load-time starts

    def test_fall_compiles_to_nothing(self):
        c = self.compiled[self.prog.scripts.index['fallingtest']]
        ops = [n for _, n, _ in awms.decode(c.code)]
        self.assertFalse(c.flags & SCRIPT_NOTYET, ops)
        self.assertEqual(ops, ['REF', 'DISABLE', 'END'])


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class InterpreterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='aw-newgame-vm-'))
        cls.prog, cls.compiled, _ = compiled_program()
        raw, _ = awms.write(cls.prog, cls.compiled, bindings(cls.prog))
        (cls.tmp / 'test.awm').write_bytes(raw)
        (cls.tmp / 'h.c').write_text(HARNESS, encoding='utf-8')
        src = ROOT / 'engine/aga/src'
        built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-Wno-unused-parameter', '-Wshadow',
                                '-fsanitize=undefined,address', '-fno-sanitize-recover=all', '-I' + str(src),
                                str(cls.tmp / 'h.c'), str(src / 'aw_mwvm.c'), str(src / 'aw_ledger.c'),
                                '-o', str(cls.tmp / 'h')], capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_vm(self, env):
        r = subprocess.run([str(self.tmp / 'h'), str(self.tmp / 'test.awm'), '3', '0.25'], capture_output=True,
                           text=True, env=dict(os.environ, **env))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout.splitlines()

    def disables(self, out):
        return [l.split() for l in out if l.split()[1:2] == ['object'] and l.split()[4] == str(OPCODES['DISABLE'][0])]

    def test_a_new_game_runs_startup_once(self):
        out = self.run_vm({'NEWGAME': '1'})
        self.assertIn('newgame 2', out)                           # Startup and VampireCheck; CharGen is by hand
        targets = {self.prog.objects.index[k] for k in ('sleeper_01', 'scaffold_x', 'twice_obj', 'nowhere_obj')}
        # Startup's four disables, once each (it stops itself), on its own run; the journal's on its own object
        startup = [d for d in self.disables(out) if int(d[3]) in targets and d[3] != str(self.prog.objects.index['scaffold_x'])]
        self.assertEqual(sorted(int(d[3]) for d in startup), sorted(targets - {self.prog.objects.index['scaffold_x']}))
        vamp = self.prog.globals.index['vampcount']
        self.assertIn('global %d 2 ' % vamp, ' '.join(l + ' ' for l in out if l.startswith('global')))

    def test_no_new_game_no_startup(self):
        out = self.run_vm({})
        sleeper = str(self.prog.objects.index['sleeper_01'])
        self.assertFalse([d for d in self.disables(out) if d[3] == sleeper], out)


if __name__ == '__main__':
    unittest.main()
