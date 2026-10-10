# SPDX-License-Identifier: GPL-3.0-only
"""v0.0.35 engine review fixes: one regression check per mechanism.

ENGINE-PAK-HEADER-TRUST-35, ENGINE-VA-UNBOUNDED-35, ENGINE-FILEBASE-UNBOUNDED-35,
ENGINE-ANGLEMOD-RANGE-35, ENGINE-GAMMA-POW-35 run natively (aga_engine_review_test.c);
ENGINE-FLOATTIME-DIV64-35 runs the extracted helper natively; the Amiga-only
paths (stack check, UDP address, scene names, harvest message, unlink, fopen
mode, c2p rect list) are checked in the source. ENGINE-C2P-ROWSTRIDE-35 is
checked against a pixel oracle in test_aga.py."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def text(name):
    return (SRC / name).read_text(encoding='utf-8')


def section(body, start, end):
    return body[body.index(start):body.index(end, body.index(start))]


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class EngineReviewNative(unittest.TestCase):
    compile_run = native.NativeSourceTests.compile_run

    def test_pak_header_bounds_va_filebase_anglemod_gamma(self):
        self.compile_run('aga_engine_review_test.c',
                         [SRC / 'common.c', SRC / 'crc.c', SRC / 'mathlib.c'],
                         cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_eclock_seconds_matches_64_bit_reference(self):
        helper = section(text('sys_amiga.c'), '/* aw_eclock_seconds begin */', '/* aw_eclock_seconds end */')
        program = helper + r'''
#include <stdio.h>
int main(void)
{
    static const unsigned long long base[] = {0ULL, 0xfffffff0ULL, 0x1234ffffffffULL};
    static const unsigned long long step[] = {0ULL, 1ULL, 15ULL, 16ULL, 709379ULL, 0x100000000ULL, 709379ULL * 86400ULL};
    unsigned i, j;
    for (i = 0; i < 3; i++)
        for (j = 0; j < 7; j++) {
            unsigned long long a = base[i], b = base[i] + step[j];
            double got = AW_EClockSeconds((unsigned long)(b >> 32), (unsigned long)(b & 0xffffffffULL),
                                          (unsigned long)(a >> 32), (unsigned long)(a & 0xffffffffULL),
                                          1.0 / 709379.0);
            double want = (double)step[j] / 709379.0;
            if (got - want > 1e-9 || want - got > 1e-9) { printf("%u %u %.12f %.12f\n", i, j, got, want); return 1; }
        }
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            c = Path(tmp) / 'eclock.c'
            c.write_text(program, encoding='utf-8', newline='\n')
            exe = Path(tmp) / 'eclock'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', str(c), '-o', str(exe)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stdout)


class EngineReviewSource(unittest.TestCase):
    def test_floattime_uses_the_eclock_directly(self):
        body = section(text('sys_amiga.c'), 'double Sys_FloatTime (void)', 'char *Sys_ConsoleInput')
        fast = body[:body.index('timer (clock);')]
        self.assertIn('ReadEClock', fast)
        self.assertIn('AW_EClockSeconds', fast)

    def test_stack_is_checked_before_anything_else(self):
        sys = text('sys_amiga.c')
        main = section(sys, 'int main(int argc', 'RunGameLoop();')
        self.assertLess(main.index('AW_StackTooSmall()'), main.index('AW_PlatformInit();'))
        check = section(sys, 'static int AW_StackTooSmall', 'int main(int argc')
        self.assertIn('tc_SPUpper', check)
        self.assertIn('tc_SPLower', check)
        # The minimum stays below what the boot disk sets.
        minimum = int(re.search(r'#define AW_MIN_STACK (\d+)UL', sys).group(1))
        startup = (ROOT / 'tools/fpu_support.py').read_text(encoding='utf-8')
        given = int(re.search(r"'Stack (\d+)'", startup).group(1))
        self.assertGreaterEqual(minimum, 2048 * 64 + 65536)  # pak directory + headroom
        self.assertLess(minimum, given)

    def test_udp_partial_address_is_length_checked(self):
        body = section(text('net_amigaudp.c'), 'static int PartialIPAddress', 'int UDP_Connect')
        self.assertLess(body.index('strlen(in) > sizeof(buff) - 2'), body.index('strcpy(buff+1, in)'))

    def test_scene_names_are_copied_bounded(self):
        scene = text('aw_scene.c')
        self.assertNotRegex(scene, r'strcpy\((r\.target|r\.source|links_map),')
        self.assertIn('copy_name(r.target,sizeof(r.target),', scene)

    def test_harvest_message_is_bounded(self):
        body = section(text('aw_harvest_runtime.c'), 'int AW_HarvestUse(void)', 'return 1;\n}')
        self.assertNotIn('sprintf(line,', body.replace('snprintf(line,', ''))
        self.assertIn('>sizeof(message))break;', body)

    def test_unlink_deletes_and_binary_files_open_binary(self):
        stubs = text('amiga_stubs.c')
        self.assertIn('DeleteFile(', section(stubs, 'int unlink(', '}'))
        self.assertNotIn('fopen(path, "r")', text('sys_file_amiga.c'))

    def test_vid_update_converts_every_rect(self):
        body = section(text('vid_amiga.c'), 'void\tVID_Update (vrect_t *rects)', '} else {')
        self.assertIn('r = r->pnext', body)
        self.assertIn('vid.width, rows', body)
        self.assertIn('BytesPerRow < width / 8', text('vid_amiga.c'))

    def test_gamma_table_does_not_call_pow(self):
        self.assertNotRegex(text('view.c'), r'\bpow\s*\(')


if __name__ == '__main__':
    unittest.main()
