# SPDX-License-Identifier: GPL-3.0-only
"""The load trace and the memory line (LOAD-HANG-WATCHDOG-62, CHIM-SEYDA-BALMORA-LOAD-HANG-43, experiments E6 and the
switchable load trace): the ring in engine/aga/src/aw_loadtrace.c (host C), and the source contracts that keep it off
by default, one test per file call when off, never writing during a load, and the memory line after every load."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class LoadTraceNativeTests(unittest.TestCase):
    def test_ring_off_on_wrap_names_unfinished_and_dump(self):
        native.NativeSourceTests().compile_run('aga_loadtrace_test.c', [SRC / 'aw_loadtrace.c'],
                                               defines=('AW_LOADTRACE_HOST_TEST',),
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class LoadTraceSourceContracts(unittest.TestCase):
    def test_off_by_default_and_one_test_per_file_call(self):
        trace = code('aw_loadtrace.c')
        self.assertIn('static cvar_t loadtrace_cvar = {"aw_loadtrace", "0"};', trace)
        spike = code('aw_spike.h')
        bodies = spike[spike.index('#define AW_DISKWAIT_BODIES'):]
        for wrapper in ('AW_DiskFopen', 'AW_DiskFread', 'AW_DiskFseek', 'AW_DiskFclose'):
            body = bodies[bodies.index(wrapper):]
            body = body[:body.index('return')]
            self.assertEqual(body.count('if(aw_loadtrace_on)'), 1, wrapper)
            self.assertIn('if(lt)AW_LoadTraceEnd(', body, wrapper)
        self.assertIn('#define fclose(f) AW_DiskFclose((f))', spike)
        # the shipped default config does not turn it on
        self.assertNotIn('aw_loadtrace', (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8'))

    def test_no_file_written_during_a_load(self):
        trace = code('aw_loadtrace.c')
        self.assertIn('#define AW_DISKWAIT_NO_WRAP', (SRC / 'aw_loadtrace.c').read_text(encoding='utf-8'))
        # the only fopen is the dump's, reached from Scene ready / first presented and the command
        self.assertEqual(trace.count('fopen ('), 1)
        # the definitions, not the prototypes near the top of the file (a prototype ends in ';', a definition opens '{')
        def definition(name):
            return re.search(r'void %s\s*\([^;{]*\)\s*\{' % name, trace).start()
        dump = trace[definition('AW_LoadTraceDump'):definition('AW_LoadTraceSceneReady')]
        self.assertIn('fopen (LT_FILE, "w")', dump)
        self.assertIn('#define LT_FILE\t\t"RAM:amiwind-loadtrace.txt"', trace)
        self.assertIn('AW_LoadTraceSceneReady("scene ready")', code('aw_scene.c'))
        self.assertIn('AW_LoadTraceSceneReady("first presented")', code('aw_stream.c'))

    def test_memory_line_after_every_load_and_at_scene_ready(self):
        zone = code('zone.c')
        self.assertIn('"Mem %s %s: hunk low %ld high %ld; zone largest %d free %d; cache %ld peak %ld; '
                      'fast %lu largest %lu; chip %lu largest %lu\\n"', zone)
        for phase in ('after-actors', 'scene-ready', 'after-restore'):
            self.assertIn('"%s"' % phase, zone)
        self.assertIn('AW_HeapAuditPhase(sv.name,"scene-ready")', code('aw_scene.c'))
        self.assertIn('AW_HeapAuditPhase(sv.modelname,"after-actors")', code('sv_main.c'))

    def test_registered_and_in_the_debug_help(self):
        self.assertIn('aw_loadtrace.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))
        self.assertIn('AW_LoadTraceInit();', code('aw_debug.c'))
        rows = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        self.assertIn('PLAYTESTING|loadtrace|aw_loadtrace_cmd|', rows)


if __name__ == '__main__':
    unittest.main()
