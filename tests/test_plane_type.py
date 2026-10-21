# SPDX-License-Identifier: GPL-3.0-only
"""Plane type at load (CHIM-PLANE-TYPE-ALL-SLANTED-46): the CHIM converter writes type 3 for every plane, so the
engine's loader gives a plane with an exact +X/+Y/+Z normal its axis (aw_planetype.h), and Quake's axial fast paths
apply to converted worlds as they do to id maps."""
import os
import re
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class PlaneTypeTests(unittest.TestCase):
    def test_axial_planes_get_their_axis_and_the_same_distances(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_plane_type_test.c', [],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class LoaderWiringTests(unittest.TestCase):
    def test_the_brush_plane_loader_sets_the_type(self):
        code = re.sub(r'/\*.*?\*/', '', (SRC / 'model.c').read_text(encoding='utf-8'), flags=re.S)
        loader = code[code.index('void Mod_LoadPlanes (lump_t *l)'):code.index('RadiusFromBounds')]
        self.assertIn('out->type = AW_PlaneType (out->normal, LittleLong (in->type));', loader)
        self.assertIn('#include "aw_planetype.h"', code)


if __name__ == '__main__':
    unittest.main()
