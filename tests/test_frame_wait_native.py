"""FRAME-WAIT-COUNTERS-59: per-frame disk, c2p and vbl wait counters (engine/aga/src/aw_spike.h)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'engine/aga/src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class FrameWaitNativeTests(unittest.TestCase):
    def test_nested_disk_calls_count_once(self):
        with tempfile.TemporaryDirectory() as scratch:
            exe = Path(scratch) / 'frame-wait-check'
            built = subprocess.run(['cc', '-std=gnu89', '-Wall', '-Werror', '-I' + str(SOURCE),
                                    str(ROOT / 'tests/aga_frame_wait_test.c'), '-o', str(exe)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('frame wait counters ok', run.stdout)


class FrameWaitSourceTests(unittest.TestCase):
    def read(self, name):
        return (SOURCE / name).read_text(encoding='utf-8', errors='replace')

    def test_wait_sites_are_timed(self):
        self.assertIn('AW_WAIT_END (AW_WAIT_C2P', self.read('vid_amiga.c'))
        self.assertIn('AW_WAIT_END (AW_WAIT_VBL', self.read('vid_amiga.c'))
        self.assertIn('AW_DISK_END (disk_t0)', self.read('common.c'))
        # quakedef.h asks for the wrappers; aw_spike.h (the timing header, BUILD-ENGINE-SOURCE-KEY-BROAD-36) has them
        quakedef = self.read('quakedef.h')
        self.assertIn('#define AW_DISKWAIT_WRAPPED\n#include "aw_spike.h"', quakedef)
        wrapped = self.read('aw_spike.h').split('#if defined(AW_DISKWAIT_WRAPPED)', 1)[1]
        for name in ('fopen', 'fread', 'fseek'):
            self.assertIn('#define %s(' % name, wrapped)

    def test_lines_and_report_carry_the_waits(self):
        spike = self.read('aw_spike.c')
        self.assertIn('"Long frame %d ms f%ld %s (%s):%s\\n"', spike)
        self.assertIn('"%s | %s%s%s\\n", line, waits', spike)
        self.assertIn('waits in %lu frames', spike)
        self.assertIn('{"disk", "c2p", "vbl"}', spike)

    def test_host_stubs_in_step(self):
        header = self.read('aw_spike.h')
        stubs = header.split('#else', 1)[1]
        for name in ('AW_DISK_BEGIN', 'AW_DISK_END', 'AW_WAIT_BEGIN', 'AW_WAIT_END'):
            self.assertIn('#define %s(' % name, header.split('#else', 1)[0])
            self.assertIn('#define %s(' % name, stubs)


if __name__ == '__main__':
    unittest.main()
