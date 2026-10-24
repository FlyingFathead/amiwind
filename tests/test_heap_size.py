# SPDX-License-Identifier: GPL-3.0-only
"""The game heap size (--heap-mb N, build config heap_mb, start argument -heapmb N): used exactly as
asked, like --jobs; above the size tested on the 16 MiB Fast RAM baseline, one warning in the
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
            self.assertIn('"FAIL: select 32 MB Fast RAM (16 MB is the least that starts)."', include)
            self.assertIn('"      Need 14 MiB free; 11 MiB + 16 bytes must be contiguous."', include)
            self.assertIn('heap_note:      dc.b 0\n', include)
            self.assertNotIn('Game heap', include)

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
            # The safe Fast RAM minimum (RAM-REQUIREMENT-32MB-48): its KiB threshold, the WARN row and the note.
            self.assertIn((32 * 1024 - 64).to_bytes(4, 'big'), outputs[11])
            self.assertIn(b'Fast RAM:             %2ld MB (32 MB needed)', outputs[11])
            self.assertIn(b'Press ENTER to continue anyway.', outputs[11])
            self.assertIn(b'\rStarting in %ld s... \0', outputs[11])


def run_fast_ram_note(fast_bytes):
    """sys_amiga.c Sys_FastRamNote compiled on the host from the engine's own text with the generated
    amiwind_heap.h, AvailMem answering fast_bytes: (CLI text, startup-screen rows, the size in MB)."""
    text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
    body = re.search(r'static long aw_fast_ram_short_mb;.*?\nstatic void Sys_FastRamNote\(void\) \{.*?\n\}\n', text,
                     re.S).group(0).replace('extern char aw_fast_ram_screen[256];', 'char aw_fast_ram_screen[256];') \
        .replace('extern long aw_fast_ram_found_mb;', 'long aw_fast_ram_found_mb;')   # aw_scene.c's (the room doors)
    harness = ('#include <stdio.h>\n#include <string.h>\n#include <stdlib.h>\n#include "amiwind_heap.h"\n'
               '#define MEMF_FAST 4L\nstatic unsigned long fast_bytes;\n'
               'static unsigned long AvailMem(long flags){return flags==(MEMF_FAST|(1L<<19))?fast_bytes:0;}\n'
               'static void PutStr(const char *s){fputs(s,stdout);}\n' + body +
               'int main(int argc,char **argv){fast_bytes=strtoul(argv[1],0,10);Sys_FastRamNote();'
               'printf("@screen %s\\n@mb %ld\\n",aw_fast_ram_screen,aw_fast_ram_short_mb);return 0;}\n')
    with tempfile.TemporaryDirectory() as tmp:
        generate_heap(tmp)
        source = Path(tmp) / 'note.c'
        source.write_text(harness)
        binary = Path(tmp) / 'note'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Werror', '-I', tmp, '-o', str(binary), str(source)], check=True)
        out = subprocess.run([str(binary), str(fast_bytes)], capture_output=True, text=True, check=True).stdout
    cli, rest = out.split('@screen ', 1)
    screen, mb = rest.rsplit('\n@mb ', 1)
    return cli, screen, int(mb)


class BootWaitRun:
    """Runs a routine of engine/aga/boot/boot_wait.asm on the host, one source line at a time, for the few
    instructions it uses (no 68k emulator in the gate image). The library calls are stubs: keys holds, per
    WaitForChar call, the key typed in that second (None: the second passes). puts records each printed string,
    RawDoFmt fills %ld/%2ld. Fails on any instruction it does not know, so the routine cannot drift past it."""
    BOOT = ROOT / 'engine/aga/boot'

    def __init__(self, routine, keys, console=True, found_mb=16):
        with tempfile.TemporaryDirectory() as tmp:
            generate_heap(tmp)
            include = (Path(tmp) / 'amiwind_heap.i').read_text(encoding='utf-8')
        boot = (self.BOOT / 'bootcheck.asm').read_text(encoding='utf-8')
        self.strings = {}
        for text in (include, boot):
            for name, body in re.findall(r'^(\w+):\s*((?:dc\.b[^\n]*\n?(?:\s+dc\.b[^\n]*\n?)*))', text, re.M):
                self.strings[name] = ''.join(self._dcb(line) for line in re.findall(r'dc\.b\s+([^\n]*)', body))
        self.equ = {k: int(v) for k, v in re.findall(r'^(\w+) equ (\d+)\s*$', include, re.M)}
        self.lines, self.labels = [], {}
        scope = ''
        for raw in (self.BOOT / 'boot_wait.asm').read_text(encoding='utf-8').splitlines():
            line = raw.split(';', 1)[0].rstrip() if "';'" not in raw else raw.rstrip()
            label = re.match(r'^(\.?\w+):', line)
            if label:
                name = label.group(1)
                scope = scope if name.startswith('.') else name
                self.labels[scope + name if name.startswith('.') else name] = len(self.lines)
                line = line[label.end():]
            if line.strip():
                self.lines.append((scope, line.strip()))
        self.keys, self.console = list(keys), console
        self.reg = {r: 0 for r in ('d0', 'd1', 'd2', 'd3', 'd4', 'a0', 'a1', 'a2', 'a3', 'a4', 'a6')}
        self.mem = {'fast_found_mb': found_mb, 'dos_base': 'dos'}
        self.buffers, self.output, self.saved, self.pending = {}, [], [], None
        self.seconds = self.reads = self.delays = 0
        self.call(routine)

    @staticmethod
    def _dcb(args):
        out = ''
        for part in re.findall(r'"[^"]*"|\d+', args):
            out += part[1:-1] if part.startswith('"') else chr(int(part))
        return out.split('\0', 1)[0] if '\0' in out else out

    def value(self, op):
        if op in self.reg:
            return self.reg[op]
        if op.startswith('#'):
            v = op[1:]
            return ord(v[1]) if v.startswith("'") else self.equ[v] if v in self.equ else int(v)
        if op == '4.w':
            return 'exec'
        return self.mem[op]

    def text(self, ref):
        kind, name = ref
        return self.buffers[name] if name in self.buffers else self.strings[name]

    def stub(self, name):
        r = self.reg
        if name == 'Input':
            r['d0'] = 'stdin' if self.console else 0
        elif name == 'RawDoFmt':
            fmt = self.text(r['a0'])
            arg = self.mem[r['a1'][1]]
            self.buffers[r['a3'][1]] = re.sub(r'%\d*ld', str(arg), fmt, count=1)
        elif name == 'WaitForChar':
            assert r['d1'] == 'stdin' and r['d2'] == 1000000
            key = self.keys.pop(0) if self.keys else None
            self.pending = key
            if key is None:
                self.seconds += 1
            r['d0'] = 0 if key is None else -1
        elif name == 'Read':
            assert r['d1'] == 'stdin' and r['d2'] == ('sym', 'input_byte') and r['d3'] == 1
            self.reads += 1
            self.mem['input_byte'] = ord(self.pending)
            r['d0'] = 1
        elif name == 'Delay':
            assert r['d1'] == 50
            self.delays += 1
            self.seconds += 1
        else:
            raise AssertionError('library call not stubbed: ' + name)

    def call(self, routine):
        stack, pc, flag_z = [None], self.labels[routine], False
        while pc is not None:
            scope, line = self.lines[pc]
            pc += 1
            op, _, args = line.partition(' ')
            ops = [a.strip() for a in re.findall(r"(?:'[^']*'|\([^)]*\)|[^,])+", args)]
            target = lambda name: self.labels[scope + name if name.startswith('.') else name]
            if op == 'movem.l':
                if ops[1] == '-(sp)':
                    self.saved.append(dict(self.reg))
                else:
                    self.reg.update(self.saved.pop())
            elif op in ('move.l', 'moveq', 'move.b'):
                v = self.value(ops[0])
                if ops[1] in self.reg:
                    self.reg[ops[1]] = v
                else:
                    self.mem[ops[1]] = v
                if not ops[1].startswith('a'):
                    flag_z = v in (0, None)  # a move to a data register or memory sets Z
            elif op == 'lea':
                self.reg[ops[1]] = ('sym', ops[0].replace('(pc)', ''))
            elif op == 'jsr':
                self.stub(re.match(r'_LVO(\w+)\(a6\)$', ops[0]).group(1))
            elif op == 'bsr':
                if ops[0] == 'puts':
                    self.output.append(self.text(self.reg['a0']))
                else:
                    stack.append(pc)
                    pc = target(ops[0])
            elif op == 'rts':
                pc = stack.pop()
            elif op in ('tst.l',):
                flag_z = self.value(ops[0]) in (0, None)
            elif op in ('cmp.l', 'cmp.b'):
                flag_z = self.value(ops[1]) == self.value(ops[0])
            elif op == 'subq.l':
                self.reg[ops[1]] -= self.value(ops[0])
                flag_z = self.reg[ops[1]] == 0
            elif op in ('beq', 'beq.s', 'bne', 'bne.s', 'bne.w', 'bra', 'bra.s'):
                if op.startswith('bra') or flag_z == op.startswith('beq'):
                    pc = target(ops[0])
            else:
                raise AssertionError('instruction not modelled: ' + line)


class FastRamSafeMinimumTests(unittest.TestCase):
    """RAM-REQUIREMENT-32MB-48: under 32 MB of Fast RAM the boot check shows a WARN row and the maintainer's
    note and waits for ENTER, the engine repeats the note without a wait; at 32 MB and more nothing extra."""
    MAINTAINER_TEXT = ('NOTE: AmiWind has grown since v0.0.48: 32 MB of Fast RAM is now the minimum. Only 16 MB '
                       'Fast RAM found, hence the game will start but may load more often. Press ENTER to continue '
                       'anyway.')

    def test_the_text_is_the_maintainers_word_for_word(self):
        self.assertEqual(project_version.fast_ram_note('16'), self.MAINTAINER_TEXT)
        self.assertEqual(project_version.fast_ram_note('16', enter=False),
                         self.MAINTAINER_TEXT[:-len(' Press ENTER to continue anyway.')])
        for width in (BOOT_COLUMNS, project_version.STARTUP_SCREEN_COLUMNS):
            rows = project_version.fast_ram_note_lines(width, enter=width == BOOT_COLUMNS)
            joined = ' '.join(rows).replace('%ld', '16')
            self.assertEqual(joined, self.MAINTAINER_TEXT if width == BOOT_COLUMNS
                             else project_version.fast_ram_note('16', enter=False))
            for row in rows:
                self.assertLessEqual(len(row.replace('%ld', '999999')), width, row)
        self.assertEqual(project_version.fast_ram_note_lines(BOOT_COLUMNS)[-1], 'Press ENTER to continue anyway.')

    def test_the_size_rule_at_16_32_and_between(self):
        short, found = project_version.fast_ram_short, project_version.fast_ram_found_mb
        for kib, is_short, mb in ((16384, True, 16), (16320, True, 16), (24576, True, 24), (31 * 1024, True, 31),
                                  (32704, False, 32), (32768, False, 32), (65536, False, 64), (131072, False, 128)):
            self.assertEqual(short(kib), is_short, kib)
            self.assertEqual(found(kib), mb, kib)

    def test_the_boot_checklist_row_and_the_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate_heap(tmp)
            include = (Path(tmp) / 'amiwind_heap.i').read_text()
        self.assertIn('AW_FAST_SAFE_KIB equ 32704\n', include)
        self.assertIn('AW_FAST_SLACK_KIB equ 64\n', include)
        row = re.search(r'fast_warn_format: dc\.b "([^"]*)"', include).group(1)
        self.assertEqual(row, 'Fast RAM:             %2ld MB (32 MB needed)       [!] WARN')
        # As printed (16 for %2ld) the marker sits in the column of the other rows.
        self.assertEqual(row.replace('%2ld', '16').index('[!] WARN'), 49)
        self.assertEqual(project_version.fast_ram_row('16'), row.replace('%2ld', '16'))
        note = ' '.join(re.findall(r'dc\.b "([^"]*)",10', include.split('fast_note:', 1)[1]))
        self.assertEqual(note.replace('%ld', '16'), self.MAINTAINER_TEXT)
        self.assertIn('AW_FAST_WAIT_SECONDS equ 10\n', include)
        self.assertIn('fast_countdown_format: dc.b 13,"Starting in %ld s... ",0\n', include)
        boot = (ROOT / 'engine/aga/boot/bootcheck.asm').read_text()
        # Below the minimum: the WARN row (never d7, never a stop); else the OK row.
        warn = boot.split('cmp.l   #AW_FAST_SAFE_KIB,12(a0)', 1)[1].split('.fast_address:', 1)[0]
        self.assertIn('bhs     .fast_full', warn)
        self.assertIn('lea     fast_warn_format(pc),a0', warn)
        self.assertNotIn('d7', warn)
        self.assertIn('lea     fast_ok_format(pc),a0', warn.split('.fast_full:', 1)[1])
        # The note right under the separator (nothing printed between), its countdown under it, then the verdict.
        tail = boot.split('lea     separator(pc),a0\n        bsr     puts\n', 1)[1].split('failed:', 1)[0]
        self.assertNotIn('puts', tail.split('bsr     fast_wait', 1)[0])
        self.assertIn('bsr     fast_wait\n        lea     passed(pc),a0', tail)
        self.assertIn('.countdown:\n        lea     passed(pc),a0\n        bsr     puts\n        bsr     countdown', tail)
        self.assertIn('include "boot_wait.asm"', boot)

    def test_the_boot_wait_never_blocks(self):
        """boot_wait.asm run on the host, line by line (BootWaitRun): ENTER skips, the timeout goes on by itself."""
        note = '\n'.join(project_version.fast_ram_note_lines(BOOT_COLUMNS)).replace('%ld', '16') + '\n'
        # Nobody presses a key (an unattended run): ten rows of one second each, then it starts by itself.
        run = BootWaitRun('fast_wait', keys=[])
        self.assertEqual(run.output[0], note)
        self.assertEqual(run.output[1:11], ['\rStarting in %d s... ' % n for n in range(10, 0, -1)])
        # Each row overwrites the one before (carriage return): "10 s" is one column wider than "9 s", and its last
        # column is a space, so no dot is left behind; "Starting now." covers the widest row.
        widths = [len(row) for row in run.output[1:11]]
        self.assertLessEqual(max(widths) - min(widths), 1)
        self.assertTrue(all(row.endswith(' ') for row in run.output[1:11]))
        self.assertGreaterEqual(len(run.output[11].rstrip('\n')), max(widths))
        self.assertEqual(run.output[11:], ['\rStarting now.                                     \n'])
        self.assertEqual((run.seconds, run.reads), (10, 0))
        # ENTER in the fourth second: the wait ends there.
        for key in ('\r', '\n'):
            run = BootWaitRun('fast_wait', keys=[None, None, None, key])
            self.assertEqual(run.output[1:5], ['\rStarting in %d s... ' % n for n in (10, 9, 8, 7)])
            self.assertEqual(run.output[5:], ['\rStarting now.                                     \n'])
            self.assertEqual((run.seconds, run.reads), (3, 1))
        # Another key does not end it; the count goes on.
        run = BootWaitRun('fast_wait', keys=['x'])
        self.assertEqual((len(run.output), run.seconds, run.reads), (12, 9, 1))
        # No console input at all: one-second Delay()s, still ten seconds, then the start.
        run = BootWaitRun('fast_wait', keys=[], console=False)
        self.assertEqual((len(run.output), run.seconds, run.delays), (12, 10, 10))
        # The 32 MB path keeps its five-second countdown.
        run = BootWaitRun('countdown', keys=[])
        self.assertEqual(run.output[0], '\rSPACE or ENTER = start now.   Starting in 5 s...')
        self.assertEqual((len(run.output), run.seconds), (6, 5))

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_the_engine_warns_at_16_mb(self):
        for fast in (16 * 1048576, 16 * 1048576 - 32):
            cli, screen, mb = run_fast_ram_note(fast)
            self.assertEqual(mb, 16)
            self.assertEqual(cli, self.MAINTAINER_TEXT[:-len(' Press ENTER to continue anyway.')] + '\n')
            self.assertEqual(screen.split('\n'), ['NOTE: AmiWind has grown since v0.0.48:',
                                                  '32 MB of Fast RAM is now the minimum.',
                                                  'Only 16 MB Fast RAM found, hence the',
                                                  'game will start but may load more often.'])

    @unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
    def test_the_engine_is_quiet_at_32_mb_and_more(self):
        for fast in (32 * 1048576, 32 * 1048576 - 32, 64 * 1048576, 128 * 1048576):
            self.assertEqual(run_fast_ram_note(fast), ('', '', 0), fast)

    def test_wired_into_the_start_the_console_and_the_logo(self):
        text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        self.assertIn('    Sys_FastRamNote();\n    // Allocate memory.', text)
        self.assertIn('if (aw_fast_ram_short_mb)\n        Con_Printf(AW_FAST_RAM_NOTE "\\n", aw_fast_ram_short_mb);', text)
        movie = (ROOT / 'engine/aga/src/aw_movie.c').read_text(encoding='utf-8')
        self.assertIn('char aw_fast_ram_screen[256];', movie)
        self.assertIn('for(p=aw_fast_ram_screen;*p;y+=10)', movie)


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


@unittest.skipUnless(shutil.which('cc'), 'host C compiler required')
class AutoHeapTests(unittest.TestCase):
    """The heap grown into spare Fast RAM (aw_heapsize.c, ENGINE-HEAP-FIXED-SIZE-43): 16 MiB keeps the built
    11 MiB exactly; a large machine grows it by a quarter of the room beyond it, to 24 MiB; -heapmb and
    aw_autoram 0 win."""

    def run_auto(self, *cases):
        harness = ('#include <stdio.h>\n#include "aw_heapsize.h"\n'
                   'int main(int argc,char **argv){int i,g;for(i=1;i+4<argc+1;i+=5){'
                   'int h=AW_HeapAuto(atoi(argv[i]),atoi(argv[i+1]),strtoul(argv[i+2],0,10)*1048576UL,'
                   'strtoul(argv[i+3],0,10)*1048576UL,atoi(argv[i+4]),&g);printf("%d %d\\n",h,g);}'
                   'printf("off %d %d %d\\n",AW_HeapAutoOff("bind x y\\naw_autoram \\"0\\"\\n"),'
                   'AW_HeapAutoOff("aw_autoram \\"1\\"\\n"),AW_HeapAutoOff("seta xaw_autoram \\"0\\"\\n"));return 0;}\n')
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'auto.c'
            source.write_text('#include <stdlib.h>\n' + harness)
            binary = Path(tmp) / 'auto'
            subprocess.run(['cc', '-std=c99', '-Wall', '-Werror', '-I', str(ROOT / 'engine/aga/src'), '-o', str(binary),
                            str(source), str(ROOT / 'engine/aga/src/aw_heapsize.c')], check=True)
            args = [str(v) for case in cases for v in case]
            return subprocess.run([str(binary), *args], capture_output=True, text=True, check=True).stdout.split('\n')

    def test_sizes(self):
        out = self.run_auto(
            (11, 0, 14, 16, 0),     # 16 MiB board, 14 free: the built heap, not grown
            (11, 0, 15, 16, 0),
            (11, 0, 26, 32, 0),     # 32 MiB (the safe minimum): room 26 - 6 = 20 >= 19 -> 11 + 9/4 = 13
            (11, 0, 113, 128, 0),   # 128 MiB: room 95 -> 11 + 21 = 32, at most 24
            (11, 12, 113, 128, 0),  # -heapmb 12: as asked
            (11, 0, 113, 128, 1),   # aw_autoram 0
            (11, 0, 2000, 2048, 0),
            (11, 0, 58, 64, 0))     # 64 MiB: room 58 - 10 = 48 -> 11 + 37/4 = 20
        # RAM-REQUIREMENT-32MB-48 moved no tier: more than 32 MiB is still used automatically.
        self.assertEqual(out[:8], ['11 0', '11 0', '13 1', '24 1', '12 0', '11 0', '24 1', '20 1'])
        self.assertEqual(out[8], 'off 1 0 0')

    def test_wired_into_the_start(self):
        text = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')
        self.assertIn('heap_mb = AW_HeapAuto(AMIWIND_HEAP_MB, 0, AvailMem(MEMF_FAST|MEMF_LARGEST),', text)
        self.assertIn('aw_heapsize.c', (ROOT / 'engine/aga/Makefile').read_text())


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
