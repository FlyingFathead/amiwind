"""Regression tests for free-look pitch drift policy."""
import os
from pathlib import Path
import shutil
import unittest
import test_aga_native_source as native

@unittest.skipIf(os.name == 'nt', 'native fixtures run inside Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class ViewAutoCenterTests(unittest.TestCase):
    def test_free_look_default_opt_in_explicit_center_and_quiet_mouse_mlook(self):
        config=(native.ROOT/"config/game.cfg").read_text(encoding="utf-8")
        self.assertRegex(config, r"(?m)^aw_auto_center 0$")
        native.NativeSourceTests().compile_run('aga_view_autocenter_test.c',
            [Path(native.SOURCE)/'src/view.c', Path(native.SOURCE)/'src/in_amiga.c'],
            cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])
