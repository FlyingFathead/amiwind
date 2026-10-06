# SPDX-License-Identifier: GPL-3.0-only
"""Actual compact catalogue ownership, dense admission and persistent facts."""
import os
from pathlib import Path
import unittest

import test_aga_native_source as native


@unittest.skipIf(os.name == 'nt', 'C fixtures run in the authorized Linux Docker builder')
class CompactHarvestNativeTests(unittest.TestCase):
    def test_dense_maps_owned_allocations_oom_and_saved_facts(self):
        native.NativeSourceTests().compile_run(
            'aga_harvest_compact_test.c',
            [Path(native.SOURCE)/'src'/name for name in
             ('aw_harvest.c', 'aw_harvest_proxy.c', 'aw_state.c', 'aw_save_codec.c')],
            cflags=['-O1', '-g', '-fsanitize=address,undefined,float-cast-overflow',
                    '-fno-sanitize-recover=all', '-Wl,--wrap=calloc',
                    '-Wl,--wrap=realloc', '-Wl,--wrap=free'])


if __name__ == '__main__':
    unittest.main()
