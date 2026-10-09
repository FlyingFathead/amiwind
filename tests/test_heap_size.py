# SPDX-License-Identifier: GPL-3.0-only
"""The game heap size (--heap-mb N, build config heap_mb, start argument -heapmb N): used exactly as
asked, like --jobs; above the size measured to run the whole game on 16 MiB Fast RAM, one warning in the
build output, the engine receipt, the boot check and the engine's start, and never a refusal. The heap
gates measure against the build's own size."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import project_version
from project_version import BOOT_COLUMNS, generate_heap, generate_native, heap_defaults, heap_plan


def find_sdk():
    for candidate in (os.environ.get('AMIWIND_SDK'), '/opt/amiwind-tools/sdk'):
        if candidate and (Path(candidate) / 'bin/vasmm68k_mot').is_file():
            return Path(candidate)
    return None


def boot_strings(include):
    return re.findall(r'dc\.b\s+"([^"]*)"', Path(include).read_text(encoding='utf-8'))


class HeapPlanTests(unittest.TestCase):
    def test_defaults_come_from_the_engine_source(self):
        text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        default, safe = heap_defaults()
        self.assertIn('#define AMIWIND_HEAP_MB %d\n' % default, text)
        self.assertIn('#define AMIWIND_HEAP_SAFE_MB %d\n' % safe, text)
        self.assertEqual(default, 11)
        plan = heap_plan()
        self.assertEqual((plan['heap_mb'], plan['fast_free_mb'], plan['fast_board_mb']), (11, 14, 16))
        self.assertIsNone(plan['heap_warning'])

    def test_any_size_is_used_as_asked_and_above_safe_warns(self):
        _, safe = heap_defaults()
        for mb in (1, 8, safe, safe + 1, 12, 13, 100, 2047):
            plan = heap_plan(mb)
            self.assertEqual(plan['heap_mb'], mb)
            if mb > safe:
                self.assertIn(f'Game heap {mb} MiB is above the {safe} MiB', plan['heap_warning'])
                self.assertIn('built as asked', plan['heap_warning'])
            else:
                self.assertIsNone(plan['heap_warning'])
        self.assertEqual(heap_plan(13)['fast_board_mb'], 32)

    def test_only_sizes_the_engine_cannot_hold_are_errors(self):
        # Not a policy: memsize is a signed 32-bit byte count.
        for value in (0, -1, 2048):
            with self.assertRaisesRegex(ValueError, 'from 1 to 2047'):
                heap_plan(value)


class GeneratedHeapFileTests(unittest.TestCase):
    def test_default_keeps_the_boot_text_and_prints_no_heap_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_native(ROOT / 'VERSION', tmp)
            header = (Path(tmp) / 'amiwind_heap.h').read_text()
            self.assertIn('#define AMIWIND_HEAP_MB 11\n', header)
            include = (Path(tmp) / 'amiwind_heap.i').read_text()
            self.assertIn('AW_HEAP_BYTES equ 11*1048576', include)
            self.assertIn('AW_FAST_FREE_BYTES equ 14*1048576', include)
            self.assertIn('"FAIL: select 16 MB Fast RAM or more."', include)
            self.assertIn('"      Need 14 MiB free; 11 MiB + 16 bytes must be contiguous."', include)
            self.assertIn('heap_note:      dc.b 0\n', include)
            self.assertNotIn('WARN', include)

    def test_a_larger_heap_changes_the_figures_and_warns_in_one_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_native(ROOT / 'VERSION', tmp, 12)
            self.assertIn('#define AMIWIND_HEAP_MB 12\n', (Path(tmp) / 'amiwind_heap.h').read_text())
            include = (Path(tmp) / 'amiwind_heap.i').read_text()
            self.assertIn('AW_HEAP_BYTES equ 12*1048576', include)
            self.assertIn('AW_FAST_FREE_BYTES equ 15*1048576', include)
            self.assertRegex(include, r'heap_note:\s+dc\.b "Game heap: +12 MiB, above 11 MiB tested +\[!\] WARN",10,0')

    def test_every_generated_boot_line_fits_one_console_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mb in (1, 9, 11, 12, 99, 100, 999, 2047):
                generate_heap(tmp, mb)
                for line in boot_strings(Path(tmp) / 'amiwind_heap.i'):
                    with self.subTest(mb=mb, line=line):
                        self.assertLessEqual(len(line), BOOT_COLUMNS)

    def test_an_unchanged_size_keeps_the_files_untouched(self):
        # make rebuilds only what a new heap size changes.
        with tempfile.TemporaryDirectory() as tmp:
            generate_heap(tmp, 12)
            header = Path(tmp) / 'amiwind_heap.h'
            os.utime(header, (1000000, 1000000))
            generate_heap(tmp, 12)
            self.assertEqual(header.stat().st_mtime, 1000000)
            generate_heap(tmp, 13)
            self.assertNotEqual(header.stat().st_mtime, 1000000)

    def test_the_makefile_passes_the_size_and_tracks_it(self):
        text = (ROOT / 'engine/aga/Makefile').read_text()
        self.assertIn('HEAP_MB ?=', text)
        self.assertEqual(text.count('$(if $(HEAP_MB),--heap-mb $(HEAP_MB))'), 2)
        self.assertIn('$(OBJDIR)/sys_amiga.o: build/version/amiwind_heap.h', text)
        boot = (ROOT / 'engine/aga/boot/bootcheck.asm').read_text()
        self.assertIn('include "amiwind_heap.i"', boot)
        self.assertIn('cmp.l   #AW_FAST_FREE_BYTES,16(a0)', boot)
        self.assertIn('cmp.l   #AW_HEAP_BYTES+16,20(a0)', boot)
        self.assertNotRegex(boot, r'#1[0-9]\*1024\*1024')

    @unittest.skipUnless(find_sdk(), 'Amiga SDK (vasm) required')
    def test_the_boot_check_assembles_with_the_warning_and_without(self):
        sdk = find_sdk()
        vasm = str(sdk / 'bin/vasmm68k_mot')
        ndk = str(sdk / 'm68k-amigaos/ndk-include')
        boot = ROOT / 'engine/aga/boot'
        with tempfile.TemporaryDirectory() as tmp:
            outputs = {}
            for mb in (11, 12):
                gen = Path(tmp) / f'gen{mb}'
                generate_native(ROOT / 'VERSION', gen, mb)
                target = Path(tmp) / f'check{mb}'
                result = subprocess.run([vasm, '-m68000', '-Fhunkexe', '-kick1hunks', '-nosym', '-I', ndk, '-I', str(boot),
                                         '-I', str(gen), '-o', str(target), str(boot / 'bootcheck.asm')],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('warning', (result.stdout + result.stderr).lower())
                outputs[mb] = target.read_bytes()
            self.assertNotIn(b'Game heap', outputs[11])
            self.assertIn(b'Game heap:            12 MiB, above 11 MiB tested', outputs[12])
            self.assertIn(b'Need 15 MiB free; 12 MiB', outputs[12])
            self.assertIn(b'Need 14 MiB free; 11 MiB', outputs[11])
            # The Fast RAM comparisons carry the build's own figures (68000 cmp.l #imm,d16(a0)).
            self.assertIn((14 * 1048576).to_bytes(4, 'big'), outputs[11])
            self.assertIn((11 * 1048576 + 16).to_bytes(4, 'big'), outputs[11])
            self.assertIn((15 * 1048576).to_bytes(4, 'big'), outputs[12])
            self.assertIn((12 * 1048576 + 16).to_bytes(4, 'big'), outputs[12])


@unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
class StartArgumentTests(unittest.TestCase):
    """-heapmb N at start (sys_amiga.c Sys_HeapArgument), compiled on the host from the engine's own text."""

    def run_parser(self, *args):
        text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        body = re.search(r'static int Sys_HeapArgument\(int argc, char \*\*argv\) \{.*?\n\}\n', text, re.S).group(0)
        harness = ('#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n'
                   'static void PutStr(const char *s){fputs(s,stdout);}\n' + body +
                   'int main(int argc,char **argv){printf("heap %d\\n",Sys_HeapArgument(argc,argv));return 0;}\n')
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'heaparg.c'
            source.write_text(harness)
            binary = Path(tmp) / 'heaparg'
            subprocess.run(['cc', '-std=c99', '-Wall', '-Werror', '-o', str(binary), str(source)], check=True)
            return subprocess.run([str(binary), *args], capture_output=True, text=True, check=True).stdout

    def test_the_start_argument_is_used_as_asked(self):
        self.assertIn('heap 0', self.run_parser())
        self.assertIn('heap 12', self.run_parser('-heapmb', '12'))
        self.assertIn('heap 64', self.run_parser('+map', 'prison', '-heapmb', '64'))
        self.assertIn('heap 2047', self.run_parser('-heapmb', '2047'))

    def test_a_bad_start_argument_falls_back_to_the_built_size(self):
        for value in ('0', '2048', '12x', 'big', '99999999999'):
            out = self.run_parser('-heapmb', value)
            self.assertIn('heap 0', out)
            self.assertIn('-heapmb takes a whole number', out)

    def test_the_engine_warns_above_the_safe_size_and_starts(self):
        text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        self.assertIn('#include "amiwind_heap.h"', text)
        self.assertIn('if (heap_mb > AMIWIND_HEAP_SAFE_MB)', text)
        self.assertIn('starting as asked', text)
        self.assertIn('Sys_Init(Sys_HeapArgument(argc, argv));', text)
        self.assertNotIn('cannot allocate the 11 MiB', text)


class BuilderHeapOptionTests(unittest.TestCase):
    def test_cli_beats_the_build_config_beats_the_engine_default(self):
        import build
        from build_font_options import resolve_heap
        args = build.parser().parse_args([])
        plan = resolve_heap(args)
        self.assertEqual((plan['heap_mb'], plan['selected_by'], plan['heap_warning']), (11, 'engine default', None))
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'build.json'
            config.write_text(json.dumps({'heap_mb': 12}))
            args = build.parser().parse_args(['--build-config', str(config)])
            plan = resolve_heap(args)
            self.assertEqual((plan['heap_mb'], plan['selected_by']), (12, 'build config'))
            self.assertIn('above the 11 MiB', plan['heap_warning'])
            args = build.parser().parse_args(['--build-config', str(config), '--heap-mb', '10'])
            plan = resolve_heap(args)
            self.assertEqual((plan['heap_mb'], plan['selected_by'], plan['heap_warning']), (10, 'CLI override', None))
            config.write_text(json.dumps({'heap_mb': '12'}))
            with self.assertRaisesRegex(ValueError, 'Invalid heap_mb'):
                resolve_heap(build.parser().parse_args(['--build-config', str(config)]))

    def test_only_an_asked_heap_changes_the_engine_command(self):
        import build
        tools = {name: '/tools/' + name for name in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        for extra, expected in (([], None), (['--heap-mb', '12'], '12'), (['--heap-mb', '11'], '11')):
            args = build.parser().parse_args(['--hands', 'sprites', *extra])
            args.data_files, args.sdk, args.upstream_archive = Path('/d'), Path('/sdk'), Path('/u.tar.gz')
            engine = dict(build.commands(args, tools, Path('/private/run')))['engine']
            if expected is None:
                self.assertNotIn('--heap-mb', engine)
            else:
                self.assertEqual(engine[engine.index('--heap-mb') + 1], expected)

    def test_the_engine_build_passes_the_size_and_records_it(self):
        import build_aga
        calls = []

        def fake_run(command, cwd=None, env=None, capture=False):
            command = [str(c) for c in command]
            calls.append(command)
            tree = Path(cwd) if cwd else None
            if command[0] == 'make' and 'bench' in command:
                (tree / 'build').mkdir(exist_ok=True); (tree / 'build/awbench').write_bytes(b'bench')
            elif command[0] == 'make':
                (tree / 'build').mkdir(exist_ok=True); (tree / 'build/AmiQuakeGCC').write_bytes(b'engine')
            elif '-o' in command:
                Path(command[command.index('-o') + 1]).write_bytes(b'hunk')
            return ''
        for asked in (None, 12):
            calls.clear()
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'engine'
                argv = ['build_aga.py', 'engine', '--out', str(out), '--sdk', tmp, '--jobs', '1',
                        *(['--heap-mb', str(asked)] if asked else [])]
                with patch('sys.argv', argv), patch.object(build_aga, 'run', side_effect=fake_run), \
                        patch.object(build_aga, 'check_binary'), \
                        patch.object(build_aga, 'check_engine_fpu', return_value=None), \
                        patch.object(build_aga, 'executable_path', side_effect=lambda p: p), \
                        patch.object(build_aga, 'write_world_coverage'), \
                        patch('sys.stdout'):
                    build_aga.main()
                make = calls[0]
                record = json.loads((out / 'engine-build.json').read_text())
                if asked is None:
                    self.assertFalse([part for part in make if part.startswith('HEAP_MB=')])
                    self.assertEqual((record['heap_mb'], record['heap_mb_selected_by']), (11, 'engine default'))
                    self.assertIsNone(record['heap_warning'])
                else:
                    self.assertIn('HEAP_MB=12', make)
                    self.assertEqual((record['heap_mb'], record['heap_mb_selected_by']), (12, '--heap-mb'))
                    self.assertIn('above the 11 MiB', record['heap_warning'])
                self.assertEqual(record['heap_safe_mb'], 11)


class HeapGateTests(unittest.TestCase):
    def test_the_map_gate_uses_the_build_size(self):
        from check_world_map_heap import heap_capacity
        self.assertEqual(heap_capacity()[0], 11 * 1048576)
        budget, source = heap_capacity(12)
        self.assertEqual((budget, source['heap_megabytes'], source['selected_by']),
                         (12 * 1048576, 12, 'engine build receipt'))

    def test_the_image_gate_reads_the_engine_receipt(self):
        import build_aga
        seen = {}

        def fake_audit(maps, sdk, out, jobs=1, heap_mb=None):
            seen['heap_mb'] = heap_mb
            return {'heap_budget_bytes': (heap_mb or 11) * 1048576}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(build_aga, 'verify_heap_loader_source_receipt', return_value={}), \
                    patch('check_world_map_heap.audit_world_maps', side_effect=fake_audit):
                report = build_aga.audit_world_map_heap_with_receipt({'heap_mb': 12}, tmp, tmp, Path(tmp) / 'h.json')
                self.assertEqual((seen['heap_mb'], report['heap_budget_bytes']), (12, 12 * 1048576))
                build_aga.audit_world_map_heap_with_receipt({}, tmp, tmp, Path(tmp) / 'h.json')
                self.assertIsNone(seen['heap_mb'])

    def test_the_chim_memory_figures_follow_the_build_size(self):
        import engine_limits
        from chim.heap import engine_memory
        self.assertEqual(engine_memory()['hunk_bytes'], 11 * 1048576)
        self.assertEqual(engine_memory(12)['hunk_bytes'], 12 * 1048576)
        self.assertEqual(engine_limits.chim_memory()['heap_safe_mb'], heap_defaults()[1])


if __name__ == '__main__':
    unittest.main()
