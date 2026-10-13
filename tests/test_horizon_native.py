"""Actual resident LAND rasterizer checked against independent geometric rays."""
import os
from pathlib import Path
import shutil
import unittest
import test_aga_native_source as native

@unittest.skipIf(os.name == 'nt', 'automated native fixtures require Linux Docker')
@unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
class HorizonNativeTests(unittest.TestCase):
    def test_resident_land_matches_ray_geometry_and_preserves_foreground_and_gaps(self):
        native.NativeSourceTests().compile_run('aga_horizon_test.c',
            [Path(native.SOURCE)/'src'/name for name in ('aw_horizon.c','mathlib.c')],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])

    def test_fog_independent_land_with_rollback_and_interior_palette_guards(self):
        native.NativeSourceTests().compile_run('aga_horizon_test.c',
            [Path(native.SOURCE)/'src'/name for name in ('aw_horizon.c','aw_fog.c','mathlib.c')],
            defines=['HORIZON_FOG_TEST'],
            cflags=['-fsanitize=undefined,float-cast-overflow','-fno-sanitize-recover=all'])
