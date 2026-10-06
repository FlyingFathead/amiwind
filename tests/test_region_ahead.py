"""Exercise actual first-crossed-region prediction with synthetic public geometry."""
import os
from pathlib import Path
import shutil
import unittest
import test_aga_native_source as native

@unittest.skipIf(os.name == 'nt', 'native fixtures run inside Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class RegionAheadTests(unittest.TestCase):
    def test_first_residency_hysteresis_directions_corners_and_guards(self):
        native.NativeSourceTests().compile_run('aga_region_ahead_test.c',
            [Path(native.SOURCE)/'src/aw_region.c'],
            cflags=['-fsanitize=undefined,float-cast-overflow', '-fno-sanitize-recover=all'])
