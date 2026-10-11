# SPDX-License-Identifier: GPL-3.0-only
"""Engine profiles (docs/ENGINE_PROFILES.md, ENGINE-UPSTREAM-ASM-UNUSED-36).

The default is the c profile: AmiWind's C paths at -O1, built with exactly the make command of the
build before engine profiles existed (no extra make variables, no assembly objects). The upstream
profile links upstream AmiQuake's turbulent-span and chunky-to-planar assembly at -O1, as upstream's
Makefile builds; --engine-opt o2 is the separate selective -O2 experiment. The gate's engine step builds both (build_aga.py engine
--check-profiles) and checks that c with its make variables spelled out gives the same binary
SHA-256 as the plain c build; these host tests pin the rest without a cross compiler.
"""
import contextlib
import io
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import engine_profile  # noqa: E402
import project_version  # noqa: E402

ENGINE = ROOT / 'engine' / 'aga'
UPSTREAM_FILES = ('c2p8.s', 'd_scan_68k.s', 'd_scan_68k_nofpu.s', 'fixedpoint_asm.s', 'mathlib_68k.s')


class ProfileRecordTests(unittest.TestCase):
    def test_default_is_c_and_adds_nothing(self):
        record = engine_profile.resolve()
        self.assertEqual(record['label'], 'c')
        self.assertTrue(engine_profile.is_default(record))
        self.assertEqual(engine_profile.make_variables(record), [])
        self.assertEqual(record['asm_objects'], [])
        self.assertEqual(engine_profile.cli_arguments(SimpleNamespace(engine_profile='c', engine_asm=None,
                                                                      engine_opt=None)), [])

    def test_builder_default_is_c(self):
        import build
        with contextlib.redirect_stdout(io.StringIO()):
            args = build.parser().parse_args([])
        self.assertEqual(args.engine_profile, 'c')
        self.assertIsNone(args.engine_asm)
        self.assertIsNone(args.engine_opt)
        self.assertEqual(build.engine_profile_arguments(args), [])

    def test_upstream_profile(self):
        record = engine_profile.resolve('upstream')
        self.assertEqual(record['label'], 'upstream')
        self.assertEqual(record['asm_linked'], ['turb', 'c2p'])
        self.assertEqual(record['asm_objects'], ['c2p8.o', 'd_scan_68k.o'])
        self.assertEqual(record['opt'], 'o1')
        self.assertEqual(engine_profile.make_variables(record), ['ENGINE_ASM=turb c2p fixed', 'ENGINE_OPT=o1'])
        self.assertIn('TerribleFire', record['credit'])
        self.assertIn('Stephen Leary', record['credit'])
        self.assertIn('NovaCoder', record['credit'])
        no_fpu = engine_profile.resolve('upstream', cpu='68020')
        self.assertEqual(no_fpu['asm_objects'], ['c2p8.o', 'd_scan_68k_nofpu.o', 'fixedpoint_asm.o'])

    def test_overrides_and_labels(self):
        self.assertEqual(engine_profile.resolve('c', None, 'o2')['label'], 'custom')
        self.assertEqual(engine_profile.resolve('upstream', 'none', 'o1')['label'], 'c')
        self.assertEqual(engine_profile.resolve('c', 'turb,c2p,fixed', 'upstream')['label'], 'upstream')
        self.assertEqual(engine_profile.resolve('c', 'turb,c2p')['label'], 'upstream')
        self.assertEqual(engine_profile.resolve('upstream', None, 'o2')['label'], 'custom')
        self.assertEqual(engine_profile.parse_opt('upstream'), 'o1')
        self.assertEqual(engine_profile.resolve('c', 'all')['asm'], list(engine_profile.UNITS))
        self.assertIn('spans', engine_profile.resolve('c', 'spans')['notes'])
        for bad in ('vector', 'turb,bogus', ''):
            with self.assertRaises(ValueError):
                engine_profile.resolve('c', bad)
        with self.assertRaises(ValueError):
            engine_profile.resolve('c', None, 'o3')
        with self.assertRaises(ValueError):
            engine_profile.resolve('fast')
        with self.assertRaises(ValueError):
            engine_profile.resolve('c', 'maths', cpu='68020')
        with self.assertRaises(ValueError):
            engine_profile.resolve('c', 'turb', cpu='68020')

    def test_spans_stay_out_of_the_upstream_profile(self):
        # Upstream's D_DrawSpans8 assembly is the sprite span loop (ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36).
        self.assertNotIn('spans', engine_profile.PROFILE_ASM['upstream'])
        self.assertNotIn('maths', engine_profile.PROFILE_ASM['upstream'])

    def test_link_map_check(self):
        c, upstream = engine_profile.resolve('c'), engine_profile.resolve('upstream')
        linked = 'obj/aw_c2p.o\nobj/d_scan_68k.o\nobj/c2p8.o\n'
        self.assertEqual(engine_profile.check_link_map(linked, upstream), [])
        self.assertEqual(len(engine_profile.check_link_map(linked, c)), 2)
        self.assertEqual(len(engine_profile.check_link_map('obj/aw_c2p.o\n', upstream)), 2)


class BootLineTests(unittest.TestCase):
    def test_boot_rows_fit_and_name_the_profile(self):
        for args, word in ((('c',), 'c:'), (('upstream',), 'upstream:'), (('c', 'turb'), 'custom:')):
            line = engine_profile.boot_line(engine_profile.resolve(*args))
            self.assertLessEqual(len(line), 63)
            self.assertIn('Engine profile:', line)
            self.assertIn(word, line)

    def test_generated_default_matches_the_c_profile(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = engine_profile.write_boot_include(tmp, engine_profile.resolve('c'))
            self.assertEqual(path.read_text(encoding='utf-8'), project_version.DEFAULT_ENGINE_INCLUDE)

    def test_boot_check_prints_the_row(self):
        text = (ENGINE / 'boot' / 'bootcheck.asm').read_text(encoding='utf-8')
        self.assertIn('include "amiwind_engine.i"', text)
        self.assertIn('lea     engine_note(pc),a0', text)


class SourceTests(unittest.TestCase):
    def test_upstream_files_carry_their_origin(self):
        for name in UPSTREAM_FILES:
            with self.subTest(name=name):
                text = (ENGINE / 'src' / name).read_text(encoding='utf-8')
                head = text.splitlines()[:3]
                self.assertIn('upstream AmiQuake', head[0])
                self.assertIn('src/' + name, head[0])
                self.assertIn(engine_profile.UPSTREAM_REVISION, head[1])
                self.assertIn('GPL v2', head[1])

    def test_makefile_units_match(self):
        text = (ENGINE / 'Makefile').read_text(encoding='utf-8')
        units = re.search(r'^ENGINE_ASM_UNITS = (.*)$', text, re.M).group(1).split()
        self.assertEqual(tuple(units), engine_profile.UNITS)
        # the C span code stays compiled in every profile
        self.assertIn('-DUSE_ASM_SPANS=0', text)

    def test_docs_and_release_list(self):
        import json
        listed = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        for name in UPSTREAM_FILES:
            self.assertIn('engine/aga/src/' + name, listed)
        for doc in ('docs/ENGINE_PROFILES.md', 'tools/engine_profile.py', 'tests/test_engine_profile.py'):
            self.assertIn(doc, listed)
        licensing = (ROOT / 'docs' / 'LICENSING_AND_CREDITS.md').read_text(encoding='utf-8')
        experimental = (ROOT / 'docs' / 'EXPERIMENTAL_FLAGS.md').read_text(encoding='utf-8')
        for name in UPSTREAM_FILES:
            self.assertIn(name, licensing)
        self.assertIn('--engine-profile upstream', experimental)


def make_commands(*variables):
    """make -n -B fpu in engine/aga: the commands, whitespace-normalised, one per line."""
    result = subprocess.run(['make', '-n', '-B', 'fpu', 'PYTHON=python3', *variables], cwd=ENGINE,
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise AssertionError(result.stdout[-2000:] + result.stderr[-2000:])
    return [' '.join(line.split()) for line in result.stdout.splitlines() if line.strip()]


@unittest.skipUnless(shutil.which('make'), 'GNU make not installed')
class MakefileTests(unittest.TestCase):
    def test_c_profile_commands_are_the_plain_build(self):
        # The make command of a c build gets no variables; spelling them out changes no command.
        self.assertEqual(make_commands(), make_commands('ENGINE_ASM=', 'ENGINE_OPT=o1'))
        plain = '\n'.join(make_commands())
        self.assertNotIn('vasmm68k_mot -Fhunk', plain)
        self.assertNotIn('-O2', plain)
        self.assertNotIn('AW_ASM_', plain)

    def test_upstream_profile_commands(self):
        record = engine_profile.resolve('upstream')
        commands = make_commands(*engine_profile.make_variables(record))
        def compile_of(name):
            return next(line for line in commands if line.endswith('src/' + name))
        self.assertIn(' -O1 ', compile_of('d_scan.c'))
        self.assertFalse([line for line in commands if ' -O2 ' in line])
        self.assertIn(' -O0 ', compile_of('d_sprite.c'))
        self.assertIn('-DAW_ASM_TURB=1', compile_of('d_scan.c'))
        self.assertIn('-DAW_ASM_C2P=1', compile_of('aw_c2p.c'))
        self.assertNotIn('-DAW_ASM_SPANS', compile_of('d_scan.c'))
        assembled = [line for line in commands if line.startswith('vasmm68k_mot ')]
        self.assertEqual(sorted(Path(line.split()[-1]).name for line in assembled), ['c2p8.s', 'd_scan_68k.s'])
        link = next(line for line in commands if ' -o build/AmiQuakeGCC ' in line)
        self.assertIn('obj/d_scan_68k.o', link)
        self.assertIn('obj/c2p8.o', link)
        self.assertNotIn('fixedpoint_asm.o', link)

    def test_o2_experiment_commands(self):
        commands = make_commands(*engine_profile.make_variables(engine_profile.resolve('c', None, 'o2')))
        def compile_of(name):
            return next(line for line in commands if line.endswith('src/' + name))
        self.assertIn(' -O2 ', compile_of('d_scan.c'))
        self.assertIn(' -O2 ', compile_of('chim/chim_world.c'))
        self.assertIn(' -O1 ', compile_of('mathlib.c'))
        self.assertIn(' -O1 ', compile_of('in_amiga.c'))
        self.assertIn(' -O0 ', compile_of('d_sprite.c'))
        self.assertFalse([line for line in commands if line.startswith('vasmm68k_mot ')])

    def test_unknown_units_are_refused(self):
        result = subprocess.run(['make', '-n', '-B', 'fpu', 'PYTHON=python3', 'ENGINE_ASM=vector'], cwd=ENGINE,
                                capture_output=True, text=True, timeout=120)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ENGINE_ASM', result.stderr)


if __name__ == '__main__':
    unittest.main()
