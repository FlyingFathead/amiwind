# SPDX-License-Identifier: GPL-3.0-only
"""Wide coordinates (engine/aga/src/aw_coord.h, the default since v0.0.36, CHIM-FRAME-COORD-RANGE-33): 24 bits of
1/256 units round-trip every position of the +/-32,768 range to within half a 1/256 unit, clamp instead of
wrapping, and set the bound and the protocol number; AW_COORD_NARROW (tools/build.py --coord-range narrow) keeps
Quake's values (bound 4,000, protocol 15); AW_EXP_WIDECOORD (the spike's switch) still selects wide, and both
switches together do not compile."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src'
FLAGS = ['-std=gnu89', '-Wall', '-Werror', '-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all']

HARNESS = r'''
#include <math.h>
#include <stdio.h>
#include "aw_coord.h"
static int fails;
static void check(float f, float expect)
{
    unsigned char b[3];
    float back;
    AW_Coord24Encode(f, b);
    back = AW_Coord24Decode(b);
    if (fabs(back - expect) > 0.5 / 256.0 + 1e-6) { printf("FAIL %f -> %f (want %f)\n", f, back, expect); fails++; }
}
int main(void)
{
    float v;
    for (v = -32767.0f; v <= 32767.0f; v += 97.37f) check(v, v);
    check(0.0f, 0.0f); check(4096.0f, 4096.0f); check(-4096.5f, -4096.5f); check(5440.125f, 5440.125f);
    check(1.0f / 1024.0f, 0.0f); check(1.0f / 512.0f, 1.0f / 256.0f); check(-0.001f, 0.0f);
    check(40000.0f, 8388607.0f / 256.0f); check(-40000.0f, -32768.0f);      /* clamped, never wrapped */
    check(NAN, 0.0f);
    printf("bytes %d bound %d protocol %d\n", AW_COORD_BYTES, AW_COORD_BOUND, AW_COORD_PROTOCOL);
    return fails != 0;
}
'''


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class WideCoordTests(unittest.TestCase):
    def run_harness(self, defines, compiles=True):
        with tempfile.TemporaryDirectory() as scratch:
            src = Path(scratch) / 'coord.c'
            src.write_text(HARNESS, encoding='utf-8')
            exe = str(Path(scratch) / 'coord')
            built = subprocess.run(['cc', *FLAGS, *defines, '-I' + str(SOURCE), str(src), '-lm', '-o', exe],
                                   capture_output=True, text=True)
            if not compiles:
                self.assertNotEqual(built.returncode, 0)
                return built.stderr
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            ran = subprocess.run([exe], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
            return ran.stdout.strip().splitlines()[-1]

    def test_default_is_wide_round_trips_and_raises_the_bound(self):
        self.assertEqual(self.run_harness([]), 'bytes 3 bound 32000 protocol 1015')
        self.assertEqual(self.run_harness(['-DAW_EXP_WIDECOORD']), 'bytes 3 bound 32000 protocol 1015')

    def test_narrow_keeps_quakes_values(self):
        self.assertEqual(self.run_harness(['-DAW_COORD_NARROW']), 'bytes 2 bound 4000 protocol 15')

    def test_both_switches_refuse_to_compile(self):
        self.assertIn('different coordinate ranges',
                      self.run_harness(['-DAW_COORD_NARROW', '-DAW_EXP_WIDECOORD'], compiles=False))


if __name__ == '__main__':
    unittest.main()
