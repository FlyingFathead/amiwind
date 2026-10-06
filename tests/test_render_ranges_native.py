"""Render-range identity uses the real legacy coordinate/angle wire codec."""
import os
from pathlib import Path
import shutil
import unittest
import test_aga_native_source as native

@unittest.skipIf(os.name == 'nt', 'automated native fixtures require Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class RenderRangesNativeTests(unittest.TestCase):
    def test_actual_wire_angles_resolve_ranges_without_ambiguous_near_placements(self):
        native.NativeSourceTests().compile_run('aga_render_ranges_wire_test.c',
            [Path(native.SOURCE)/'src/common.c'],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])
