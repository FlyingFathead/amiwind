"""The builder's 68040-unimplemented FPU check (ENGINE-FPU-UNIMPL-31) on synthetic
objdump -d -r output and linker maps: classification, call graph, allowlist."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_fpu_unimplemented as check  # noqa: E402

MAP = '''Linker script and memory map

 .text          0x00000000      0x100 obj/r_bsp.o
                0x00000000                R_RotateBmodel
                0x00000040                R_Other
 .text          0x00000100       0x80 obj/aw_profile.o
                0x00000100                AW_Print
 .text          0x00000180       0x40 /sdk/lib/libm.a(lib_a-cexp.o)
                0x00000180                cexp
 .text          0x000001c0       0x40 /sdk/lib/libc.a(lib_a-svfprintf.o)
                0x000001c0                _svfprintf_r
 .data          0x00000000       0x10 obj/r_bsp.o
'''


def dis(*lines):
    return '\n'.join(lines) + '\n'


class ClassificationTests(unittest.TestCase):
    def test_full_68040_unimplemented_list_and_packed_operands(self):
        for name in ('fint', 'fintrz', 'fmovecr', 'fsincos', 'fsin', 'fcos', 'ftan', 'fatan', 'fasin',
                     'facos', 'fetox', 'fetoxm1', 'ftwotox', 'ftentox', 'flogn', 'flognp1', 'flog10',
                     'flog2', 'fsinh', 'fcosh', 'ftanh', 'fatanh', 'fgetexp', 'fgetman', 'fmod',
                     'frem', 'fscale'):
            for spelling in (name, name + 'x', name + 'd', name + 's'):
                self.assertTrue(check.unimplemented(spelling), spelling)
        for packed in ('fmovep', 'faddp', 'fmulp'):
            self.assertTrue(check.unimplemented(packed), packed)

    def test_implemented_instructions_pass(self):
        for name in ('fmovex', 'fmoves', 'fmoved', 'fmovel', 'fmovemx', 'fmoveml', 'faddx', 'fsadds',
                     'fdmuld', 'fdivx', 'fsqrtx', 'fssqrts', 'fabsx', 'fnegx', 'fcmpx', 'ftstx',
                     'fbeq', 'fbolt', 'fsave', 'frestore', 'fnop', 'movel', 'jsr', 'fsglmulx'):
            self.assertFalse(check.unimplemented(name), name)


class GraphTests(unittest.TestCase):
    def run_check(self, disassembly, allowed=()):
        return check.check(disassembly, MAP, {'allowed': list(allowed)})

    def test_engine_call_into_trapping_library_fails_with_path(self):
        result = self.run_check(dis(
            '   10:\t4eb9 0000 0180 \tjsr 0x180',
            '\t\t\t12: RELOC32\t.text',
            '  184:\tf200 5c0f      \tfmovecrx #15,%fp1'))
        self.assertFalse(result['passed'])
        row = [r for r in result['engine_failures'] if r['function'] == 'R_RotateBmodel'][0]
        self.assertEqual(row['path'], ['R_RotateBmodel', 'cexp'])
        self.assertEqual(result['unimplemented_instructions'], 1)

    def test_register_loaded_and_pc_relative_references_count(self):
        for line in ('   44:\t47f9 0000 0180 \tlea 0x180,a3', '   44:\t4eba 0140      \tjsr %pc@(0x180)'):
            lines = [line]
            if 'lea' in line:
                lines.append('\t\t\t46: RELOC32\t.text')
            result = self.run_check(dis(*lines, '  190:\tf200 0003      \tfintrzx %fp0,%fp0'))
            self.assertIn('R_Other', [r['function'] for r in result['engine_failures']], line)

    def test_data_addresses_are_not_code_references(self):
        result = self.run_check(dis(
            '   10:\t2039 0000 0180 \tmovel 0x180,d0',
            '\t\t\t12: RELOC32\t.bss',
            '   20:\t2f3c 0000 0180 \tmovel #0x180,sp@-',
            '  184:\tf200 5c0f      \tfmovecrx #15,%fp1'))
        self.assertTrue(result['passed'], result['engine_failures'])

    def test_allowlist_cuts_named_callers_only(self):
        lines = ('   10:\t4eb9 0000 01c0 \tjsr 0x1c0', '\t\t\t12: RELOC32\t.text',
                 '  104:\t4eb9 0000 01c0 \tjsr 0x1c0', '\t\t\t106: RELOC32\t.text',
                 '  1c4:\tf200 0003      \tfintrzx %fp0,%fp1')
        everyone = self.run_check(dis(*lines), [{'function': '_svfprintf_r', 'callers': '*', 'why': 't'}])
        self.assertTrue(everyone['passed'])
        one = self.run_check(dis(*lines), [{'function': '_svfprintf_r', 'callers': ['AW_Print'], 'why': 't'}])
        self.assertEqual([r['function'] for r in one['engine_failures']], ['R_RotateBmodel'])
        unused = self.run_check(dis('  1c4:\tf200 0003      \tfintrzx %fp0,%fp1'),
                                [{'function': 'cexp', 'callers': '*', 'why': 't'}])
        self.assertEqual(unused['allowlist_unused'], ['cexp'])

    def test_unimplemented_instruction_in_engine_object_fails(self):
        result = self.run_check(dis('  108:\tf200 0001      \tfintx %fp0,%fp0'))
        self.assertEqual([r['function'] for r in result['engine_failures']], ['AW_Print'])

    def test_pointer_table_in_text_is_not_an_instruction(self):
        # ENGINE-FPU-DATA-DECODE-33: a constant table of .text pointers (0x0003f2xx) decodes as
        # fintrz; the opcode lies inside a relocated longword, so it is data, not code.
        table = dis(
            '   44:\t0000 0003      \torib #3,%d0',
            '\t\t\t46: RELOC32\t.text',
            '   48:\tf202 0003      \tfintrzx %fp0,%fp0',
            '\t\t\t4a: RELOC32\t.text',
            '   4c:\tf210 0003      \tfintrzx %fp0,%fp0')
        result = self.run_check(table)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['unimplemented_instructions'], 0)
        # A real instruction keeps failing, even right after a relocated operand.
        real = dis(
            '   44:\t4eb9 0000 0040 \tjsr 0x40',
            '\t\t\t46: RELOC32\t.text',
            '   4a:\tf203 0003      \tfintrzx %fp0,%fp0')
        result = self.run_check(real)
        self.assertFalse(result['passed'])
        self.assertEqual(result['unimplemented_instructions'], 1)


class RepositoryTests(unittest.TestCase):
    def test_allowlist_is_justified_line_by_line(self):
        data = json.loads(check.ALLOWLIST.read_text(encoding='utf-8'))
        names = [row['function'] for row in data['allowed']]
        self.assertEqual(len(names), len(set(names)))
        for row in data['allowed']:
            self.assertEqual(set(row), {'function', 'callers', 'why'})
            self.assertTrue(row['callers'] == '*' or (isinstance(row['callers'], list) and row['callers']))
            self.assertGreater(len(row['why']), 30, row['function'])
        for banned in ('sin', 'cos', 'cexp', 'atan', 'atan2', 'tan', 'exp', '__kernel_sin', '__kernel_cos'):
            self.assertNotIn(banned, names, 'trigonometry must stay unlinked, not allowlisted')
        for banned in ('pow', '__ieee754_pow'):
            # ENGINE-GAMMA-POW-35: the gamma table uses Q_GammaPow (mathlib.c).
            self.assertNotIn(banned, names, 'pow must stay unlinked, not allowlisted')
        for banned in ('_strtod_l', '_dtoa_r', '_svfprintf_r', '_vfprintf_r', '__fixdfdi', '__fixunsdfdi'):
            self.assertNotIn(banned, names, 'C library float parsing/printing must stay unlinked (aw_format.c)')

    def test_engine_uses_its_own_text_number_conversion(self):
        # ENGINE-FPSP-MISSING-31: the C library's atof/strtod/scanf and printf
        # float code execute FINTRZ; the engine parses with Q_atof/Q_strtod/
        # Q_sscanf/Q_fscanf and links the printf family to Q_vsnprintf.
        import re
        call = re.compile(r'(?<![\w.])(atof|strtod|strtof|sscanf|fscanf|vsscanf|vfscanf|scanf)\s*\(')
        bad = []
        for p in sorted((ROOT / 'engine/aga/src').glob('*.c')):
            if p.name == 'aw_format.c':
                continue
            for n, line in enumerate(p.read_text(encoding='latin-1').splitlines(), 1):
                code = line.split('//')[0]
                if call.search(code) and not code.lstrip().startswith(('*', '/*')):
                    bad.append(f'{p.name}:{n}: {line.strip()}')
        self.assertEqual(bad, [])
        makefile = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        wraps = set(re.findall(r'-Wl,--wrap=(\w+)', makefile))
        self.assertTrue({'sprintf', 'snprintf', 'vsprintf', 'vsnprintf',
                         'fprintf', 'vfprintf', 'printf', 'vprintf'} <= wraps, wraps)
        self.assertIn('$(FORMAT_WRAPS)', makefile)

    def test_no_star_field_widths_in_engine_format_strings(self):
        # The Amiga C library prints "%0*ld" literally (REMOTE-STATE-WIDTH-31).
        import re
        star = re.compile(r'"[^"]*%[-+ #0]*\*[^"]*"')
        bad = [f'{p.name}:{n}' for p in sorted((ROOT / 'engine/aga/src').glob('*.c'))
               for n, line in enumerate(p.read_text(encoding='latin-1').splitlines(), 1)
               if 'printf' in line and star.search(line)]
        self.assertEqual(bad, [])

    def test_engine_build_runs_the_check_and_links_a_map(self):
        builder = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('check_fpu_unimplemented.check(', builder)
        self.assertIn("'-d','-r','-m','m68k:68040'", builder)
        makefile = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('-Wl,-Map,build/AmiQuakeGCC.map', makefile)
        self.assertIn('-fno-builtin-sin -fno-builtin-cos', makefile)


if __name__ == '__main__':
    unittest.main()
