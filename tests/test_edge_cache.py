# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import unittest
import test_aga_native_source as native

class EdgeCacheTests(unittest.TestCase):
    def test_actual_edge_clipping_projection_and_world_cache(self):
        native.NativeSourceTests().compile_run('aga_edge_cache_test.c',
            [Path(native.SOURCE)/'src/r_draw.c'],
            cflags=['-O1','-fsanitize=address,undefined','-fno-sanitize-recover=all'])

if __name__=='__main__':unittest.main()
