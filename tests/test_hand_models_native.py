# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import os
import shutil
import unittest
import test_aga_native_source as native


@unittest.skipIf(os.name=='nt','native fixtures run in Linux Docker')
@unittest.skipUnless(shutil.which('cc'),'requires a C compiler')
class HandModelsNative(unittest.TestCase):
    compile_run=native.NativeSourceTests.compile_run
    def test_race_sex_hand_model_pairs_preserve_frames_and_reset(self):
        self.compile_run('aga_hand_models_test.c',[Path(native.SOURCE)/'src/aw_hand_models.c'],
                         cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all'])
