# SPDX-License-Identifier: GPL-3.0-only
"""Actual C decoder and hunk/cache comparison; asset-free fixtures."""
from pathlib import Path
import unittest
import test_aga_native_source as native

class AliasStreamTests(unittest.TestCase):
    def test_direct_stream_cache_bytes_and_lifetimes(self):
        native.NativeSourceTests().compile_run('aga_alias_stream_test.c',
            [Path(native.SOURCE)/'src'/name for name in ('model.c','mathlib.c')],
            cflags=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wl,--wrap=malloc'])

if __name__=='__main__':
    unittest.main()
