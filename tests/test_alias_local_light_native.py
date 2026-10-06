# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import os
import shutil
import unittest
import test_aga_native_source as native


@unittest.skipIf(os.name == 'nt', 'native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'requires a C compiler')
class AliasLocalLightNative(unittest.TestCase):
    compile_run = native.NativeSourceTests.compile_run

    def test_local_light_survives_static_clamp_and_night_palette(self):
        self.compile_run('aga_alias_local_light_test.c',
            [Path(native.SOURCE)/'src'/name for name in
             ('r_alias.c', 'r_aclip.c', 'mathlib.c', 'd_polyse.c',
              'r_sky.c', 'aw_fog.c', 'aw_clock.c', 'aw_state.c')],
            cflags=['-fsanitize=address,undefined,float-cast-overflow',
                    '-fno-sanitize=alignment', '-fno-sanitize-recover=all'])
