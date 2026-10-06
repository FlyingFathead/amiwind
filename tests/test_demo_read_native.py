# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import os,shutil,unittest
import test_aga_native_source as native


@unittest.skipIf(os.name=='nt','native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'),'requires a C compiler')
class DemoReadNative(unittest.TestCase):
    compile_run=native.NativeSourceTests.compile_run
    def test_complete_and_malformed_demo_reads_and_startup_timedemo(self):
        self.compile_run('aga_demo_read_test.c',[Path(native.SOURCE)/'src/cl_demo.c'],
                         cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])
