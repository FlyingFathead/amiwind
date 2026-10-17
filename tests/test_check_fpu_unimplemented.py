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


class Cpu68060Tests(unittest.TestCase):
    """--cpu 68060 (docs/68060.md, ENGINE-060-FSCC-41): the 68060's unimplemented set, in the objdump
    spelling of this SDK (registers without %)."""

    def kind(self, mnemonic, operands=''):
        return check.trap_kind(mnemonic, operands, '68060')

    def test_fpu_conditionals_trap(self):
        for m in ('fsgt', 'fsne', 'fseq', 'fslt', 'fsugt', 'fsngle', 'fsst', 'fssf', 'fsogl'):
            self.assertEqual(self.kind(m, 'd0'), 'fscc', m)
        self.assertEqual(self.kind('fdbne', 'd1,0x40'), 'fdbcc')
        for m in ('ftrapne', 'ftrapnew', 'ftrapeql'):
            self.assertEqual(self.kind(m, '#1'), 'ftrapcc', m)
        # arithmetic with an s (single) prefix, and other fs... mnemonics, are not FScc
        for m, ops in (('fsnegx', '%fp0,%fp1'), ('fsaddx', '%fp1,%fp0'), ('fsglmulx', '%fp1,%fp0'),
                       ('fsgldivx', '%fp1,%fp0'), ('fsqrtx', '%fp0'), ('fsubx', '%fp1,%fp0'), ('fsave', 'sp@-'),
                       ('fsmoves', 'd0,%fp0'), ('fsabsx', '%fp0')):
            self.assertIsNone(self.kind(m, ops), m)

    def test_fint_runs_on_the_68060_only(self):
        self.assertIsNone(self.kind('fintrzx', '%fp0,%fp1'))
        self.assertIsNone(self.kind('fintx', '%fp0,%fp1'))
        self.assertEqual(check.trap_kind('fintrzx', '%fp0,%fp1', '68040'), 'fpu')
        for m in ('fsinx', 'fmovecrx', 'fetoxx', 'fmodx', 'fgetexpx', 'fscalex'):
            self.assertEqual(self.kind(m, '%fp0,%fp1'), 'fpu', m)
        self.assertEqual(self.kind('fmovep', '%fp0,a0@'), 'fpu')

    def test_effective_address_forms(self):
        self.assertEqual(self.kind('fmovemx', 'a0@,d1'), 'fmovem-dynamic')
        self.assertEqual(self.kind('fmovemx', '%d0,%a0@'), 'fmovem-dynamic')
        self.assertIsNone(self.kind('fmovemx', '%fp0-%fp2,sp@-'))
        self.assertIsNone(self.kind('fmovemx', 'sp@+,%fp2'))
        self.assertEqual(self.kind('fmoveml', '#0,fpsr/fpcr'), 'fmovem-control-immediate')
        self.assertIsNone(self.kind('fmovel', '#0,fpcr'))
        self.assertEqual(self.kind('fmovex', '#0x3fff0000800000000000,%fp0'), 'fpu-immediate')
        self.assertIsNone(self.kind('fmoves', '#0x3f800000,%fp0'))
        self.assertIsNone(self.kind('fmoved', '#0x3ff0000000000000,%fp0'))

    def test_integer_instructions(self):
        self.assertEqual(self.kind('mulsl', 'd1,d2,d0'), 'mul64')
        self.assertEqual(self.kind('mulul', '#-858993459,d0,d1'), 'mul64')
        self.assertIsNone(self.kind('mulsl', 'd1,d0'))
        # commas inside an indexed operand are not operand separators
        self.assertIsNone(self.kind('mulsl', 'a0@(0,d0:l:4),d1'))
        self.assertEqual(self.kind('divsl', 'd1,d2,d0'), 'div64')
        self.assertEqual(self.kind('divul', 'd3,d1,d0'), 'div64')
        self.assertIsNone(self.kind('divsll', 'd1,d2,d0'))
        self.assertIsNone(self.kind('divull', 'd1,d0,d0'))
        for m, kind in (('movepw', 'movep'), ('movepl', 'movep'), ('chk2l', 'chk2'), ('cmp2b', 'cmp2'),
                        ('cas2w', 'cas2')):
            self.assertEqual(self.kind(m, 'd0,a0@(2)'), kind, m)
        self.assertIsNone(check.trap_kind('mulsl', 'd1,d2,d0', '68040'))
        self.assertIsNone(self.kind('movel', 'd0,d1'))

    def test_operands_split_at_top_level(self):
        self.assertEqual(check.operands_of('a0@(0,d0:l:4),d1'), ['a0@(0,d0:l:4)', 'd1'])
        self.assertEqual(check.operands_of(' d1,d2,d0 '), ['d1', 'd2', 'd0'])
        self.assertEqual(check.operands_of(''), [])

    def test_check_reports_kinds_per_function_and_fails_on_engine_traps(self):
        disassembly = dis(
            '   10:\tf240 0012      \tfsgt d0',
            '   14:\t4c01 0c02      \tmulsl d1,d2,d0',
            '   18:\t0d0a 0073      \tmovepw a2@(115),d6',
            '  108:\tf200 0083      \tfintrzx %fp0,%fp1')
        result = check.check(disassembly, MAP, {'allowed': []}, '68060')
        self.assertFalse(result['passed'])
        self.assertEqual(result['cpu'], '68060')
        self.assertEqual(result['trap_kinds'], {'fscc': 1, 'movep': 1, 'mul64': 1})
        row = result['functions_by_kind']['R_RotateBmodel']
        self.assertEqual(row['kinds'], {'fscc': 1, 'movep': 1, 'mul64': 1})
        self.assertTrue(row['engine'])
        self.assertEqual(result['unimplemented_instructions'], 2)   # movep: decoded data, not counted
        self.assertEqual([r['function'] for r in result['engine_failures']], ['R_RotateBmodel'])
        # the same binary in 68040 mode: FINTRZ fails, the rest runs in hardware
        result = check.check(disassembly, MAP, {'allowed': []})
        self.assertEqual([r['function'] for r in result['engine_failures']], ['AW_Print'])
        self.assertNotIn('trap_kinds', result)

    def test_decoded_data_alone_passes(self):
        result = check.check(dis('   18:\t0d0a 0073      \tmovepw a2@(115),d6'), MAP, {'allowed': []}, '68060')
        self.assertTrue(result['passed'])
        self.assertEqual(result['trap_kinds'], {'movep': 1})

    def test_68060_allowlist_is_justified(self):
        self.assertEqual(check.allowlist_path('68060').name, 'fpu-unimplemented-allowlist-68060.json')
        self.assertEqual(check.allowlist_path('68040'), check.ALLOWLIST)
        data = json.loads(check.ALLOWLIST_68060.read_text(encoding='utf-8'))
        names = [row['function'] for row in data['allowed']]
        self.assertEqual(len(names), len(set(names)))
        for row in data['allowed']:
            self.assertEqual(set(row), {'function', 'callers', 'why'})
            self.assertGreater(len(row['why']), 30, row['function'])
        # engine code itself is never allowlisted: only C library and libgcc functions
        for name in names:
            self.assertFalse(name[:1].isupper() or name.startswith(('AW_', 'R_', 'D_', 'CHIM_')), name)
        self.assertNotIn('cexp', names)


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
